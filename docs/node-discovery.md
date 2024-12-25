# Node Discovery Service Design
For the purposes of node discovery, we have elected to employ a configurable
address from which the file service nodes receive the addresses of all nodes,
and to whom they send their own liveness information.


## Discovery server features
The discovery node communicates periodically with all file service nodes whose
existence it is aware of. New file service nodes joining the network must
contact the discovery server on startup, and the discovery server drops file
service nodes that it cannot reach after a period of time from its list.

## Joining the discovery service
Each file service node receives the address of the discovery node from a
configuration file.

On startup, a file service node sends to the discovery node a message in the
following format:
```
Join-Discovery-Service <node-address>
```
The discovery service adds the joining node to its list and responds with a
listing of all node addresses it is aware of, and the file service node
immediately takes them to use.

### Fault tolerance
If a file service node does not receive a message from the discovery node in a
reasonable time (measure RTT, 1 second likely enough), it will hold on to its
current listing of node addresses and attempt to re-establish contact with the
discovery node as if joining for the first time.

## Receiving up-to-date node information
The discovery node will periodically send an updated list of node addresses it
is aware of to all node addresses it is aware of. Each node replaces their
internal list with the provided one and responds with a simple OK message to
inform the discovery node of its liveness. If the discovery node does not
receive responses to three successive lists, it will consider the file service
node unresponsive and drop it from its list of addresses.

The listing should use the following header, with the format the lists
themselves taking the form development realities dictate:
```
Peer-Node-Address-Listing\n
```
