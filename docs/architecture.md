# Architecture Plan
2024-10-31: The project aims to provide the distributed file service through
multiple server nodes communicating with one another in a flat hierarchy. The
client is proposed to be any client that may send proper HTTP requests.

## Server Nodes
The server nodes are presented in a flat hierarchy. Communication between nodes
happens when users wish to download content from the service, which is when the
nodes form a consensus of where the latest modified version of the file is
situated and it is downloaded to the node the user accesses the file from, and
then sent to the user via this server. Each of the nodes thus serves as a
storage for data and as an access point to the data for the client.

### Communication with the client
The client connects to one of the server nodes and poses an HTTP request. The
details of the types of requests and how they are to be served can be found
in [the protocol documentation](protocol.md).

### Communication between servers
The server nodes communicate between one another with an application specific
protocol via sockets. Further details can be found in
[the protocol documentation](protocol.md).

### Fault tolerance
As nodes may die or lose connection from the rest, we establish a timeout for
requests after which a response will no longer be expected.

## Client
No special client is in the works. Currently the team is opting to use `curl`
for testing and further operation with the system as a readily accessible
HTTP client with little overhead.
