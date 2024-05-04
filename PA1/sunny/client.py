import argparse
import re
import socket
import sys
import threading

def receive_data(s):
    
    while True:
        received_data = s.recv(1024) 
        if not received_data:
            break
        decodeData = received_data.decode('utf-8')
        print(decodeData)
        sys.stdout.flush()

def valid_passcode_check(passcode):
    return re.match(r'^[a-zA-Z0-9]{1,5}$', passcode)

parser = argparse.ArgumentParser(prog="chat application", description="python3 server.py -start -port <port> -passcode <passcode>")

parser.add_argument('-join', action='store_true', help='Start the client')
parser.add_argument('-host', type=str, help='Server host id 127.0.0.1', required=True)
parser.add_argument('-port', type=str, help='Client port (4-digit number)', required=True)
parser.add_argument('-username', type=str, help='Client username', required=True)
parser.add_argument('-passcode', type=str, help='Chatroom passcode (up to 5 alphanumeric characters)', required=True)

args = parser.parse_args()

if not valid_passcode_check(args.passcode):
    print('Incorrect passcode')
    sys.stdout.flush()

if args.join:
    if valid_passcode_check(args.passcode):
        host = args.host
        port = int(args.port)
        username = args.username
        passcode = args.passcode
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host,port))
        s.send(username.encode('utf-8'))
        receive_thread = threading.Thread(target=receive_data, args=(s,))
        receive_thread.start()
        while True:
            user_input = input()
            s.send(user_input.encode('utf-8'))
            if user_input == ':Exit':
                receive_thread.join() 
                break 
                

            