# Peer-to-Peer Cloud Storage (Sync.com/pCloud design)

#Peer Priority Support (Neighbour Priority Peers Determination Algorithm) 

1)Btree

2)Binary tree (inorder traversal to determine neighbour priority order)

#File piece Algorithm Support

#Full p2p network layer logging using p2p framework 

https://github.com/suhasagg/python-p2p-network

Contents
---------------------

 * Usage
 * Overall Architecture
 * Modules
 * Files and Functions
 * Message Types
 * Security
 * Details and Assumptions

## Usage

```bash=
pip install pyaes
python main.py <directory>
```

## Overall Architecture

The overall architecture of our implementation involves eight main threads. 
    
#### Main Listener Thread

This thread starts the main listener which listens for messages from other nodes. Once it connects to the other node trying to send a message, it waits to receive (or times out and restarts if the other node is inactive), processes the message (often involves spawning new threads for individual connections or upload/download), and closes the connection so it can receive a new one. 

#### User Input Thread
##Which data is populated in user queue

This thread waits for input from the user and adds it to `user_queue`. 

#### Process User Input Thread

This thread processes the input from the user by reading from `user_queue`. 

#### Heartbeat Thread

This thread sends heartbeats to all direct connections. This heartbeat message is sent every 2 seconds, and it includes all of the current direct connections it has in the message.

#### Send Messages Thread

This message reads from `message_queue` and sends out messages to other nodes. 

#### Response Print Thread

This thread reads from a queue and prints out messages for the user to stdout. 

#### Update File Thread

This thread updates user_files every 5 seconds to ensure we have accurate files and checksums. 

#### File Download Thread

This thread starts the file download listener, used to receive file packets.

### Other Threads

* Sender and receiving threads for each direct connection
* Upload and download threads and a thread to place new download packets into the correct queue. 

## Modules

#### 1. Sender and Receiver from sender and receiver

These are used to send reliable messages from node to node. These are virtually identical to the sender and receiver from lab4.

#### 2. Sender from file_sender and Receiver from file_receiver

These are used to send reliable packets during a file upload and download. They are similar to the other Sender and Receiver except this Sender takes in a random number to add to the beinning of each packet. On the download end, the main download listener uses this number to put the packet into the correct queue. This Receiver takes from a queue instead of reading from the network. 

#### 3. Message

Stores the node object that the message will be sent to & the contents of the message itself. 

#### 4. SendToAll

Stores a message that will be sent to all direct connections.

#### 5. GlobalInfo

Stores information about the current node's state:
* ip, port
* download port
* current files
* message_queue, response_queue, user_queue, download_queues
* all_nodes, my_connections
* active
* directory
* keys

#One user application - if multiple users are uploading, will it shared across multiple users, multiple user support is there

#### 6. Neighbor

Stores information about neighbor nodes, both direct connections and indirect connections. Stores:
* their main listener ip and port
* their last active time
* their sender and receiver
* a dictionary of their files
* their last heartbeat message

## Files and Functions

### [main.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/main.py)

This is the main file that runs. It takes the directory for uploading and downloading as a parameter.

#### `main()`
Runs all the threads
* main listener thread 
* user input thread
* process user input thread
* heartbeat thread
* send messages thread
* print output thread
* update files thread
* upload and download thread

#### `get_checksum(filename)`
Given the filename, get_checksum returns the sha 256 hashed checksum value for the provided file. 

#### `get_path(directory)`
Returns the path of the directory provided in the directory parameter.

#### `update_files(directory,user_files, date_modified)`
Updates the current files of each user every 5 seconds. Also notifies and updates users about added files and files that have been changed.

#### `get_files(directory)`
Takes in the current working directory and reads in the file of each user. 
Then a dictionary of files and checksums are created. Each file is a key while the values are the checksum values. 

#### `get_ip()`
Returns the IP of a socket.

### [user.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/user.py)

This file directly handles the user's stdin and stdout, reading from stdin and print out to stdout.

#### `user_input(globalInfo)`
Reads from stdin and adds the commands the user writes to the user_queue.

