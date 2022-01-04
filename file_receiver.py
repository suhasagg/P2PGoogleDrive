
# notes: for listening, set the localhost to an empty string

import select
import socket
import random
import time
import hashlib
import queue
from encryption import decrypt,encrypt
# File is received - Message decoding is happening

#Advantage of all the granular packet parameters

class Receiver:

    def __init__(self,q):
        # UDP socket for receiving file
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_queue = q
        self.open = True
        self.window_size = 1600
        self.recieve_buffer = {}
        self.last_recieved = 0
        #self.recv.setblocking()
        self.isn = int(random.random()*1000)
        self.on = True

    # indicate ready-ness to receive incoming connections
    def mrt_open(self):
        return self.open
        
    # accept an incoming connection (return a connection), 
    # guaranteed to return one (will block until there is one)
    def mrt_accept1(self):
        if(self.open == False):
            return Exception('Already connected to someone.')

        self.open = False

        # wait for syn message
        while True:
            (x,sender) = self.recv_queue.get()
            syn = x.decode('utf-8')
            self.sender = sender
            self.conn_num = get_field(syn,con_num=True)
            self.last_recieved = get_field(syn,seq=True) + 2
            if(check_checksum(syn) and verify_flag(packet=syn, syn=True)):
                break
        
        # check message and get isn and random connection number
        # packet window size
        self.socket.sendto(encrypt(self.make_pack("",self.isn,self.last_recieved,ack=True,syn=True,ad_win = self.window_size)),self.sender)

    # return true if packet is uncorrupted and in order
    # false otherwise
    def check_packet(self,data):
        if get_field(data,con_num=True) == self.conn_num and check_checksum(data):
            return True
        else:
            return False

    # wait for at least one byte of data over a given connection, 
    # guaranteed to return data except if the connection closes 
    # (will block until there is data or the connection closes)
    # always recieve 1460 bytes as a minimum
    def mrt_recieve1(self):
        (x,sender) = self.recv_queue.get()
        packet = x.decode('utf-8')
        if(self.check_packet(packet)):
            return self.process_packet(packet)
    
    def mrt(self,recieved_packet):

        # check to see if packet is legit or should be ignored
        # if is normal data message
        if(get_field(recieved_packet,flags=True) == "000"):
            # if is the right packet, send ack and update next ack to send
            # if is the wrong packet, ignore
            # Add one to sequence number to derive acknoweldgement number
            ack_num = get_field(recieved_packet, seq=True) + 1
            self.socket.sendto(encrypt(self.make_pack("",0,ack_num = ack_num%10000,ack=True,ad_win = self.window_size)),self.sender)
            
            # check to see if last_received is the seq process_packetnumber
            if self.last_recieved%10000 == ack_num-1:
                self.last_recieved += len(recieved_packet.encode())
                # somehow pass up here to the user
                return get_field(recieved_packet,data=True)

        # if is FIN message
        if(get_field(recieved_packet,flags=True) == "001"):
            # Add one to sequence number to derive acknoweldgement number
            ack_num = get_field(recieved_packet, seq=True) + 1
            self.mrt_disconnect(ack_num)

    # given a connection, returns whether there is currently data to be received.
    def mrt_probe(self):
        if(self.recv_queue.qsize()>0):
            return True
        else:
            return False

    # close the connection
    def mrt_disconnect(self, ack_num):
        finack = self.make_pack("",0,ack_num,ack=True,fin=True,ad_win = self.window_size)
        self.socket.sendto(encrypt(finack),self.sender)
        time_last = time.time()
        timeout = time.time()

        # keep looping incase they did not get the finack
        ack= None
        while not ack:

            if(time.time() - time_last >= 1):
                self.socket.sendto(encrypt(finack),self.sender)
                time_last = time.time()
            
            if(time.time() - timeout > 10):
                # timeout and quit
                ack = True

            if(self.recv_queue.qsize()>0):
                (data,sender) = self.recv_queue.get()
                data = data.decode('utf-8')
                # if data is valid and is a synack
                if data and verify_flag(data,fin = True) and verify_flag(data,ack = True) and self.check_packet(data):
                    ack = data
    
        self.on = False
        # wait and timeout
        
    # indicate incoming connections are no-longer accepted
    def mrt_close(self):
        # do nothing because nothing happens
        return

    # add header to packets:
    def make_pack(self, data, seq_num, ack_num, ack=False, syn = False, fin = False,ad_win = 0):
        
        flags = ""

        if(ack):
            flags += "1"
        else:
            flags += "0"

        if(syn):
            flags += "1"
        else:
            flags += "0"
        
        if(fin):
            flags += "1"
        else:
            flags += "0"

        packet_format = "{flags:>3}{seq:>4}{ack:>4}{random:>4}{hash:>4}{advWin:>5}"
        pseudo_header = (packet_format.format(flags=flags,seq = seq_num, ack = ack_num, random = self.conn_num,hash = 0, advWin = ad_win))
        pseudo_packet = pseudo_header + str(data)
        check_sum = int(hashlib.sha1(pseudo_packet.encode()).hexdigest(),16)%10000
        packet = (packet_format.format(flags=flags,seq = seq_num, ack = ack_num,random = self.conn_num,hash = check_sum % 10000, advWin = ad_win)) + str(data)
        return packet.encode()
    
def get_field(decoded_msg, flags = False, seq = False, ack = False, con_num = False, checksum = False, ad_win = False, data = False):
        if flags:
            return decoded_msg[0:3]
        if seq:
            return int(decoded_msg[3:7])
        if ack:
            return int(decoded_msg[7:11])
        if con_num:
            return int(decoded_msg[11:15])
        if checksum:
            return int(decoded_msg[15:19])
        if ad_win:
            return int(decoded_msg[19:24])
        if data:
            return decoded_msg[24:]

def verify_flag( packet, syn = False, synack = False, ack = False, fin = False):
        flags = get_field(packet,flags=True)
        if ack and flags[0:1] == "1":
            return True

        if syn and flags[1:2] == "1":
            return True
        
        if synack and flags[0:2] == "11":
            return True

        if fin and flags[2:3] == "1":
            return True
        
        return False

def check_checksum(decoded_packet):
        checksum = get_field(decoded_packet,checksum=True)
        pseudo_packet = decoded_packet[0:15] + "   0" + decoded_packet[19:]
        curr_checksum = int(hashlib.sha1(pseudo_packet.encode()).hexdigest(),16)%10000
        return int(checksum) == curr_checksum

