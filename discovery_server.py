import socket
import threading
import time

# Global state to store active nodes
nodes = {}
lock = threading.Lock()  # Ensures thread-safe access to `nodes`

# Configuration
DISCOVERY_HOST = "128.214.224.188"
DISCOVERY_PORT = 6500
NODE_TIMEOUT = 3  # Number of consecutive missed updates before considering a node unresponsive
UPDATE_INTERVAL = 10  # Time interval (in seconds) between node updates
RETRY_INTERVAL = 1  # Retry interval for re-establishing communication with unresponsive nodes


def send_to_node(node_address, message):
    """
    Sends a message to a node and waits for a response.
    
    Parameters:
        node_address (tuple): (host, port) of the node
        message (str): Message to send
    
    Returns:
        bool: True if the message was acknowledged, False otherwise
    """
    try:
        with socket.create_connection(node_address, timeout=1) as sock:
            sock.sendall(message.encode("utf-8"))
            response = sock.recv(1024).decode("utf-8").strip()
            return response == "OK"
    except Exception:
        return False


def update_nodes():
    """
    Periodically sends updated node listings to all active nodes.
    """
    while True:
        time.sleep(UPDATE_INTERVAL)
        with lock:
            inactive_nodes = []
            current_nodes = list(nodes.keys())

            for node in current_nodes:
                message = "Peer-Node-Address-Listing\n" + "\n".join(f"{host}:{port}" for host, port in current_nodes) + "\n"
                success = send_to_node(node, message)

                if success:
                    nodes[node]["missed_updates"] = 0
                else:
                    nodes[node]["missed_updates"] += 1
                    if nodes[node]["missed_updates"] >= NODE_TIMEOUT:
                        inactive_nodes.append(node)

            # Remove unresponsive nodes
            for node in inactive_nodes:
                del nodes[node]


def handle_node_registration(conn, addr):
    """
    Handles registration messages from nodes.

    Parameters:
        conn: The socket connection to the node
        addr: The address (host, port) of the connecting node
    """
    try:
        data = conn.recv(1024).decode("utf-8").strip()
        if data.startswith("Join-Discovery-Service"):
            node_address = tuple(data.split()[1].split(":"))
            with lock:
                if node_address not in nodes:
                    nodes[node_address] = {"last_seen": time.time(), "missed_updates": 0}
            # Respond with a listing of all nodes
            current_nodes = list(nodes.keys())
            listing_message = "Peer-Node-Address-Listing\n" + "\n".join([f"{host}:{port}" for host, port in current_nodes]) + "\n"
            conn.sendall(listing_message.encode("utf-8"))
    except Exception as e:
        print(f"Error handling node registration from {addr}: {e}")
    finally:
        conn.close()


def discovery_server():
    """
    Main server loop for the discovery service.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((DISCOVERY_HOST, DISCOVERY_PORT))
        server_sock.listen()
        print(f"Discovery server listening on {DISCOVERY_HOST}:{DISCOVERY_PORT}")

        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_node_registration, args=(conn, addr)).start()


if __name__ == "__main__":
    # Start the background update thread
    threading.Thread(target=update_nodes, daemon=True).start()

    # Start the discovery server
    discovery_server()
