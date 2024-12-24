# Distributed File Service Demo Guide

This guide demonstrates the functionality of our distributed file service system. The demo shows file upload, retrieval, and synchronization across multiple servers.

## Server Setup

First, we need to start the servers. Open three separate terminals and run each server:

### Terminal 1 - Starting Server 1
This command connects to the first server through pangolin and starts the file service:
```bash
ssh username@pangolin.it.helsinki.fi
```
```bash
ssh username@svm-11.cs.helsinki.fi
```
```bash
cd ~/distributed-file-service
python3 server.py
```

### Terminal 2 - Starting Server 2
Similar to Server 1, connect and start the service on the second server:
```bash
ssh username@pangolin.it.helsinki.fi
```
```bash
ssh username@svm-11-2.cs.helsinki.fi
```
```bash
cd ~/distributed-file-service
python3 server.py
```

### Terminal 3 - Starting Server 3
Connect and start the service on the third server:
```bash
ssh username@pangolin.it.helsinki.fi
```
```bash
ssh username@svm-11-3.cs.helsinki.fi
```
```bash
cd ~/distributed-file-service
python3 server.py
```

## Demo Commands

Open a fourth terminal for running the demo commands. First, connect to the gateway:
```bash
ssh username@pangolin.it.helsinki.fi
```

### File Operations Demo

1. First, we create a test file with initial content and upload it to Server 1:
Create and upload initial file to Server 1
```bash
echo "Initial test content $(date)" > test.txt
curl -F "file=@test.txt" http://svm-11.cs.helsinki.fi:65421/file/test.txt
```

2. Next, we verify that Server 1 has received and stored the file:
Retrieve file from Server 1
```bash
curl http://svm-11.cs.helsinki.fi:65421/file/test.txt
```

3. We check if Server 3 has synchronized the file (demonstrating file propagation):
Retrieve file from Server 3
```bash
curl http://svm-11-3.cs.helsinki.fi:65423/file/test.txt
```

4. Now we demonstrate file modification by creating and uploading a new version through Server 2:
Create and upload modified version through Server 2
```bash
echo "Modified content $(date)" > test.txt
curl -F "file=@test.txt" http://svm-11-2.cs.helsinki.fi:65422/file/test.txt
```

5. Finally, we verify that Server 1 has synchronized with the new version:
Verify updated content from Server 1
```bash
curl http://svm-11.cs.helsinki.fi:65421/file/test.txt
```
