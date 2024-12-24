import yaml
import socket
import logging
from pathlib import Path

def load_config(config_file='config/config.yaml'):
    try:
        # Load YAML configuration
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Resolve server IP
        server_ip = socket.gethostbyname(config['server']['host'])

        # Resolve discovery server IP
        discovery_ip = socket.gethostbyname(config['discovery']['host'])
        discovery_port = config['discovery']['port']

        # Ensure storage path exists
        Path(config['storage']['path']).mkdir(parents=True, exist_ok=True)

        # Return configuration as a dictionary
        return {
            'HOST': server_ip,
            'PORT': config['server']['http_port'],
            'SOCK_PORT': config['server']['socket_port'],
            'STORAGE': config['storage']['path'],
            'LOG_FILE': config['storage']['log_file'],
            'DISCOVERY_HOST': discovery_ip,
            'DISCOVERY_PORT': discovery_port
        }
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        raise
