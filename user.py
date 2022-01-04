import sys
import queue
import threading
from receiver import Receiver
from support import Neighbor, Message, SendToAll
from sender import Sender
import select
from node_connection import user_add
import upload_download
import time
import random

# thread to take in user input
def user_input(globalInfo):
    print("Type 'CMDS' to see the full list of commands you can use.")
    line = ""
    while globalInfo.active:
        time.sleep(.01)
        try:
            line = sys.stdin.readline()
        except:
            # exception occurs when user types ctrl + c.
            globalInfo.response_queue.put("Disconnecting from network...")
            return

        globalInfo.user_queue.put(line[:len(line)-1])
    

# thread to process user input
def process_user_input(globalInfo):
    while globalInfo.active: 
        msg = globalInfo.user_queue.get() # this should be blocking
        command = msg[0:4]

        if command == "ADD ":
            dest_ip = msg[4:].split(":")[0]
            dest_port = msg[4:].split(":")[1]

            request_key_thread = threading.Thread(target=user_add,args=(globalInfo, dest_ip, dest_port, False,))
            request_key_thread.start()
            
        elif command == "LIST":
            # assume nodes send when their directory changes and 
            # thread constantly checks to see if folder reasdy
            files = set()
           
            for node in globalInfo.all_nodes:
                file_list = node.get_file_list()
                for file in file_list:
                    files.add(file)
            file_string = ""
            for file in files:
                file_string += file + "\n"
            # chop off last newline character
            file_string = file_string[:len(file_string)-1]
            globalInfo.response_queue.put(file_string)
        elif command == "GET ":
            filename = msg[4:]
            for node in globalInfo.all_nodes:
                ip,port = node.main_listener
                if(node.has_file(filename) and not (ip == globalInfo.ip and int(port) == int(globalInfo.port))):
                    # run download thread
                    mainl_ip_port = node.get_info()
                    mainl_ip = mainl_ip_port[0]
                    mainl_port = mainl_ip_port[1]
                    rand_file_num = 10000 + int(random.random()*90000)
                    msg = f"SMFX^{globalInfo.ip}^{globalInfo.download_port}^{filename}^{rand_file_num}"
                    globalInfo.download_queues[rand_file_num] = queue.Queue()
                    single_use_sender = Sender(mainl_ip, mainl_port)
                    single_use_sender.mrt_connect()
                    single_use_sender.mrt_send(msg)
                    data = single_use_sender.mrt_recieve1()
                    single_use_sender.process_data(data)
 
                    end_on_finish = threading.Thread(target=single_use_sender.mrt_disconnect,args=())
                    end_on_finish.start()
                    thread_download = threading.Thread(target=upload_download.download_thread, args=(filename, rand_file_num,globalInfo.download_queues, globalInfo.directory, ))
                    thread_download.start()
                    break

        elif command == "SEND":
            filename = msg[5:]
            # send to every neighbor
            if filename in globalInfo.user_files:
                for node in globalInfo.all_nodes:
                    ip,port = node.main_listener
                    # Sending to every node which is not in global info IP, global info Port
                    if not (ip == globalInfo.ip and int(port) == int(globalInfo.port)):
                        # run download thread
                        mainl_ip_port = node.get_info()
                        mainl_ip = mainl_ip_port[0]
                        mainl_port = mainl_ip_port[1]
                        rand_file_num = 10000 + int(random.random()*90000)
                        to_send = f"SDFX^{globalInfo.ip}^{globalInfo.port}^{filename}^{globalInfo.user_files.get(filename)}"
                        single_use_sender = Sender(mainl_ip, mainl_port)
                        single_use_sender.mrt_connect()
                        single_use_sender.mrt_send(to_send)
                        data = single_use_sender.mrt_recieve1()
                        single_use_sender.process_data(data)
    
                        end_on_finish = threading.Thread(target=single_use_sender.mrt_disconnect,args=())
                        end_on_finish.start()

        elif command == "BYE":
            print("this guy is leaving")
            msg_string = "BYEF^" + globalInfo.ip + "^" + str(globalInfo.port)
            msg = SendToAll(msg_string)
            globalInfo.message_queue.put(msg)
            globalInfo.active = False
            for node in globalInfo.my_connections:
                # time.sleep(2)
                node.get_sender().unacked = []
                thread1 = threading.Thread(target=node.get_sender().mrt_disconnect,args=(''))
                thread1.setDaemon(True)
                thread1.start()
            
            print("closed everyone!")
            return 

        elif command == "CMDS":
            commands = "\nCommands available: \n"
            commands += "ADD <new neighbor IP>:<new neighbor port>\n • Adds a new node connection.\n"
            #Display cumulative files stored across every node
            commands += "LIST\n • Lists the files that are currently available.\n"
            #Maintains file version history or latest version
            #a)Single file available across multiple nodes
            #b)Set of files distributed across multiple nodes
            commands += "GET <filename>\n • Download a the most recent version of a file.\n"
            #P2P Storage client - specify file path (synchronise file to peers based on peers (neighbour peers) derivation algorithm)
            #Suffixes,Prefixes to use appropriate protocol (for different type of exchanges - send,receive)
            commands += "SEND <filename>\n • Send everyone your most recent version of a file.\n"
            #Exit code - if you are exiting the network
            commands += "BYE\n • Leave the network and inform everyone.\n"
            globalInfo.response_queue.put(commands)

        else:
            globalInfo.response_queue.put('Invalid command!')

def print_output(globalInfo):
    while globalInfo.active:
        user_msg = globalInfo.response_queue.get()
        print(user_msg)

