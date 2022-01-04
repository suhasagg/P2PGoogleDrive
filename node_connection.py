import socket 
from sender import Sender
from receiver import Receiver
from support import Message, SendToAll, Neighbor
import queue
from random import randint
import time 
import select
import threading


# takes in a sender and receives its acks etc
def sender_thread(globalInfo, recovery_connection, node):
    # print("sender thread! my port is " + str(src_port))

    send = node.get_sender()
    send.mrt_connect()


    if not recovery_connection: 
       
        net_msg = f'TIMN^{globalInfo.ip}^{globalInfo.port}^'
        # loops over all nodes in user's current network
        for n in globalInfo.all_nodes:
            # node = Neighbor(node)
            # there is a difference between main listener ip and individual ip
            nbr_addr = n.get_info()
            net_msg += nbr_addr[0] + "&" + str(nbr_addr[1])
            list_of_files = n.get_file_list()
            for file in list_of_files:
                net_msg += '&' + file + '&' + list_of_files[file]
            
            net_msg += '^'

        # globalInfo.all_nodes.add(node)
        

        net_msg = net_msg[:-1] # remove the last ^

        id_msg = Message(node, net_msg)
        # print(f'node, {node}, msg, {net_msg}')
        globalInfo.message_queue.put(id_msg)

    globalInfo.my_connections.add(node)

    # print(node.get_sender())

    while send.connected == True and globalInfo.active:
        reading, writing, closing = select.select([send.s],[send.s],[send.s])
        
        for sock in reading:
        # if reading from stdin 
            if sock is send.s:
                try: 
                    data = send.mrt_recieve1()
                    send.process_data(data)
                except: 
                    if not globalInfo.active: 
                        return 

        for sock in writing:
            send.update()

def receiver_thread(globalInfo, neighbor): 

    receiver = neighbor.get_receiver()

    receiver.mrt_open()

    # print('before accept')

    receiver.mrt_accept1()
    # print('after accept')


    while receiver.on: 
        # print("top of recv thread")
        try: 
            message = receiver.mrt_recieve1()

        except: 
            if not globalInfo.active: 
                return
            break

        # message = globalInfo.encryption.decrypt(encrypted_message)

        if message:
            splitMsg = message.split("^")

            if splitMsg[0] == "BYEF": 
                handle_node_leaving(splitMsg[1], splitMsg[2], globalInfo, True)
              
            if splitMsg[0] == "FILE":
                filename = splitMsg[1]
                checksum = splitMsg[2]
                tell_others = False
                for node in globalInfo.all_nodes:
                    if node.has_file(filename) and node.files.get(filename) == checksum:
                        continue
                    else:
                        node.files[filename] = checksum
                        tell_others = True

                if tell_others:
                    msg = f"FILE^{filename}^{checksum}"
                    globalInfo.message_queue.put(SendToAll(msg))

            # This is one of your connections telling you one of their connections left
            if splitMsg[0] == "LEFT": 
                handle_node_leaving(splitMsg[1], splitMsg[2], globalInfo, False)
                
                
            if splitMsg[0] == "JOIN" and (int(splitMsg[2]) != globalInfo.port or splitMsg[1] != globalInfo.ip): 
                # check our set of users to see if this guy's information is new
                msg_ip = splitMsg[1]
                msg_port = splitMsg[2]

                if is_guy_in_network(msg_ip, msg_port,globalInfo.all_nodes) is None: 

                    add_from_network_msg(splitMsg, globalInfo, neighbor)

                    globalInfo.message_queue.put(SendToAll(message))

            if splitMsg[0] == "TIMN": 
                ## MSG FORMAT: 
                ## nodes are delimited by ^
                
                add_from_network_msg(splitMsg, globalInfo, neighbor)
                join_msg_string = "JOIN" + message[4:]
                globalInfo.message_queue.put(SendToAll(join_msg_string))

                   
                        
            if splitMsg[0] == "HB":
                neighbor.last_active = time.time()
                neighbor.last_heartbeat = message

def add_from_network_msg(splitMsg, globalInfo, neighbor):
    for i in range(3, len(splitMsg)): 
        innerSplitMsg = splitMsg[i].split("&")
        ip = innerSplitMsg[0]
        port = innerSplitMsg[1]

        # if isn't self
        if not (ip == globalInfo.ip and int(port) == int(globalInfo.port)):

            
            if ip == neighbor.get_info()[0] and int(port) == int(neighbor.get_info()[1]): 
                node = neighbor

            else: 
                node = Neighbor(ip, port)

            
            for j in range(2, len(innerSplitMsg),2): 
                # TODO: change 0 to checksum
                
                node.files[innerSplitMsg[j]] = innerSplitMsg[j+1]
                        
            globalInfo.all_nodes.add(node)




def is_guy_in_network(ip, port, all_nodes):
    # loop over 
    
    for node in all_nodes: 
        node_ip, node_port = node.get_info()
        if ip == node_ip and port == node_port:
            return node
    return None  


