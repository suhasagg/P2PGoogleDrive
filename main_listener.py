# CS 60
import select
import socket
from support import Message, Neighbor,SendToAll
from receiver import Receiver
from sender import Sender
from upload_download import download_thread,upload_thread
import threading
import time
import queue
from node_connection import receiver_thread, sender_thread, user_add
import random

# main_listener can only deal with one sender at a time5
def mainl(globalInfo):

    src_ip = globalInfo.ip
    src_port = int(globalInfo.port)

    # print(f'main receiver: {src_ip},{src_port}')

    while True:
        receiver = Receiver(src_ip, src_port,)
        # first establish a connection with sender
        receiver.mrt_accept1()
        ack = receiver.mrt_recieve_timeout(.5)
        msg = receiver.mrt_recieve_timeout(.5)
        # if is an ack or timeout
        # msg = globalInfo.encryption.decrypt(encrypted_msg)
        if msg == '' or ack == 0 or msg is None: 
            continue
        
        # add message
        # if is_rkey_msg == 'RKEY':
        #     payload = encrypted_msg[5:].split('^')
        #     dest_ml_ip = payload[0]
        #     dest_ml_port = payload[1]
        #     sender_pub_key = payload[2]
        #     globalInfo.keys[(payload[0], payload[1])] = sender_pub_key
        #     give_key_msg = f'GKEY^{src_ip}^{src_port}^{str(globalInfo.encryption.pub_key)}'
        #     key_send_thread = threading.Thread(target=send_key, args=(dest_ml_ip, dest_ml_port, give_key_msg,))
        #     key_send_thread.start()
            
        # parse message
        msg_type = msg[0:4]
        payload = msg[5:].split('^')
        dest_ml_ip = payload[0]
        dest_ml_port = payload[1]
        
        # if msg_type == 'GKEY':    
        #     sender_pub_key = payload[2]
        #     globalInfo.keys[(payload[0], payload[1])] = sender_pub_key
        #     user_add_thread = threading.Thread(target=user_add,args=(globalInfo, dest_ml_ip, dest_ml_port, False))
        #     user_add_thread.run()
            

        if msg_type == 'CONN':
            their_download_port = payload[2]
            port_their_receiver = payload[3]
            port_my_receiver = payload[4]
            if payload[5] == "True": 
                recovery_connection = True
            else: 
                recovery_connection = False


            thread_add = threading.Thread(target=add_node, args=(dest_ml_ip, dest_ml_port, their_download_port, port_their_receiver, port_my_receiver, globalInfo, recovery_connection, ))
            thread_add.start()

            # print(f'their receiver: {port_their_receiver}, my receiver: {port_my_receiver}')

        # get message
        # Get file command sent to Outgoing node, Upload file process is triggered on Outgoing node
        # File chunks are further granulated into packets and sent to incoming Node over UDP connection
        if msg_type == 'SMFX':
            filename = payload[2]
            random_num = payload[3]
            download_port = dest_ml_port
            filepath = "" + globalInfo.directory + '/' + filename
            thread_upload = threading.Thread(target=upload_thread, args=(filepath, dest_ml_ip, download_port,int(random_num)))
            thread_upload.start()

        # Send message
        # Send message command is triggered by Node which received the Get File command
        # Download thread is activated on the node, which assembles packets received into a single file
        # Send file command can be used to replicate file chunks on peers. Neighbour peers can be stored in btree (for peer priority based on peer distance calculated using multiple parameters geography, uniform spread)
        # A simple data structure like binary tree can also be used to store neighbour peers (inorder traversal of the tree will give neighbour peers in order)
        # Application of using binary tree is to optimise routing table storage and processing times
        if msg_type == 'SDFX':
            filename = payload[2]
            new_checksum = payload[3]
            download_file = True
            file_exist = False
            if filename in globalInfo.user_files:
                old_checksum = globalInfo.user_files.get(filename)
                if new_checksum == old_checksum:
                    download_file = False
            file_exist = True

            if not file_exist:
                # add file to your user_files list
                globalInfo.user_files.append((filename, new_checksum))
            
            if download_file:
                    # rand num used just for this file exchange
                    rand_file_num = 10000 + int(random.random()*90000)
                    globalInfo.download_queues[rand_file_num] = queue.Queue()
                    msg = f"SMFX^{src_ip}^{globalInfo.download_port}^{filename}^{rand_file_num}"
                    single_use_sender = Sender(dest_ml_ip, dest_ml_port)
                    single_use_sender.mrt_connect()
                    single_use_sender.mrt_send(msg)
                    data = single_use_sender.mrt_recieve1()
                    single_use_sender.process_data(data)
 
                    end_on_finish = threading.Thread(target=single_use_sender.mrt_disconnect,args=())
                    end_on_finish.start()
                    thread_download = threading.Thread(target=download_thread, args=(filename,rand_file_num,globalInfo.download_queues,globalInfo.directory,))
                    thread_download.start()
        
        while receiver.on:
            receiver.mrt_recieve1()


def add_node(dest_ml_ip, dest_ml_port, download_port, port_their_receiver, port_my_receiver, globalInfo, recovery_connection):
    # do we need to check to see if the node already exists in the all_nodes list?
    # or do we not need to worry about a case like this?
    
    # create sender for to communicate with new peer
    sender = Sender(dest_ml_ip, port_their_receiver)

    # create dest_node, giving ip and port of the node who sent the connect msg.
    # this isn't right huh because they don't provide their listener port in msg
    
    dest_node = Neighbor(dest_ml_ip, dest_ml_port)
    dest_node.set_sender(sender)
    dest_node.set_file_receiver(dest_ml_ip,download_port)
    
    # creates msg containing network

    # create receiver thread here 
    receiver = Receiver(globalInfo.ip, port_my_receiver)
    dest_node.set_receiver(receiver)
    
    thread_sender = threading.Thread(target=sender_thread, args=(globalInfo, recovery_connection, dest_node,))
    thread_sender.setDaemon(True)
    thread_sender.start()

    thread_receiver = threading.Thread(target=receiver_thread,args=(globalInfo, dest_node,))
    thread_receiver.setDaemon(True)

d_receiver.start()
