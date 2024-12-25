import socket             
from flask import Flask, request, send_file 
import os               
import threading         
import logging          
from logging.handlers import RotatingFileHandler  
import time
from config_loader import load_config


# Load configuration
config = load_config()
HOST = config['HOST']
PORT = config['PORT']
SOCK_PORT = config['SOCK_PORT']
DISCOVERY_HOST = config['DISCOVERY_HOST']
DISCOVERY_PORT = config['DISCOVERY_PORT']
STORAGE = config['STORAGE']
LOG_FILE = config['LOG_FILE']

# Create storage directory if missing - ensures application doesn't fail on first run
if not os.path.exists(STORAGE):
    os.makedirs(STORAGE, exist_ok=True)

# ====== Flask and Logging Setup ======
app = Flask(__name__)  # Initialize Flask application

# Configure rotating log handler:
# - Rotates log file when it reaches 10KB
# - Keeps one backup file
# - Uses timestamp-name-level-message format for log entries
handler = RotatingFileHandler(LOG_FILE, maxBytes=10000, backupCount=1)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Shared state
NODES = []  # List of peer nodes
REJOIN_INTERVAL = 5  # Interval to retry joining discovery service

def join_discovery_service():
    """
    Registers the file server with the discovery server and updates the list of peer nodes.
    """
    while True:
        try:
            with socket.create_connection((DISCOVERY_HOST, DISCOVERY_PORT), timeout=5) as sock:
                message = f"Join-Discovery-Service {HOST}:{SOCK_PORT}\n"
                sock.sendall(message.encode("utf-8"))
                response = sock.recv(1024).decode("utf-8").strip()
                
                if response.startswith("Peer-Node-Address-Listing"):
                    global NODES
                    NODES = [tuple(node.split(":")) for node in response.split("\n")[1:] if node]
                    print(f"Updated peer nodes: {NODES}")
                break  # Exit retry loop if successful
        except Exception as e:
            print(f"Failed to join discovery service: {e}")
            time.sleep(REJOIN_INTERVAL)  # Retry after delay

def listen_for_discovery_updates():
    """
    Listens for periodic updates from the discovery server and updates the list of peer nodes.
    """
    while True:
        try:
            with socket.create_connection((DISCOVERY_HOST, DISCOVERY_PORT), timeout=5) as sock:
                print("Connected to discovery server for updates.")
                while True:
                    response = sock.recv(1024).decode("utf-8").strip()
                    if not response:  # Empty response means connection was closed
                        print("Connection closed by discovery server.")
                        break  # Exit the inner loop to reconnect
                    
                    if response.startswith("Peer-Node-Address-Listing"):
                        global NODES
                        NODES = [tuple(node.split(":")) for node in response.split("\n")[1:] if node]
                        print(f"Received updated peer nodes: {NODES}")
                        sock.sendall("OK\n".encode("utf-8"))
        except Exception as e:
            print(f"Lost connection to discovery server: {e}")
        finally:
            # Reconnect after a delay
            time.sleep(REJOIN_INTERVAL)
            print("Reconnecting to discovery server...")

def start_discovery_thread():
    """
    Starts the thread to manage discovery service interaction.
    """
    threading.Thread(target=join_discovery_service, daemon=True).start()
    threading.Thread(target=listen_for_discovery_updates, daemon=True).start()

def validate_filename(filename):
    """
    Security check for filenames to prevent directory traversal attacks
    
    Parameters:
        filename (str): Name of file to validate
    
    Returns:
        bool: True if filename is safe to use, False if potentially malicious
    
    Security checks:
        - Not empty string
        - No forward slashes (Unix paths)
        - No backslashes (Windows paths)
        - No parent directory references (..)
        - Length within reasonable limits
    """
    return (filename and 
            '/' not in filename and 
            '\\' not in filename and 
            '..' not in filename and 
            len(filename) < 255)

def get_timestamp(filename):
    """
    Gets modification time for a local file and formats it as protocol message
    
    Parameters:
        filename (str): Name of file to check
    
    Returns:
        str: Protocol message with format "Last-Modified <filename> <timestamp> <server-id>"
            or None if file doesn't exist/invalid
    
    Process:
        1. Validate filename
        2. Check if file exists
        3. Get modification time
        4. Format protocol message with server identifier
    """
    if not validate_filename(filename):
        return None
    
    path = os.path.join(STORAGE, filename)
    if os.path.exists(path):
        timestamp = os.path.getmtime(path)
        return f"Last-Modified {filename} {timestamp} {HOST}:{SOCK_PORT}"
    return None

