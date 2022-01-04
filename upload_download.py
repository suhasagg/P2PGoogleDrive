from os import read
import threading
from file_sender import Sender
from file_receiver import Receiver
import queue
import socket
import select
from encryption import decrypt

BYTE_TRANSMIT_SIZE = 100
SAVE_PATH = "test-output.txt"
INPUT_FILE_PATH = "test-input.txt"
IP_TEST = "localhost"

def up_down_thread(ip,port, download_queues):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip,int(port)))
    receiving_thread = threading.Thread(target=add_to_queue,args=(sock,download_queues,))
    receiving_thread.setDaemon(True)
    receiving_thread.start()
    
def add_to_queue(sock, download_queues):
    while(True):
        (x,_,_,sender) = sock.recvmsg(2**16)
        x = decrypt(x).decode('utf-8').split('^')
        num = int(x[0])
        msg = x[1]
        ##Pulling from nodeid/connection number
        q = download_queues.get(num)
        q.put((msg.encode(),sender))

## needs to be updated with mrt_layer
def upload_thread(filename, IP, PORT, num): 

    sender = Sender(IP,PORT,num)
    sender.mrt_connect()

    thread1 = threading.Thread(target=upload_helper,args=(sender,))
    thread1.start()

    file = open(filename, "rb")
    readChars = file.read(BYTE_TRANSMIT_SIZE).decode('utf-8')

    while readChars != '': 
        try: 
            sender.mrt_send(readChars)
        except Exception: 
            return (Exception)

        readChars = file.read(BYTE_TRANSMIT_SIZE).decode('utf-8')
        # append to the beginning

    file.close()
    closing_thread = threading.Thread(target=sender.mrt_disconnect,args=())
    closing_thread.start()
    
def upload_helper(send):
    while send.disconnecting == False:
        reading, writing, _ = select.select([send.s],[send.s],[])
        
        for sock in reading:
        # if reading from stdin 
            data = send.mrt_recieve1()
            send.process_data(data)

        for sock in writing:
            send.update()

def download_thread(filename,num,download_queues,directory): 
    num = int(num)
    q = download_queues.get(num)
    sock = Receiver(q)
    sock.mrt_accept1()

    file = open("" + directory + '/' + filename, "w")

    ack = sock.mrt_recieve1()
    # File packets arrive continuously
    # When size reach chunk threshold, chunk is created with entry in file and chunk map
    # File chunk/piece optimisation can be placed here
    # File chunk-map can be placed in global data structure
    # Each file chunk can be written to separate file - chunk name and specific size
    # Each chunk is replicated (in multiple peers based on geography and other parameters to ensure uniform availability) by issuing send command to each peer
    # Faster data transfer using multiple peer set for chunk set for a file
    # Send file command can be used to replicate file chunks in selective peers
    while sock.on:
    # Receiving chunks in a while loop
        bytesRecv = sock.mrt_recieve1()
    # Chunks getting assembled into a single file
        if bytesRecv:
            file.write(bytesRecv)
        else:
            break

    file.close()









        