#### `process_user_input(globalInfo)`
Gets a user command from the user_queue and looks at its msg type. Then carries out a series of actions according to the type of message that was inputted.

#### `print_output(globalInfo)`
Gets from the user_response queue (which is a queue full of all of the response messages the user has received) and prints the message to stdout.

### [main_listener.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/main_listener.py)

The principal listener socket for a node that handles connection requests & file upload and download messages.

#### `mainl(globalInfo)`
Listens for incoming connection requests. The main listener can respond to 3 message types: CONN, SMFX ('send me file x'), and SDFX ('sending file x'). This function spawns threads to handle the different commands. If the main listener receives a SDFX message, it checks to see if it needs the file that another node wants to send to it & if it does, it sends a SMFX message back to the sending node's main listener.

#### `add_node(dest_ml_ip, dest_ml_port, download_port, port_their_receiver, port_my_receiver, globalInfo, recovery_connection)`
This function is called from mainl(). It creates a 1:1 connection with another node, spawning both sender and receiver threads to handle communication with the other node (it also creates new sender and receiver sockets for the connection)

### [upload_download.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/upload_download.py)

#### `up_down_thread(ip,port, download_queues)`

The main download listening thread that each download packet is sent to. It initializes the socket and starts the add_to_queue thread. 

#### `add_to_queue(sock, download_queues)`

This is a helper thread that, based on the first number in the packet, places this packet into a queue in download_queues to be accessed by the Receiver later.

#### `upload_thread(filename, IP, PORT, num)`

This thread creates a Sender to send the file, and sends the file. It uses upload_helper to receive and process acks from the receiver. 

#### `upload_helper(send)`

A helper thread for upload_thread that receives and processes acks for the Sender until the Sender is finished sending and disconnects.

#### `download_thread(filename,num,download_queues,directory)`

This thread initializes a new Receiver using the queue corresponding to num and reads in packets using the receiver to build the new file. 

### [node_connection.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/node_connection.py)

#### `sender_thread(globalInfo, recovery_connection, node)`

This sender_thread first starts by telling the other node its network and file information. Afterwards, it just receives and processes acks from the receiver until the sender thread is closed. Other methods send the messages that this sender_thread receives acks for. 

#### `receiver_thread(globalInfo, neighbor)`

The receiver_thread processes messages that come in from direct connections and acts accordingly.

#### `add_from_network_msg(splitMsg, globalInfo, neighbor)`

This method processes the information from a TIMN message, adding in the files and checksome for each node.

#### `is_guy_in_network(ip, port, all_nodes)`
 
This method returns whether a node is already in the network. 

#### `heartbeat(globalInfo)`

This method sends out a heartbeat message of type SendToAll every two seconds. The heartbeat message contains a list of all of the node's current direct connections, to be used later if the node disconnects. 

#### `send_messages(globalInfo)`

This method reads messages from message_queue and sends them to the correct nodes in the network.

#### `handle_node_leaving(node_left_ip, node_left_port, globalInfo, directConnection)`

This method handles a node leaving, sending LEFT messages to all of its neighbors, and initiating new connections if needed. After a node leaves, all of its previous direct connections connect to eachother. The node with the higher port number initiates the connection between each pair. 

#### `user_add(globalInfo, dest_ip, dest_port, recovery_connection)`

This method responds to a new user add. It makes a new sender and receiver for the direct connection, sends a CONN message, and begins the sender and receiver threads. 

### [support.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/support.py)

This file contains the Message, SendToAll, and GlobalInfo modules described above. 

### [encryption.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/encryption.py)

#### `encrypt(i)`

This method takes in the byte message i and encrypts it using the secret key. 

#### `decrypt(i)`

This method takes in the encrypted byte message i and decrypts it using the secret key.

### [sender.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/sender.py), [receiver.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/receiver.py)

These sender and receivers implement the mrt_layer abstract methods and others.

Methods used include:
* mrt_connect()
* mrt_accept1()
* mrt_send()
* update()
* process_data()
* mrt_disconnect()
* mrt_receive()

