import datetime
import socket
import argparse
import re
import sys
import threading

def is_valid_passcode(passcode):
    pattern = r'^[a-zA-Z0-9]{1,5}$'
    return bool(re.match(pattern, passcode))

parser = argparse.ArgumentParser(prog="chat application", description="python3 server.py -start -port <port> -passcode <passcode>")

parser.add_argument('-start', action='store_true', help='Start the server')
parser.add_argument('-port', type=str, help='Server port', required=True)
parser.add_argument('-passcode', type=str, help='Chatroom passcode (up to 5 alphanumeric characters)', required=True)
args = parser.parse_args()

if not is_valid_passcode(args.passcode):
    print('Incorrect passcode')
    sys.stdout.flush()

clients = {}
def handle_client(conn,addr):
    
    while True:
        data = conn.recv(1024)
        decoded_data = data.decode('utf-8')
        if addr not in clients:
            print(decoded_data, "joined the chatroom")
            sys.stdout.flush()
            clients[addr] = (conn, decoded_data)
            for address, userdata in clients.items():
                con = userdata[0]
                username = userdata[1]
                if username == decoded_data:
                    announcement = "Connected to "+ hostIP+" on port "+str(port)
                    con.send(announcement.encode('utf-8'))
                else:
                    announcement = decoded_data+" joined the chatroom"
                    con.send(announcement.encode('utf-8'))
        elif decoded_data.startswith(':dm'):
            try:
                _, receiver_username, message = decoded_data.split(' ', 2)
            except ValueError:
                continue
            sender_username = clients[addr][1]
            for _, (con, username) in clients.items():
                if username == receiver_username:
                    direct_message = f"#{sender_username}: {message}"
                    con.send(direct_message.encode('utf-8'))
                    break  
            print(f"#{sender_username} to {receiver_username}: {message}")
            sys.stdout.flush()
        elif decoded_data == ':Exit':
            traitor = ''
            for address, userdata in clients.items():
                con = userdata[0]
                if addr==address:
                    traitor = clients[address][1]
                    print(traitor, "left the chatroom")
                    sys.stdout.flush()
                    con.close()
                    del clients[address]
                    break
            for address, userdata in clients.items():
                con = userdata[0]
                announcement = traitor+" left the chatroom"
                con.send(announcement.encode('utf-8'))
            conn.close()
            break
        else:
            speaker = ''
            for address, userdata in clients.items():
                con = userdata[0]

                if addr==address:
                    speaker = clients[address][1]
                    if decoded_data==":)":
                        print(f"{speaker}: [feeling happy]")    
                    elif decoded_data==":(":
                        print(f"{speaker}: [feeling sad]")    
                    elif decoded_data ==":mytime":
                        now = datetime.datetime.now()
                        formatted_time = now.strftime("%a %b %d %H:%M:%S %Y")
                        announcement = speaker+": "+ formatted_time
                        print(f"{speaker}: {formatted_time}")    
                    elif decoded_data==":+1hr":
                        onehradded = datetime.datetime.now() + datetime.timedelta(hours=1)
                        formatted_time = onehradded.strftime("%a %b %d %H:%M:%S %Y")
                        announcement = speaker+": "+ formatted_time
                        print(f"{speaker}: {formatted_time}")    
                    else:
                        print(f"{speaker}: {decoded_data}")    
                    sys.stdout.flush()
                    break
            for address, userdata in clients.items():
                
                con = userdata[0]
                if addr==address:
                    continue
                announcement=''
                if decoded_data==":)":
                    announcement = speaker+": " + "[feeling happy]"
                    announcement = f"{speaker}: [feeling happy]"
                elif decoded_data==":(":
                    announcement = f"{speaker}: [feeling sad]"
                elif decoded_data ==":mytime":
                    now = datetime.datetime.now()
                    formatted_time = now.strftime("%a %b %d %H:%M:%S %Y")
                    announcement = f"{speaker}: {formatted_time}"
                elif decoded_data==":+1hr":
                    onehradded = datetime.datetime.now() + datetime.timedelta(hours=1)
                    formatted_time = onehradded.strftime("%a %b %d %H:%M:%S %Y")
                    announcement = f"{speaker}: {formatted_time}"
                else:
                    announcement = f"{speaker}: {decoded_data}"
                con.send(announcement.encode('utf-8'))

if args.start:
    sys.stdout.flush()
    if is_valid_passcode(args.passcode):
        hostIP = '127.0.0.1'
        port = int(args.port)
        print(f"Server started on port {port}. Accepting connections")
        sys.stdout.flush()
        passcode = args.passcode
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((hostIP, port))
        s.listen(10)
        
        while True:
            conn, addr = s.accept()
            client_handler = threading.Thread(target=handle_client, args=(conn,addr))
            client_handler.start()
else:
    print("Your input is not valid. Remember Port is 4 digit integers and Passcode is maximum 5 length of alpha and numeric values.\nYour port:", args.port," and your passcode:", args.passcode)