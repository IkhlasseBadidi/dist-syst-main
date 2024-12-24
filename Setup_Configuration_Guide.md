# Distributed File Service Setup Guide

## Server Access

> Note: While IP addresses are still used in the system, they are now stored in configuration files (config.yaml) rather than being hardcoded in the server code. 

1. Connect to UH gateway:
```bash
ssh username@pangolin.it.helsinki.fi
```

2. Access servers:
```bash
# Server 1
ssh username@svm-11.cs.helsinki.fi
# Server 2
ssh username@svm-11-2.cs.helsinki.fi
# Server 3
ssh username@svm-11-3.cs.helsinki.fi
```

## Installation (On Each Server)

1. Create directories and set permissions:
```bash
mkdir -p ~/distributed-file-service/{config,distfiles}
chmod 755 ~/distributed-file-service/distfiles
```

2. Install required packages:
```bash
pip3 install --user flask pyyaml
```

3. Server Code Implementation
Add `server.py` to each server's `~/distributed-file-service/` directory:

```python
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
NODES = config['NODES']
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
    # Start socket server in background thread
    threading.Thread(target=socket_server, daemon=True).start()
    # Start Flask web server in main thread
    app.run(host=HOST, port=PORT)

```

This code should be identical for all three servers. The only difference is in the configuration files that each server loads.

4. Create config loader (`~/distributed-file-service/config_loader.py`):
```python
import yaml
import socket
import logging
from pathlib import Path

def load_config(config_file='config/config.yaml'):
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        server_ip = socket.gethostbyname(config['server']['host'])
        nodes = []
        for node in config['nodes']:
            node_ip = socket.gethostbyname(node['host'])
            nodes.append((node_ip, node['socket_port']))
        
        Path(config['storage']['path']).mkdir(parents=True, exist_ok=True)
        
        return {
            'HOST': server_ip,
            'PORT': config['server']['http_port'],
            'SOCK_PORT': config['server']['socket_port'],
            'NODES': nodes,
            'STORAGE': config['storage']['path'],
            'LOG_FILE': config['storage']['log_file']
        }
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        raise
```

## Server Configuration

Create respective config files (`~/distributed-file-service/config/config.yaml`):

### Server 1 (svm-11):
```yaml
server:
  host: svm-11.cs.helsinki.fi
  http_port: 65421
  socket_port: 65411
nodes:
  - host: svm-11-2.cs.helsinki.fi
    socket_port: 65411
  - host: svm-11-3.cs.helsinki.fi
    socket_port: 65411
storage:
  path: ./distfiles
  log_file: server1.log
```

### Server 2 (svm-11-2):
```yaml
server:
  host: svm-11-2.cs.helsinki.fi
  http_port: 65422
  socket_port: 65411
nodes:
  - host: svm-11.cs.helsinki.fi
    socket_port: 65411
  - host: svm-11-3.cs.helsinki.fi
    socket_port: 65411
storage:
  path: ./distfiles
  log_file: server2.log
```

### Server 3 (svm-11-3):
```yaml
server:
  host: svm-11-3.cs.helsinki.fi
  http_port: 65423
  socket_port: 65411
nodes:
  - host: svm-11.cs.helsinki.fi
    socket_port: 65411
  - host: svm-11-2.cs.helsinki.fi
    socket_port: 65411
storage:
  path: ./distfiles
  log_file: server3.log
```

## Running the Servers
On each server:
```bash
cd ~/distributed-file-service
python3 server.py
```

Expected output:
```
[timestamp] INFO in server: Socket server listening on [HOST]:[SOCK_PORT]
* Running on http://[HOST]:[PORT]
```

## Testing
From pangolin:

1. Basic upload and download:
```bash
# Create and upload file
echo "Test content $(date)" > test.txt
curl -F "file=@test.txt" http://svm-11.cs.helsinki.fi:65421/file/test.txt

# Verify from all servers
curl http://svm-11.cs.helsinki.fi:65421/file/test.txt
curl http://svm-11-2.cs.helsinki.fi:65422/file/test.txt
curl http://svm-11-3.cs.helsinki.fi:65423/file/test.txt
```

2. Version sync test:
```bash
# Upload new version to different server
echo "Updated content $(date)" > test.txt
curl -F "file=@test.txt" http://svm-11-2.cs.helsinki.fi:65422/file/test.txt

# Verify synchronization
curl http://svm-11.cs.helsinki.fi:65421/file/test.txt
curl http://svm-11-2.cs.helsinki.fi:65422/file/test.txt
curl http://svm-11-3.cs.helsinki.fi:65423/file/test.txt
```
