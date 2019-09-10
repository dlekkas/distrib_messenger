# Distributed Group Messenger

## Introduction
This project is a terminal-based group messenger operating on a P2P basis for messaging operations and on a client-server basis for control operations. 

Each client can participate in one or more available group chats (concurrently) while an external tracker ensures the system stability by monitoring health and taking care of group access policies. Two distinct distributed ordering protocols were implemented to preserve the order of messages.

## System Decisions
Clients within the same group are exchanging messages using the UDP protocol since fast delivery is our priority over reliability. The messages are sent using B-Multicast. Each client maintains for each group a list of all the members of the group. This data structure facilitates the delivery of messages to other clients since a simple iteration over the list is sufficient to communicate the message to others using B-Multicast.

Since a messenger application has to be reliable with respect to the order of the messages we tried two distributed ordering protocols with different trade-offs:
### FIFO Ordering
This type of ordering was achieved by using Lamport timestamps. Each client maintained for each pair of (username,group name), a lamport timestamp initialized to zero. When a client is sending a message to a group then the associated timestamp is incremented by one. When a client receives a message from a user and group then he checks the timestamp of the corresponding pair to ensure that the message received contains a lamport timestamp that is the exact next from the one that receiver already had. In such scenario the message is delivered and presented to the terminal (UI). If that is not the case, the message is buffered until the condition is met.
The data structure used to implement this type of ordering is hash-table (dictionary) for each client where the key is a tuple of username and group name. Each client along its message is also sending its associate lamport timestamp.

### FIFO + Total Ordering
This ordering policy is a more strict variation of the FIFO protocol implemented above. In that sense, the ordering of events is trivial with respect to the ordering of each client's messages but when a universally acceptable order does not exist (the events occur "at the same time") then a consensus is required to ensure that every client perceives the same ordering of messages. This type of ordering is achieved by implementing the ISIS algorithm.


## Centralized Tracker
The communication between clients and tracker is implemented using TCP messages since the reliability is vital to ensure system's stability. More specifically, tracker is implemented to support 6 interactive control operations:

(When a message of a client begins with exclamation mark (!) the message is interpreted as a command and is sent to the tracker)


|Command              |     Description          | 
|----------------|-------------------------------|
|`!g`		  |Display the names of the active groups          |
|`!lm <groupname` |Display the usernames of this group's members          |
|`!j <groupname>` |Joins the specified group      |
|`!w <groupname>` |Declares to which group the following messages will be sent	|
|`!e <groupname>` |Leaves the specified group |
|`!q <groupname>` |Exits the application|

Apart from dispatching the interactive commands the tracker is also responsible to asynchronously inform clients for new members or when members exit a group.

Additionally, for the purpose of this system the clients inform the tracker with various messages regarding performance to capture significant metrics to evaluate the performance of the system.
Specifically, the system logs whenever a client exits the application the following metrics:
*  Message Throughput
*  Message Latency
*  Total messages sent
*  Total messages received
*  Total number of messages exchanged


Finally, tracker performs health monitoring to  ensure system's stability with health checks. Those checks are implemented using heartbeats sent to each registered client. Failure of a client to respond to the heartbeat means his automatic de-registration of any group he belonged. A client to recover such failure would need to join again each group he belonged to.

## Usage
Firstly, host the tracker somewhere (by default it assumes localhost):
`python2 tracker.py`

Second, connect a client and follow the prompts of the application:
`python2 demo.py`

Third, distribute to your friends and enjoy!
