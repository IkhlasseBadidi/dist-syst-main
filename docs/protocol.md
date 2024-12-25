# The Protocol Details
The service uses two distinct ways of communication, HTTP with the client and
plaintext messages over TCP between nodes.


## Server-to-server communication
The server nodes communicate between themselves when the user initiates a
download request from one of them. At this point the server nodes establish
between themselves which of them holds the most recent version of the
requested file, if any does.

Once this is established, the server serving the client will fetch the file
from another server if needed and serve it to the client.

As such, the protocol needs to support both the checking of existence and
timestamps in one call, and the request to provide data to another node in
another. Should time allow, the idea of a file name set index has also been
discussed as a third feature.

### Behaviour on checking for modification time
To ensure the most recent file is provided, the server contacts its peers with
a version check message. The message follows the format
`Last-Modified-Check <filename>`.

The peer servers respond to the query with
`Last-Modified <filename> <timestamp> <node-address>`.

### Behaviour on fetching files
To request the most recent version of the file from its peer, the server sends
a message containing `File-Provision-Request <filename>` to which the other
server answers by `File-Provision <filename>\n <file data>`.

### Behaviour on forming the file index
To request a listing of all the files on the service, a server sends out the
message `Index-Listing-Request` to its peers.

The peers respond to this with a message beginning with the line `Index-Listing`
and followed by all the filenames present on that node separated by linebreaks,
e.g.
```
Index-Listing
file1
file2
file3
file4
```

## Client-to-server-to-client communication
The client establishes connection to the server with a message following the
HTTP protocol. The server accepts `GET` and `POST` requests, and rejects all
other types with `405` status.

### GET request
On a `GET` request, the user expects to receive a file. The servers establish
which of them has the most recent file and then provide it to the client. We
respond with code `404` if no such file exists, or `200` with the requested
data if the file is found from the service.

A request from the client should be formatted in the way that the URI-path
includes the filename after the server address, and little else.

### POST request
On a `POST` request, the user sends a file to the service. The server accepts
and stores the file, returning `204` and no further content. The servers do NOT
immediately share the file between one another, but wait for it to be requested
instead.

A request from the client should be formatted so that it includes the desired
filename and actual file contents as form fields in the POST request. The field
names to use are `name` for the filename and `file` for the contents. Processing
the input as form data allows the upload of binary files and allows us to avoid
URL-encoding all the inputs.

## Peer node discovery
The details of peer node discovery are provided in
[associated solution documentation](node-discovery.md).
