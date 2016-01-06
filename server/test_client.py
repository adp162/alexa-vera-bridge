#!/usr/bin/python
import socket, ssl
import json
import sys

def send_vera_message(s, data):
    # Encode the message, send to Vera, and wait for response
    msg = json.dumps(data)
    print ('sending msg: ' + msg)
    s.sendall(msg)

    # Wait for a response
    resp = s.read()
    print ('resp: ' + resp)
        
    # Decode the received message
    return json.loads(resp)

def main():
    # Define the port/hostname for the server that we will connect to
    PORT = 3000
    HOST = '0.0.0.0' # FIXME
    
    # Define paths to our security assets
    CA_PATH = './base_rootCA.pem'
    CLIENT_CERT_PATH = './lambda.crt'
    CLIENT_KEY_PATH = './lambda.key'
    
    print 'Configuring security parameters.'
    
    # Create the SSL context to authenticate server
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_verify_locations(CA_PATH)
    context.load_cert_chain(certfile=CLIENT_CERT_PATH, keyfile=CLIENT_KEY_PATH)
    context.verify_mode = ssl.CERT_REQUIRED
    
    # Create the socket and wrap it in our context to secure
    # By specifying server_hostname we require the server's certificate to match the
    # hostname we provide
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_s = context.wrap_socket(s, server_hostname='hostname.dynamic-dns.net') # FIXME
    print 'connect to ' + HOST + ':' + str(PORT)
    secure_s.connect((HOST, PORT))
    
    # Send a test message
    device = '18'
    action = 'on'
    if action == 'on':
        value = 1
    elif action == 'off':
        value = 0
    else:
        value = 0
    data = { 'id':int(device), 
                'action': {'type': 'set', 'attribute': {'power':value} },
                'close_connection':True }
    resp = send_vera_message(secure_s, data)
    if resp['status'] == 0:
        print 'OK.'
    else:
        print 'Error. ' + resp['err_str']

    # Close the socket and exit
    secure_s.close()
    print 'closed connection'
    sys.exit()
        
if __name__ == '__main__':
    main()
