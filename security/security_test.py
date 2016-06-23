#!/usr/bin/python

import base64
import time
import socket
import ssl
import threading
import pprint
import sys
import pkgutil
import os

# Global variables
BASE_PATH='./sample'

CA_PATH = BASE_PATH + '/rootCA.pem'
PORT = 3000
HOST = 'localhost'

# Function that configures and starts the server
def start_server(security, lock):

    # Location of server cert/key
    SERVER_CERT_PATH = BASE_PATH + '/server.crt'
    SERVER_KEY_PATH = BASE_PATH + '/server.key'

    print ('server: configuring security profile as "' + security + '"')
    
    # Open up the port and listen for connections
    # Create the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the socket to the port
    print 'server: started on ' + socket.gethostname() + ':' + str(PORT)
    print
    # Do some error checking as binds can fail if the port is being used by
    # someone else
    try:
        s.bind(('', PORT))
    except socket.error as msg:
        print 'server: socket bind() failed!'
        print 'server: (err ' + str(msg[0]) + '): ' + msg[1]
        sys.exit()

    # start listening (with max 3 connections queued)
    s.listen(3)

    # Setup the SSL context based on assets provided in the config file
    if security == 'none':
        # No need to create an SSL context
        pass
    elif security == 'ssl':
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.set_ciphers('HIGH')
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif security == 'ssl_mutual_auth':
        # Make sure the cert files are present
        if os.path.isfile(SERVER_CERT_PATH) and os.path.isfile(SERVER_KEY_PATH):
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_verify_locations(CA_PATH)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_cert_chain(certfile=SERVER_CERT_PATH, keyfile=SERVER_KEY_PATH)
        else:
            print "Missing server security assets!"
            return s

    # Wait here for a client to connect
    # accept() will block until a client has tried to connect
    (new_s, addr) = s.accept()
    print 'server: connection from ' + addr[0] + ':' + str(addr[1])
        
    # Wrap the socket in our SSL context to protect communications
    if security == 'none':
        secure_s = new_s
    else:
        secure_s = context.wrap_socket(new_s, server_side=True)

    # Print out the peer (client) certificate
    if security == 'ssl_mutual_auth':
        lock.acquire()
        print ('CLIENT CERTIFICATE (as seen by server):')
        cert = secure_s.getpeercert()
        pprint.pprint(cert)
        print
        lock.release()

    # Get client data and send the response
    data = secure_s.recv(1024)
    lock.acquire()
    print ('server: msg from client "' + data + '"')
    lock.release()
    secure_s.sendall(b'OK')
    lock.acquire()
    print ('server: sent response')
    lock.release()

    # Return the socket handle so we can cleanup before starting the next server
    return secure_s

# This is the main function for the client thread
def client_thread(security, lock):
    # Wait for the server to start listening then send a message
    time.sleep(1)

    # Location of client cert/key
    CLIENT_CERT_PATH = BASE_PATH + '/client.crt'
    CLIENT_KEY_PATH = BASE_PATH + '/client.key'

    print ('client: configuring security profile as "' + security + '"')
    
    # Try a regular connection (INSECURE)
    sock = None
    if security == 'none':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print ('client: connect to ' + HOST + ':' + str(PORT) + ' (INSECURE)')
    elif security == 'ssl':
        # For this example we show TLSv1. You could also try SSLv2 or SSLv3 but
        # both of these protocols are known to be insecure and more recent versions
        # of OpenSSL compiled with NO_SSLv2 and NO_SSLv3 flags won't allow this option.
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        # The string passed here sets the OpenSSL cipher we're willing to use.
        # See: https://www.openssl.org/docs/manmaster/apps/ciphers.html#CIPHER-LIST-FORMAT
        # HIGH is basically >128 bit ciphers.
        context.set_ciphers('HIGH')
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif security == 'ssl_mutual_auth':
        # Make sure the certificates exist
        if os.path.isfile(CLIENT_CERT_PATH) and os.path.isfile(CLIENT_KEY_PATH):
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(CA_PATH)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_cert_chain(certfile=CLIENT_CERT_PATH, keyfile=CLIENT_KEY_PATH)
        else:
            print "Missing client security assets!"
            return

    if security != 'none':
        # Create the socket and wrap it in our context to secure
        # By specifying server_hostname we require the server's certificate to match the
        # hostname we provide
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = context.wrap_socket(s, server_hostname=HOST)
        print ('client: connect to ' + HOST + ':' + str(PORT) + ' (SSL/TLS)')

    # Try to make the connection
    try:
        sock.connect((HOST, PORT))
    except socket.error as msg:
        print ('client: socket error (' + str(msg[0]) + '): ' + msg[1])
        return

    # Print out some info about our connection
    if security != 'none':
        lock.acquire()
        if security == 'ssl_mutual_auth':
            print ('SERVER CERTIFICATE (as seen by client):')
            cert = sock.getpeercert()
            pprint.pprint(cert)
            print
        print ('CONNECTION DETAILS:')
        cipher = sock.cipher()
        print ('cipher: ' + cipher[0] + ', protocol: ' + cipher[1] + ', bits: ' + str(cipher[2]))
        if (sock.compression() is not None):
            print ('compression: ' + sock.compression())
        else:
            print ('compression: None')
        print ('protocol version: ' + sock.version())
        print
        lock.release()

    # Send the data
    sock.sendall(b'This is a test message.')
    lock.acquire()
    print ('client: sent message to server')
    lock.release()

    # Wait for a response
    data = sock.recv(1024)
    lock.acquire()
    print ('client: msg from server "' + data + '"')
    lock.release()

    # Close the socket
    sock.close()