### [file_sender.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/file_sender.py), [file_receiver.py](https://git.dartmouth.edu/f003djh/cosc60-final-project/-/blob/master/file_receiver.py)

These two files are used in the uploading and downloading of files. They contain the abstract methods necessary for a mini-reliable transport later. 

## Message Types

The following message types are associated with each one of the user's actions. 

#### ADD Command
##### Typed by the user:

* `ADD <dest_ip:dest_port>`
The connect message is sent to the destination node after the user writes an ADD message.

#### LIST Command

##### Typed by the user:

* `LIST`
The list command prints all of the files that are in t##### Sent by the network:

* **New connection message:** `CONN^<main listener IP >^<main listener port>^<download port>^<my new receiver port>^<port of other node's receiver for 1:1 connection>^<recovery connection variable>`
A node sends this message after the user types an ADD message to try to make a direct connection with the destination node. 
When a node's main listener receives a connect message, it sets up a 1:1 connection & then sends a `TIMN` message. When the other node receives the TIMN message, it sends back a TIMN message of its own.
* **This is my network message:** `TIMN^<sender ip>^<sender port>^<sender's local files...>^<the ip & ports of other nodes in your network + the files they store locally...>`
A node sends this message out when it makes a new direct connection. When this message is receieved, it is parsed and all_nodes is updated.

he network to stdout.

#### GET Command

##### Typed by the user:

* `GET <filename>`

The GET command prompts a search through the list of files in the network. If the file exists in the network, the node sends a `SMFX` message to the main listener of the node that has the file. 

##### Sent by the network:

* **Send me file X message**: `SMFX^<sender's ip>^<sender's download port>^<filename>^<random generated number for file transfer>`
This message is sent by nodes that want a specific file. In the SMFX message, a random generated number is included, which corresponds to the upload/download pair and is used in the download_thread. When this message is receieved, a new upload thread is started with a Sender that knows the random generated number. 

### SEND Command

##### Typed by the user:

* `SEND <filename>`
The SEND command sends a file to all other users, as long as the sending node actually has the file. If other users want this file, they request it by sending back a `SMFX` message. 

##### Sent by the network:

* **Sending file X message:**`SDFX^<sender's main listener ip>^<sender's main listener port>^<filename>^<file checksum>`
This message is sent to all other nodes whenever a user uses the send command. When received, a node can decide either that they want the file and send a `SMFX` message or just simply ignore the `SDFX` message.

### Other message types sent:

##### Sent by the network:

* **New change in files message:**`FILE^<filename>^<checksum>`
This message is sent to all direct connections whenever there is a change (file update or new file) in the user's file directory. 
When this message is received: if this is new information, the received node updates its list of files in each node and sends this file change to all of its direct connections. If this is not new information, the node does not propogate the message.

* **Node leaving message:**`BYEF^<sender main listener ip>^<sender main listener port>`
This message is sent to all direct connections when a user types BYE. The program then proceeds to end all individual connections and exit. 
When this message is receieved, the `handle_node_leaving` method is called, which removes the node from all nodes, informs others if this is new information, and if this is a direct connection, starts the protocol to reform a connection (connect with all nodes that were previously direct connections of the node that left).

## Security

In order to provide security, we offer encryption and decryption for all of the packets sent. We implemented symmetric key encryption in order to protect the messages from malicious nodes that are outside the network and might try to intercept & read the data that's being sent. Therefore, only nodes that are running our program know the symmetric encryption key and can encrypt/decrypt messages. We acknowledge that if you can see our code, you can see the key.

## Details and Assumptions

* After adding a new node, it takes a up to five seconds for the lists of files to sync. 
* After removing a node, it takes up to ten seconds for the lists of files to sync. This is because it can take a while for the new connections to be made.
* We are only compatable with our implementation.
* Assume that when you send a file, you will send whatever version you have. When you are receiving a file that's being sent, as long as you don't have that file or the incoming file has a different checksum than your current version, you will accept it. 
* We assume that there are not malicious people trying to send random commands to our main listener.

