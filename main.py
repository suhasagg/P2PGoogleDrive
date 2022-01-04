# acts as the main.py
import socket
import sys 
#from sender import *
#from receiver import *
#from support import *
#from dropbox_peer import Peer

import threading
from upload_download import up_down_thread
from node_connection import heartbeat,send_messages
from random import randint
from main_listener import mainl
from user import user_input, process_user_input, print_output
import socket
import queue
import os
import math
import hashlib
import random
import time
from os import listdir
from os.path import isfile, join
import queue
from support import Neighbor, GlobalInfo, SendToAll

 
def get_checksum(filename):
   
    # print(f'calculating checksum for: {filename}')
    #hash_function = hash_function.lower()
 
    with open(filename, "rb") as f:
        bytes = f.read()  # read file as bytes
        
        try:
            readable_hash = hashlib.sha256(bytes).hexdigest()
        except:
            print("{} is unable to produce a checksum")
 
    return readable_hash

# args - directory of files
# name of the list we want to store variable to

# reads in the file of each user
# Create a list of files and checksum for each file for the user

def get_files(directory):
    user_files = dict()
    list_name = [x for x in listdir(directory) if isfile(join(directory, x))]
    date_modified = {}
    for file in list_name:
        checksum = get_checksum("" + directory + '/' + file)
        user_files[file] = checksum
        date_modified[file] = os.path.getmtime("" + directory + '/' + file)
    return user_files, date_modified
# Synchronize updated files of user to p2p storage   
def update_files(globalInfo, directory,user_files, date_modified):
    while globalInfo.active:
        time.sleep(5)
        list_name = [x for x in listdir(directory) if isfile(join(directory, x))]
        for file in list_name:
            curr_time = os.path.getmtime("" + directory + '/' + file)
            if file not in date_modified or curr_time != date_modified.get(file):
                checksum = get_checksum("" + directory + '/' + file)
                user_files[file] = checksum
                date_modified[file] = curr_time
                msg = f"FILE^{file}^{checksum}"
                globalInfo.message_queue.put(SendToAll(msg))

def get_path(directory):
    path = directory
    return path

def main():
    # main listener ip
    public_ip = get_ip()
    
    # generate random port for main listener
    mainl_port = randint(1024, 65535)
    download_port = randint(1024, 65535)

    # print(f'ip: {public_ip}, port: {mainl_port}')
    print(f'{public_ip}:{mainl_port}')

    filename = sys.argv[1] # dir for users files 
    
    user_files, date_modified = get_files(filename)

    globalInfo = GlobalInfo(public_ip, mainl_port, download_port, user_files,filename)

    self_node = Neighbor(public_ip, mainl_port)

    self_node.files = user_files
    self_node.set_file_receiver(public_ip, download_port)

    globalInfo.self_node = self_node

    globalInfo.all_nodes.add(self_node)

    # a queue that is used to print to the user's stdout


    

    '''
    # fill in the main_listener parameters and stuff
    '''

    # create main listener socket
    main_list_thread = threading.Thread(target=mainl, args=(globalInfo,))
    main_list_thread.setDaemon(True)
    main_list_thread.start()

    # create user_input thread 
    user_thread = threading.Thread(target=user_input, args=(globalInfo,))
    user_thread.setDaemon(True)
    user_thread.start()

    # create user_process_input thread
    user_process_input = threading.Thread(target=process_user_input, args=(globalInfo,))
    user_process_input.start()

    # create thread for heartbeat
    heartbeat_thread = threading.Thread(target=heartbeat, args=(globalInfo, ))
    heartbeat_thread.setDaemon(True)
    heartbeat_thread.start()
    
    # create thread for send_messages
    send_messages_thread = threading.Thread(target=send_messages, args=(globalInfo,))
    send_messages_thread.setDaemon(True)
    send_messages_thread.start()

    response_print_thread = threading.Thread(target=print_output, args=(globalInfo,))
    response_print_thread.setDaemon(True)
    response_print_thread.start()

    # continually update dictionary every five seconds
    update_file_thread = threading.Thread(target=update_files, args=(globalInfo, filename,user_files,date_modified,))
    update_file_thread.setDaemon(True)
    update_file_thread.start()

    # create file download thread
    file_download = threading.Thread(target=up_down_thread, args=(globalInfo.ip,download_port,globalInfo.download_queues,))
    file_download.start()



# From stackexchange: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except OSError:
        IP = '127.0.0.1'
    finally:
        s.close()
    
    return IP



main()