# sends heartbeats every two seconds
def heartbeat(globalInfo):
    # send heartbeat
   
    while globalInfo.active: 
        msg = "HB"

        temp_my_connections = set(globalInfo.my_connections)
        for node in temp_my_connections:

            if time.time() - node.last_active > 10:
                neighbor_ip, neighbor_port = node.get_info()
                handle_node_leaving(neighbor_ip, neighbor_port, globalInfo, True)
            else:
                ip,port = node.get_info()
                msg += f"^{ip}&{port}"
      
        globalInfo.message_queue.put(SendToAll(msg)) 
      

        # check to see if anyones inactive
        time.sleep(2)

# sends any messages in message_queue
def send_messages(globalInfo):
    while globalInfo.active: 
        action = globalInfo.message_queue.get()
        

        if isinstance(action, Message): 
            # handle message
            node,msg = action.get_info()
            
            # MADE ENCRYPTION CALL
            # encrypted_msg = globalInfo.encryption.encrypt(msg)

            # node.get_sender().mrt_send(msg)
            node.get_sender().mrt_send(msg)
            
        if isinstance(action, SendToAll): 
            copy = set(globalInfo.my_connections)
            for node in copy:
                # check to see if node is self
                new_ip, new_port = node.get_info()
                if(not (new_ip == globalInfo.ip and int(new_port) == int(globalInfo.port))):
                    msg = action.msg()                    
                    node.get_sender().mrt_send(msg)

            

def handle_node_leaving(node_left_ip, node_left_port, globalInfo, directConnection): 
    # This gets called when we detect a BYE or a ctrl c
    # We should have ports + IP's of everyone that was connected to this person who left
    # Look at stored heartbeats (node_who_left.last_heartbeat)
    # check before node is removed, if it is part of the network
    node_who_left = is_guy_in_network(node_left_ip, node_left_port, globalInfo.all_nodes)
    # if node is part of network and is timed out (high downtime above threshold)
    if node_who_left:
        globalInfo.all_nodes.remove(node_who_left)
        # Node is removed and left message is sent to all the peers
        message_string = "LEFT^" + node_left_ip + "^" + node_left_port
        globalInfo.message_queue.put(SendToAll(message_string))


        if directConnection: 
            globalInfo.my_connections.remove(node_who_left)
            thread = threading.Thread(target=node_who_left.sender.mrt_disconnect,args=())
            thread.start()
            neighbors = node_who_left.last_heartbeat.split("^")
            neighbors = neighbors[1:] # remove HB and X padding
        
            length = len(neighbors)

            # if we're the only connection, do nothing
            if length == 1:
                return

            for i in range(length):
                neighbors[i] = neighbors[i].split("&")

            # max port
            # if we're the highest of the neighbors
            highest_port_index = 0
            lowest_port_index = 0
            for i in range(1, length):
                if neighbors[i][1] > neighbors[highest_port_index][1]:
                    highest_port_index = i
                if neighbors[i][1] < neighbors[lowest_port_index][1]: 
                    lowest_port_index = i

            if globalInfo.ip == neighbors[highest_port_index][0] and int(globalInfo.port) == int(neighbors[highest_port_index][1]): 
                thread1 = threading.Thread(target=user_add, args=(globalInfo, neighbors[lowest_port_index][0], neighbors[lowest_port_index][1], True,))
                thread1.run()


# the requester side of add
def user_add(globalInfo, dest_ip, dest_port, recovery_connection):
    # announce to everyone that someone new joins

    # connect to their main listener
    # make single use sender
    single_use_sender = Sender(dest_ip,dest_port)
    single_use_sender.mrt_connect()

    recv = Receiver('',0)
    ip,port = recv.ip_port


    port = int(port)
    
    send = Sender(dest_ip,port+1)

    conn_msg = f"CONN^{globalInfo.ip}^{globalInfo.port}^{globalInfo.download_port}^{port}^{str(port + 1)}^{recovery_connection}"

    
    # CALL ENCRYPTION CLASS TO ENCRYPT MSG HERE
    # encrypted_msg = globalInfo.encryption.encrypt(conn_msg)

    single_use_sender.mrt_send(conn_msg)
    data = single_use_sender.mrt_recieve1()
    single_use_sender.process_data(data)
 
    end_on_finish = threading.Thread(target=single_use_sender.mrt_disconnect,args=())
    end_on_finish.start()

    new_node = is_guy_in_network(dest_ip, dest_port, globalInfo.all_nodes)
    if new_node is None: 
        new_node = Neighbor(dest_ip,dest_port)
    new_node.set_receiver(recv)
    new_node.set_sender(send)

    ## exchange information
    recv_thread = threading.Thread(target=receiver_thread, args=(globalInfo, new_node,))
    recv_thread.setDaemon(True)
    recv_thread.start()
    send_thread = threading.Thread(target=sender_thread, args=(globalInfo, recovery_connection, new_node,))
    send_thread.start()

    