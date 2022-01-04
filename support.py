import queue
import time
from sender import Sender
from receiver import Receiver
from encryption import decrypt,encrypt

class Message:
    def __init__(self, node, msg):
        self.node = node
        self.msg = msg

    def get_info(self):
        return self.node, self.msg

class SendToAll:
    def __init__(self,message_type):
        self.message = message_type
    
    def msg(self):
        # fix this to be the right length but for now
        return f"{self.message}"

class Neighbor:
    def __init__(self, ip, port):
        self.main_listener = (ip,port)
        self.last_active = time.time()
        self.sender = None
        self.receiver = None
        self.files = {}
        self.receiver_listener = None
        self.last_heartbeat = ""

    def get_info(self) -> tuple:
        return self.main_listener
    
    def set_sender(self,socket):
        self.sender = socket

    def set_receiver(self,socket):
        self.receiver = socket

    def add_to_files(self,filename,checksum):
        self.files[filename] = checksum
    
    def has_file(self,filename) -> bool:
        if filename in self.files:
            return True
        else:
            return False
    
    def set_file_receiver(self,ip,port):
        self.receiver_listener = (ip,port)

    def get_sender(self) -> Sender:
        return self.sender

    def get_receiver(self) -> Receiver:
        return self.receiver

    def get_file_list(self) -> list:
        return self.files

    def all_neighbor_info(self) -> str:
        file_string = ""
        for node in self.files:
            file_string += "," + node + ":" + self.files[node]
        return f'{self.main_listener[0]}^{self.main_listener[1]}^'

    def set_download_port(self, download_port): 
        self.download_port = download_port

    def get_download_port(self): 
        return self.download_port


class GlobalInfo: 
    def __init__(self, ip, port, download_port, user_files,directory): 
        self.ip = ip
        self.port = port
        self.download_port = download_port
        self.user_files = user_files
        self.message_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.user_queue = queue.Queue()
        self.download_queues = {}
        self.all_nodes = set()
        self.my_connections = set()
        self.active = True
        self.directory = directory
        self.keys = dict() # key is IP, port tuple , value is their public key 
        #File - chunk map can be stored in Global Node Data Structure
