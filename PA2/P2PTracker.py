import socket # network comm.
import threading # handling multiple clients
import logging 
import sys
import time # sleep, delay

# Adjust the logging configuration to match project specifications
logging.basicConfig(filename="logs.log", format="%(message)s", filemode="a", level=logging.DEBUG)

class P2PTracker:
#initialize new instance of Tracker class
    def __init__(self, host='localhost', port=5100):
        self.host = host
        self.port = port
        self.chunk_list = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # setting a server socket
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # setting to reuse the address
        self.server_socket.bind((self.host, self.port)) # binding IP and Port
        self.server_socket.listen() # listen: waiting for cilent

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    messages = message.split('\n')  # Handle possible concatenated messages
                    for msg in messages:
                        cmd, *args = msg.split(',')
                        if cmd == "LOCAL_CHUNKS":
                            self.register_chunk(*args)
                            time.sleep(1)
                        elif cmd == "WHERE_CHUNK":
                            self.send_chunk_location(client_socket, *args)
                            time.sleep(1)
            except ConnectionResetError:
                break
        client_socket.close()

    def register_chunk(self, chunk_index, ip_address, port_number):
        # Register chunk without additional logging
        self.chunk_list.setdefault(chunk_index, []).append((ip_address, int(port_number)))

    def send_chunk_location(self, conn, chunk_index):
        chunk_info = self.chunk_list.get(chunk_index, [])
        if chunk_info:
            response = "GET_CHUNK_FROM," + chunk_index + "," + ",".join([f"{ip},{port}" for ip, port in chunk_info])
            logging.info(f"P2PTracker,GET_CHUNK_FROM,{chunk_index}," + ",".join([f"{ip},{port}" for ip, port in chunk_info]))
        else:
            response = "CHUNK_LOCATION_UNKNOWN," + chunk_index
            logging.info(f"P2PTracker,CHUNK_LOCATION_UNKNOWN,{chunk_index}")
        conn.sendall(response.encode('utf-8'))

    def run(self):
        print("P2PTracker running on {},{}".format(self.host, self.port))
        while True:
            client_socket, _ = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    tracker = P2PTracker()
    tracker.run()
