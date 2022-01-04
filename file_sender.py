# mrt_connect
# mrt_send
# mrt_disconnect

import socket
import time
import random
import select
import hashlib
import sys
import threading
from encryption import encrypt,decrypt

class Sender:

    def __init__(self,ip,port,num):
        self.stream = b''
        self.unacked = []
        # size of sending buffer
        self.ip_port = (ip,int(port))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.base = (int)(random.random() * 300) # base 
        self.updated_base = self.base
        self.timeout = 3
        self.time_last_ack = 0
        self.next_seq_num = self.base
        self.sent_bytes = 0
        self.buffer_time = 0
        self.num = num
        self.disconnecting = False

    # add header to packets:
    def make_pack(self, data, seq_num, ack_num, ack=False, syn = False, fin = False,ad_win = 0):
        # flags (ACK, SYN, FIN) --> between 
        # random number for connection --> between 0-255
        # checksum (use hash())
        # advertised window
        # data
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
        pseudo_header = (packet_format.format(flags=flags,seq = seq_num%10000, ack = ack_num%10000, random = self.conn_num,hash = 0, advWin = ad_win))
        # pseudo packet generated for checksum
        pseudo_packet = pseudo_header + str(data)
        check_sum = int(hashlib.sha1(pseudo_packet.encode()).hexdigest(),16)%10000
        packet = (packet_format.format(flags=flags,seq = seq_num%10000, ack = ack_num%10000,random = self.conn_num,hash = check_sum, advWin = ad_win)) + str(data)
        packet = str(self.num) + '^' + packet
        return packet.encode()

    # returns a specific field in a packet with a header
    def get_field(self, msg, flags = False, seq = False, ack = False, con_num = False, checksum = False, ad_win = False, data = False):
        if('^' in msg):
            decoded_msg = msg[msg.index('^')+1:]
        else:
            decoded_msg = msg
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
        if ad_win: # purpose of advertising window
            return int(decoded_msg[19:24])
        if data:
            return decoded_msg[24:]

    # connect to a given server (return a connection)
    def mrt_connect(self):
        # generate random number for connection
        self.conn_num = int(random.random()*1000)
        syn = self.make_pack(data="",seq_num=self.next_seq_num,ack_num=0, syn=True)
        self.s.sendto(encrypt(syn),self.ip_port)
        self.time_last_ack = time.time()
        self.next_seq_num = self.next_seq_num + 1

        synack = None
        while not synack:

            reading,writing,closing = select.select([self.s], [self.s], [self.s])

            if(time.time() - self.time_last_ack >= self.timeout):
                self.s.sendto(encrypt(syn),self.ip_port)
                self.time_last_ack = time.time()

            for sock in reading:
                data = sock.recv(2**16)
                data = decrypt(data).decode('utf-8')
                # if data is valid and is a synack
                if data and self.verify_flag(data,synack = True) and self.check_packet(data):
                    synack = data
            
        # get server's ISN
        self.server_isn = self.get_field(synack,seq=True)
        self.recv_window = self.get_field(synack,ad_win=True)
        ack = self.make_pack(data="",seq_num=self.next_seq_num,ack_num=self.server_isn + 1, ack=True)
        self.next_seq_num += 1
        self.s.sendto(encrypt(ack),self.ip_port)
        self.connected = True
    
    # verifies whether a packet has a specific flag
    def verify_flag(self, packet, syn = False, synack = False, ack = False, fin = False):
        flags = self.get_field(packet,flags=True)
        if ack and flags[0:1] == "1":
            return True

        if syn and flags[1:2] == "1":
            return True
        
        if synack and flags[0:2] == "11":
            return True

        if fin and flags[2:3] == "1":
            return True
        
        return False
    
    # return true if packet is uncorrupted, in order, and from the correct
    # random number
    # false otherwise
    def check_packet(self,data):
        # check checksum
        if self.get_field(data,con_num=True) == self.conn_num and self.check_checksum(data):
            return True
        else:
            return False

    # returns true if a packet is 
    def check_checksum(self,decoded_packet):
        checksum = self.get_field(decoded_packet,checksum=True)
        pseudo_packet = decoded_packet[0:15] + "   0" + decoded_packet[19:]
        curr_checksum = int(hashlib.sha1(pseudo_packet.encode()).hexdigest(),16)%10000
        return int(checksum) == curr_checksum

    # send a chunk of data over a given connection 
    # (may temporarily block execution if the receiver is busy/full)
    # headers should have fixed size
    # send <1460 at once
    def mrt_send(self,msg):
        # check to see if can send, and wait if cannot
        # add new stuff to send to list

        packet_size = min(self.recv_window-25,1400)

        temp = 0
        new_packs = []
        while(len(msg[temp:])>0):
            if(len(msg[temp:])-packet_size>0):
                temp += packet_size
                new_packet = self.make_pack(msg[temp:temp+packet_size],seq_num = self.next_seq_num%10000,ack_num=0)
            else:
                new_packet = self.make_pack(msg[temp:],seq_num=self.next_seq_num%10000,ack_num=0)
                temp += len(msg[temp:])
            self.unacked.append(new_packet)
            new_packs.append(new_packet)
            self.next_seq_num += len(new_packet)
        
        for packs in new_packs:
            available_window = self.recv_window - self.sent_bytes
            if(self.get_field(packs.decode('utf-8'),seq=True) > self.updated_base and self.get_field(packs.decode('utf-8'),seq=True) + len(packs) < available_window):
                self.sent_bytes += len(packs)
                self.s.sendto(encrypt(packs),self.ip_port)
        
        new_packs = []

    # checks to see if timeout, and resends all unacked packets if true
    def update(self):
        # if available window is < packet length
        if(time.time() - self.time_last_ack > self.timeout):
            self.resend_all()
        # if timeout, resend the unacked

    # resends all unacked packets
    def resend_all(self):
        self.sent_bytes = 0
        for i in range(len(self.unacked)):#pack in self.unacked:
            pack = self.unacked[i]
            available_window = self.recv_window - self.sent_bytes
            if(self.get_field(pack.decode('utf-8'),seq=True) > self.updated_base and len(pack) < available_window):
                self.sent_bytes += len(pack)
                self.s.sendto(encrypt(pack),self.ip_port)
        self.time_last_ack = time.time()

    # processes data (mostly acks) recieved from server
    def process_data(self,packet):
        packet = packet.decode('utf-8')
        if(self.check_packet(packet)):
            
            # if is FIN message (sender had to initiate, send ack, wait, and close socket)


            # if is ack message
            if(self.get_field(packet,flags=True) == "100"):
                ack_num = self.get_field(packet,ack=True)
                # cumulative acks, so if got it, can remove all packets w sequence numbers
                # below
                max_base = 0
                for pack in self.unacked:
                    if self.get_field(pack.decode('utf-8'),seq=True) == ack_num-1 and max_base < ack_num:
                        max_base= ack_num 
                if max_base > self.updated_base:
                    self.updated_base = max_base
                    self.time_last_ack = time.time()

            # clear ack-d things from buffer every 5 seconds
            if time.time() - self.buffer_time > 5:
                temp = []
                for pack in self.unacked:
                    if self.get_field(pack.decode('utf-8'),seq=True) > self.updated_base:
                        temp.append(pack)
                self.unacked = temp
                self.buffer_time = time.time() + 5

                    #self.base += len(packet.encode())
                # remove the dictionary entry for that byte
                # set to next one

    # disconnects the sender and reciever using a four way handshake
    def mrt_disconnect(self):
        # wait for all things to be sent before disconnecting
        time.sleep(.5)
        while(len(self.unacked) > 0):
            self.update()
            
        self.disconnecting = True

        # generate random number for connection
        fin = self.make_pack(data="",seq_num=self.next_seq_num,ack_num=0, fin=True)
        self.s.sendto(encrypt(fin),self.ip_port)
        self.time_last_ack = time.time()
        self.next_seq_num = self.next_seq_num + len(fin)

        finack= None
        while not finack:

            reading,writing,closing = select.select([self.s], [self.s], [self.s])

            if(time.time() - self.time_last_ack >= self.timeout):
                self.s.sendto(encrypt(fin),self.ip_port)
                self.time_last_ack = time.time()

            for sock in reading:
                data = sock.recv(2**16)
                data = decrypt(data).decode('utf-8')
                # if data is valid and is a synack
                if data and self.verify_flag(data,fin = True) and self.verify_flag(data,ack = True) and self.check_packet(data):
                    finack = data
                    self.connected = False
            
        # get server's ISN
        ack = self.make_pack(data="",seq_num=self.next_seq_num,ack_num=self.server_isn + 1, ack=True)
        self.next_seq_num += 1
        self.s.sendto(encrypt(ack),self.ip_port)
        self.connected = False
        self.s.close()

    # wait for at least one byte of data over a given connection, 
    # guaranteed to return data except if the connection closes 
    def mrt_recieve1(self):
        (x,_,_,sender) = self.s.recvmsg(2**16)
        return decrypt(x)
    

    # loop through, sending messages from stdin
    # and keeping track of unacked
