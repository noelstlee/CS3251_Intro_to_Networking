import socket
import threading
import logging
import argparse
import os
import time  # Import time module for sleep

# Setup basic configuration for logging as specified
logging.basicConfig(filename="logs.log", format="%(message)s", filemode="a", level=logging.DEBUG)

class P2PClient:
    def __init__(self, folder_path, transfer_port, client_name):
        # Initialize client settings
        self.folder_path = folder_path # stores folder path where the file chunks are kept
        self.transfer_port = transfer_port # the port on which the client will listen for incoming chunk requests
        self.client_name = client_name # a name identifier for the client
        self.tracker_address = ('localhost', 5100)  # Tracker's well-known address and port
        self.local_chunks = {}  # Local chunk data
        self.total_chunks = 0  # Total number of chunks to complete the file-set

        self.requesting_chunks = set()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.transfer_port))
        self.server_socket.listen(10)

    def read_local_chunks(self):
        # Read local_chunks.txt to find out which chunks this client has
        local_chunks_path = os.path.join(self.folder_path, 'local_chunks.txt')
        with open(local_chunks_path, 'r') as file:
            for line in file:
                chunk_index, filename = line.strip().split(',')
                if filename == "LASTCHUNK":
                    self.total_chunks = int(chunk_index)
                    continue
                self.local_chunks[chunk_index] = filename

    def connect_to_tracker_and_register(self):
        # Connect to P2PTracker and register local chunks
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_socket:
            tracker_socket.connect(self.tracker_address)
            for chunk_index in self.local_chunks.keys():
                message = f"LOCAL_CHUNKS,{chunk_index},localhost,{self.transfer_port}"
                tracker_socket.sendall(message.encode())
                time.sleep(1)  # Ensure a small gap between consecutive messages
                logging.info(f"{self.client_name},{message.strip()}")

    def request_chunk_locations(self):
        # Connect to the P2PTracker and request locations for missing chunks
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_socket:
            tracker_socket.connect(self.tracker_address)
            for chunk_index in range(1, self.total_chunks + 1):  # Use the total_chunks information
                chunk_index_str = str(chunk_index)
                if chunk_index_str not in self.local_chunks:
                    message = f"WHERE_CHUNK,{chunk_index_str}"
                    tracker_socket.sendall(message.encode())
                    time.sleep(1)  # Ensure a gap between consecutive messages
                    logging.info(f"{self.client_name},WHERE_CHUNK,{chunk_index_str}")
                    response = tracker_socket.recv(1024).decode()
                    self.handle_tracker_response(response)

    def handle_tracker_response(self, response):
        # Handle response from tracker for chunk location requests
        commands = response.split('\n')
        for command in commands:
            parts = command.split(',')
            if parts[0] == "GET_CHUNK_FROM":
                chunk_index = parts[1]
                for i in range(2, len(parts), 2):
                    peer_ip, peer_port = parts[i], int(parts[i+1])
                    self.request_chunk_from_peer(chunk_index, peer_ip, peer_port)

    def request_chunk_from_peer(self, chunk_index, peer_ip, peer_port):
        # Check if we already have this chunk or it's being requested
        if chunk_index in self.local_chunks or chunk_index in self.requesting_chunks:
            return  # Exit if the chunk is already received or being requested

        # Mark the chunk as being requested to avoid duplicate requests
        self.requesting_chunks.add(chunk_index)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                peer_socket.connect((peer_ip, peer_port))
                message = f"REQUEST_CHUNK,{chunk_index}"
                peer_socket.sendall(message.encode())
                logging.info(f"{self.client_name},REQUEST_CHUNK,{chunk_index},{peer_ip},{peer_port}")
                
                chunk_data = bytearray()
                while True:
                    part = peer_socket.recv(1024)
                    if not part:
                        break  # Exit the loop if no more data is received
                    chunk_data.extend(part)
                    
                if chunk_data:
                    filename = f"chunk_{chunk_index}"
                    with open(os.path.join(self.folder_path, filename), 'wb') as chunk_file:
                        chunk_file.write(chunk_data)
                    self.local_chunks[chunk_index] = filename
                    
                    # Notify the tracker that this client now has the new chunk
                    self.notify_tracker_new_chunk(chunk_index)
        except Exception as e:
            logging.error(f"Error getting chunk {chunk_index} from {peer_ip}:{peer_port} - {e}")
        finally:
            # Remove the chunk from the requesting set in case of success or failure
            self.requesting_chunks.discard(chunk_index)

    
    def notify_tracker_new_chunk(self, chunk_index):
        # Notify the tracker that this client now has a new chunk
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_socket:
            tracker_socket.connect(self.tracker_address)
            message = f"LOCAL_CHUNKS,{chunk_index},localhost,{self.transfer_port}"
            tracker_socket.sendall(message.encode())
            logging.info(f"{self.client_name},LOCAL_CHUNKS,{chunk_index},localhost,{self.transfer_port}")


    def serve_chunk_requests(self):
        # Listen for and serve chunk requests from other clients
        try:
            while True:
                client_socket, _ = self.server_socket.accept()
                threading.Thread(target=self.handle_client_request, args=(client_socket,)).start()
        except ConnectionResetError:
            logging.info("Connection was reset unexpectedly.")
        finally:
            self.server_socket.close()

    def handle_client_request(self, client_socket):
        chunk_index = None
        try:
            message = client_socket.recv(1024).decode()
            _, chunk_index = message.strip().split(',')
            filename = self.local_chunks.get(chunk_index)
            if filename:
                with open(os.path.join(self.folder_path, filename), 'rb') as chunk_file:
                    client_socket.sendall(chunk_file.read())
        except Exception as e:
            logging.error(f"Error serving chunk {chunk_index}: {str(e)}")
        
        client_socket.close()  # Ensures the socket is closed in all cases

    def start(self):
        self.read_local_chunks()
        self.connect_to_tracker_and_register()
        threading.Thread(target=self.serve_chunk_requests, daemon=True).start()

        while len(self.local_chunks) < self.total_chunks:
            self.request_chunk_locations()
            # Sleep briefly to allow chunk requests to be processed
            time.sleep(2)

        print("All chunks acquired. Continuing to serve requests...")
        while True:
            time.sleep(10)  # Keep the main thread alive
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='P2PClient for Peer-to-Peer File Sharing')
    parser.add_argument('-folder', type=str, required=True, help='Folder containing file chunks')
    parser.add_argument('-transfer_port', type=int, required=True, help='Port for transferring file chunks')
    parser.add_argument('-name', type=str, required=True, help='Name of the client')
    args = parser.parse_args()
   
    client = P2PClient(folder_path=args.folder, transfer_port=args.transfer_port, client_name=args.name)
    client.start()