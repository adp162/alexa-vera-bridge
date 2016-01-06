#!/usr/bin/python

import base64
import time
import socket
import ssl
import threading
import pprint
import sys
import pkgutil

# Global variables
#BASE_PATH='./user/'
BASE_PATH='./sample/'

CA_PATH = BASE_PATH + 'rootCA.pem'
PORT = 3000
HOST = 'localhost'

# This is the main function for the client thread
def client_thread(lock):
    # Wait for the server to start listening then send a message
    time.sleep(1)

    # Location of client cert/key
    CLIENT_CERT_PATH = BASE_PATH + 'client.crt'
    CLIENT_KEY_PATH = BASE_PATH + 'client.key'
    
    print ('client: configuring security parameters.')
    
    # Create the SSL context to authenticate server
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_verify_locations(CA_PATH)
    context.load_cert_chain(certfile=CLIENT_CERT_PATH, keyfile=CLIENT_KEY_PATH)
    context.verify_mode = ssl.CERT_REQUIRED
    
    # Create the socket and wrap it in our context to secure
    # By specifying server_hostname we require the server's certificate to match the
    # hostname we provide
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_s = context.wrap_socket(s, server_hostname=HOST)
    print ('client: connect to ' + HOST + ':' + str(PORT))
    
    try:
        secure_s.connect((HOST, PORT))
    except socket.error as msg:
        print ('client: socket error: ' + msg[1])
        return

    # Print out some info about our connection
    lock.acquire()
    print ('SERVER CERTIFICATE (as seen by client):')
    cert = secure_s.getpeercert()
    pprint.pprint(cert)
    print
    print ('CONNECTION DETAILS:')
    cipher = secure_s.cipher()
    print ('cipher: ' + cipher[0] + ', protocol: ' + cipher[1] + ', bits: ' + str(cipher[2]))
    if (secure_s.compression() is not None):
        print ('compression: ' + secure_s.compression())
    else:
        print ('compression: None')
    print ('protocol version: ' +secure_s.version())
    print
    lock.release()

    # Send the data
    secure_s.sendall(b'This is a test message.')
    lock.acquire()
    print ('client: sent message to server')
    lock.release()

    # Wait for a response
    data = secure_s.read()
    lock.acquire()
    print ('client: msg from server "' + data + '"')
    lock.release()

    # Close the socket
    secure_s.close()

def main():
    # Check for the right Python version
    if sys.version_info < (2, 7, 9):
        print ('Python version must be 2.7.9 or greater.')
        sys.exit()
    
    # Check for presence of PyCrypto
    if pkgutil.find_loader('Crypto') is None:
        print ('PyCrypto not found - try "pip install pycrypto"')
        sys.exit()

    # Import the modules we need from PyCrypto
    from Crypto.Cipher import AES
    from Crypto import Random
    
    # Read the pre-shared key
    # FIXME: not sure why the newline gets read, but we need to strip it
    f = open('./sample/psk.bin', 'r')
    key_base64 = f.read().rstrip('\n')
    key = base64.b64decode(key_base64)
    f.close()

    #
    # Encrypt/Decrypt and examine results
    #
    msg = 'Secret message! I hope no one can read this!'
    
    # Generate a random initialization vector
    r = Random.new()
    iv = r.read(AES.block_size)

    # Setup the cipher and encrypt the message. The cipher is
    # stateful so we cannot use the same one to encrypt then decrypt!
    enc_cipher = AES.new(key, AES.MODE_CBC, iv)
    pad = '*' * (AES.block_size - (len(msg) % AES.block_size))
    enc = enc_cipher.encrypt(msg + pad)

    # Setup a new cipher with the same parameters used to encrypt
    dec_cipher = AES.new(key, AES.MODE_CBC, iv)
    dec = dec_cipher.decrypt(enc)

    # Display the results
    print ('AES Cipher Example (256 bit key)')
    print ('--------------------------------')
    print ('Secret key:   ' + key_base64)
    print ('IV:           ' + base64.b64encode(iv))
    print ('Orig Message: ' + msg)
    print ('Encrypted:    ' + base64.b64encode(enc))
    print ('Decrypted:    ' + dec.rstrip('*'))
    print
    
    #
    # Setup a mutually authenticated client/server running on localhost
    #

    # Check OpenSSL version
    print (ssl.OPENSSL_VERSION)

    # Kick off a client thread to send a message to the server
    lock = threading.Lock()
    t = threading.Thread(target=client_thread, args=(lock,))
    t.start()

    # Location of server cert/key
    SERVER_CERT_PATH = BASE_PATH + 'server.crt'
    SERVER_KEY_PATH = BASE_PATH + 'server.key'
    
    print ('server: configuring security parameters.')
    
    # Create the SSL context to authenticate client
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_verify_locations(CA_PATH)
    context.load_cert_chain(certfile=SERVER_CERT_PATH, keyfile=SERVER_KEY_PATH)
    context.verify_mode = ssl.CERT_REQUIRED
    
    # Create the socket (For SSL we must use SOCK_STREAM)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the socket to the port
    print ('server: starting on ' + socket.gethostname() + ':' + str(PORT))
    print
    # Do some error checking as binds can fail if the port is being used by
    # someone else
    try:
        s.bind(('', PORT))
    except socket.error as msg:
        print ('server: socket bind() failed!')
        print ('server: (err ' + str(msg[0]) + '): ' + msg[1])
        sys.exit()
        
    # start listening (with max 3 connections queued)
    s.listen(3)

    # accept the connection when it is received
    (new_s, addr) = s.accept()
    print ('server: connection from ' + addr[0] + ':' + str(addr[1]))
        
    # Wrap the socket in our SSL context to protect communications 
    secure_s = context.wrap_socket(new_s, server_side=True)

    # Print out the peer (client) certificate
    lock.acquire()
    print ('CLIENT CERTIFICATE (as seen by server):')
    cert = secure_s.getpeercert()
    pprint.pprint(cert)
    print
    lock.release()

    # Get client data and send the response
    data = secure_s.read()
    lock.acquire()
    print ('server: msg from client "' + data + '"')
    lock.release()
    secure_s.sendall(b'OK')
    lock.acquire()
    print ('server: sent response')
    lock.release()

    # Wait for the client thread to finish
    t.join()
    secure_s.close()

    # Exit
    sys.exit()

if __name__ == '__main__':
    main()