def latest_timestamp(filename):
    """
    Queries all servers to find most recent version of a file
    
    Parameters:
        filename (str): Name of file to check
    
    Returns:
        tuple: (latest modification info, node with latest version)
    
    Process:
        1. Get local timestamp
        2. Query each peer server
        3. Compare timestamps
        4. Track server with most recent version
        5. Handle connection failures
    """
    app.logger.info(f"Checking timestamps for {filename}")
    
    # Get local file timestamp first
    latest = get_timestamp(filename)
    latest_ts = float(latest.split()[2]) if latest else 0
    latest_node = None

    # Query each peer server for their version
    for host, port in NODES:
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                # Send timestamp check request
                message = f"Last-Modified-Check {filename}\n"
                sock.sendall(message.encode('utf-8'))
                response = sock.recv(1024).decode('utf-8').strip()
                
                # Parse response and update if newer version found
                if response.startswith("Last-Modified"):
                    _, _, timestamp, node = response.split()
                    if float(timestamp) > latest_ts:
                        latest_ts = float(timestamp)
                        latest_node = node
                        latest = response
        except Exception as e:
            app.logger.error(f"Communication with node {host}:{port} failed: {e}")
    
    return latest, latest_node

@app.route("/file/<filename>", methods=["GET"])
def get_file(filename):
    """
    HTTP endpoint for file downloads
    
    Parameters:
        filename (str): Name of file to download
    
    Returns:
        File data or error message with appropriate HTTP status code
    
    Process:
        1. Validate filename
        2. Check all servers for latest version
        3. Download from peer if needed
        4. Send file to client
    """
    if not validate_filename(filename):
        return "Invalid filename", 400
    
    latest, latest_node = latest_timestamp(filename)
    
    # Check if file exists anywhere in the system
    if not latest and not os.path.exists(os.path.join(STORAGE, filename)):
        return "File not found", 404

    filepath = os.path.join(STORAGE, filename)
    
    # If newer version exists on another server, fetch it first
    if latest_node and latest_node != f"{HOST}:{SOCK_PORT}":
        host, port = latest_node.split(':')
        try:
            with socket.create_connection((host, int(port)), timeout=5) as sock:
                # Request file from peer server
                message = f"File-Provision-Request {filename}\n"
                sock.sendall(message.encode('utf-8'))
                data = sock.recv(1024 * 1024)  # Read up to 1MB
                # Save newer version locally
                with open(filepath, "wb") as f:
                    f.write(data)
        except Exception as e:
            return f"Error downloading file: {e}", 500

    return send_file(filepath, as_attachment=True)

@app.route("/file/<filename>", methods=["POST"])
def save_file(filename):
    """
    HTTP endpoint for file uploads
    
    Parameters:
        filename (str): Name to save file as
        
    Returns:
        Empty response with appropriate HTTP status code
    
    Process:
        1. Validate filename and request
        2. Save uploaded file
        3. Log success
    """
    if not validate_filename(filename):
        return "Invalid filename", 400
    if 'file' not in request.files:
        return "No file provided", 400
    
    file = request.files["file"]
    path = os.path.join(STORAGE, filename)
    file.save(path)
    app.logger.info(f"File {filename} saved successfully")
    return "", 204

def handle_socket_request(conn, data):
    """
    Processes incoming requests from peer servers
    
    Parameters:
        conn: Socket connection object
        data (str): Received request message
    
    Handles three types of requests:
        1. Last-Modified-Check: Return file timestamp
        2. File-Provision-Request: Send file data
        3. Index-Listing-Request: List all files
    """
    try:
        # Handle timestamp check request
        if data.startswith('Last-Modified-Check'):
            filename = data.split()[1]
            response = get_timestamp(filename)
            conn.sendall((response or "File not found").encode('utf-8'))
        
        # Handle file download request    
        elif data.startswith('File-Provision-Request'):
            filename = data.split()[1]
            filepath = os.path.join(STORAGE, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    data = f.read()
                conn.sendall(data)
            else:
                conn.sendall(b"File not found")
        
        # Handle file listing request        
        elif data.startswith('Index-Listing-Request'):
            files = os.listdir(STORAGE)
            response = "Index-Listing\n" + "\n".join(files) + "\n"
            conn.sendall(response.encode('utf-8'))
    except Exception as e:
        app.logger.error(f"Error handling socket request: {e}")
        conn.sendall(b"Error processing request")

def socket_server():
    """
    Background server for peer-to-peer communication
    
    Process:
        1. Create and bind socket
        2. Listen for connections
        3. Spawn handler thread for each connection
        4. Continue accepting new connections
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((HOST, SOCK_PORT))
        server_sock.listen()
        app.logger.info(f"Socket server listening on {HOST}:{SOCK_PORT}")
        
        while True:
            conn, addr = server_sock.accept()
            app.logger.info(f"New connection from {addr}")
            threading.Thread(target=handle_connection, args=(conn, addr)).start()

def handle_connection(conn, addr):
    """
    Handles individual peer server connections
    
    Parameters:
        conn: Socket connection object
        addr: Address of connecting peer
        
    Process:
        1. Receive request data
        2. Process request
        3. Ensure connection cleanup
        4. Log any errors
    """
    with conn:
        try:
            data = conn.recv(1024).decode('utf-8').strip()
            handle_socket_request(conn, data)
        except Exception as e:
            app.logger.error(f"Failed socket connection from {addr}: {e}")

# Application entry point
if __name__ == "__main__":
    start_discovery_thread()
    # Start socket server in background thread
    threading.Thread(target=socket_server, daemon=True).start()
    # Start Flask web server in main thread
    app.run(host=HOST, port=PORT)
