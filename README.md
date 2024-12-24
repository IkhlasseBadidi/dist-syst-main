# Distributed File Service

A distributed file system implementation created as the final project for the Distributed Systems course at the University of Helsinki.

## Team Members
- Ikhlasse Badidi
- Reetta Himanka
- Henri Peurasaari

## Project Overview

This project implements a distributed file system that enables seamless file storage and retrieval across multiple server nodes. The system is designed to be reliable, consistent, and scalable while demonstrating key distributed systems concepts.

### Core Features

- File upload and download through a simple HTTP interface
- Automatic file versioning using timestamps
- Dynamic node discovery and peer management
- Transparent file synchronization across nodes
- Basic fault tolerance through timeout mechanisms
- Reactive replication strategy for efficient resource usage

## Architecture

The system employs a flat hierarchy where all server nodes are peers, communicating directly with each other to maintain file consistency. The architecture consists of:

- **Server Nodes**: Python-based servers handling both client requests and inter-server communication
- **Discovery Service**: Manages node membership and network topology
- **Client Interface**: HTTP-based interface supporting standard curl commands
- **Storage Layer**: Local file storage with timestamp-based versioning

## Key Design Principles

### Communication Flows

The system implements two primary communication patterns:

1. **POST Flow**: Simple direct file storage with atomic write operations
2. **GET Flow**: Version-aware retrieval with peer consultation for latest file versions

### Synchronization and Consistency

- Timestamp-based version control
- Peer-to-peer version checking
- Automatic synchronization of newer file versions
- Protocol messages for version checking and file transfer

## Usage

The system supports standard HTTP operations:
- File uploads via POST requests
- File downloads via GET requests

## Scalability and Performance

### Current Capabilities
- Dynamic node addition
- Independent node operation
- On-demand synchronization
- Efficient version checking protocol

### Limitations
- Network bandwidth requirements for file transfers
- Version check overhead with increasing node count
- Storage capacity limitations of individual nodes

## Best Use Cases

The service performs optimally when:
- Load is roughly equally balanced between nodes
- Files are fetched more frequently than updated
- Individual file sizes are relatively small

## Future Improvements

Potential enhancements include:
- Adding caching mechanisms
- Optimizing the version check protocol
- Introducing regional node grouping

## Technical Requirements

- Python
- HTTP server capabilities
- YAML for configuration management

## Project Context

This project was developed as part of the Distributed Systems course at the University of Helsinki, demonstrating practical implementation of distributed systems concepts including shared state management, synchronization, consensus mechanisms, and node discovery protocols.

## Contribution Credits

- **Henri Peurasaari**: System architecture design and protocol planning
- **Ikhlasse Badidi**: Technical implementation, coding, and testing
- **Reetta Himanka**: Technical implementation, coding, and testing