# Function that performs encryption/decryption with a symmetric key
def sym_enc_test(key_base64):
    # Import the modules we need from PyCrypto
    from Crypto.Cipher import AES
    from Crypto import Random

    # Convert the base64 encoded key back to binary
    key = base64.b64decode(key_base64)

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
    print
    print ('--------------------------------')
    print ('AES Cipher Example (256 bit key)')
    print ('--------------------------------')
    print ('Secret key:   ' + key_base64)
    print ('IV:           ' + base64.b64encode(iv))
    print ('Orig Message: ' + msg)
    print ('Encrypted:    ' + base64.b64encode(enc))
    print ('Decrypted:    ' + dec.rstrip('*'))
    print

def main():
    # Check for the right Python version
    if sys.version_info < (2, 7, 9):
        print ('Python version must be 2.7.9 or greater.')
        sys.exit()

    run_sym_enc_test = True
    # Check for presence of PyCrypto
    if pkgutil.find_loader('Crypto') is None:
        print ('PyCrypto not in standard search path.')
        print ('PATH = ' + str(sys.path))
        print ('Appending alternate paths...')
        alt_paths = '/usr/local/lib/python2.7/dist-packages'
        sys.path.append(alt_paths)
        if pkgutil.find_loader('Crypto') is None:
            print ('PyCrypto not found - try "pip install pycrypto"')
            run_sym_enc_test = False

    # Read the pre-shared key
    print
    print ('--------------------------------')
    print ('       Symmetric Key Test')
    print ('--------------------------------')
    try:
        f = open(BASE_PATH + '/psk.bin', 'r')
        # Note that the newline gets read, so we need to strip it
        key_base64 = f.read().rstrip('\n')
        f.close()
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
        run_sym_enc_test = False
    except:
        print "Unexpected error:", sys.exc_info()[0]
        run_sym_enc_test = False

    # If we have PyCrypto installed and the PSK file then we can run the test
    if run_sym_enc_test:
        sym_enc_test(key_base64)
    else:
        print "Skipping symmetric encryption test with PSK."

    #
    # Setup client/server running on localhost with various security parameters
    #

    # Check OpenSSL version
    print ('OpenSSL version is: ' + ssl.OPENSSL_VERSION)

    # Create a lock for synchronization between threads
    lock = threading.Lock()

    # 1) none - just do regulat connection (INSECURE)
    # Kick off a client thread to send a message to the server
    # This is done first because start_server() block waiting for a client
    # to connect.
    print
    print ('--------------------------------')
    print ('    TEST 1 - Standard socket')
    print ('--------------------------------')
    security = 'none'
    t = threading.Thread(target=client_thread, args=(security, lock,))
    t.start()
    s = start_server(security, lock)
    t.join()
    s.close()

    # 2) just the section - use ssl/tls but with no auth
    print
    print ('--------------------------------')
    print ('    TEST 2 - SSL/TLS No auth')
    print ('--------------------------------')
    security = 'ssl'
    t = threading.Thread(target=client_thread, args=(security, lock,))
    t.start()
    s = start_server(security, lock)
    t.join()
    s.close()

    # 3) root_ca plus client cert/key- give out certificate to server
    print
    print ('--------------------------------')
    print ('  TEST 3 - SSL/TLS Mutual auth')
    print ('--------------------------------')
    security = 'ssl_mutual_auth'
    t = threading.Thread(target=client_thread, args=(security, lock,))
    t.start()
    s = start_server(security, lock)
    t.join()
    s.close()

    # Exit
    sys.exit()

if __name__ == '__main__':
    main()
