#!/usr/bin/python
import sys
import os
from shutil import copyfile

def main():
    # To run the client code we have to change to that directory since a bunch of
    # files in there are pathed relative to that directory. We also have to add that
    # path to the module import path.
    os.chdir('../lambda')
    sys.path.append('./')

    # Temporarily copy sample security assets to lambda directory
    copyfile('../security/sample/rootCA.pem', './rootCA.pem')
    copyfile('../security/sample/client.crt', './client.crt')
    copyfile('../security/sample/client.key', './client.key')
    copyfile('../security/sample/psk.bin', './psk.bin')
    
    # Actually use the client code to test sending server message
    import client

    # Try connecting to the Vera server
    (socket, msg) = client.open_connection_to_vera()
    if socket == None:
        print 'Error connecting to Vera: ' + msg
        sys.exit()

    # TEST: Run scene 1
    data = { 'id':1, 'action': {'type': 'run' }, 'close_connection':True }
    resp = client.send_vera_message(socket, data)
    print resp

    # TEST: Run scene 2
    data = { 'id':2, 'action': {'type': 'run' }, 'close_connection':True }
    resp = client.send_vera_message(socket, data)
    print resp

    # TEST: Turn device 1 on
    data = { 'id':1, 'action': {'type': 'set', 'attribute': {'power': 1} }, 'close_connection':False }
    resp = client.send_vera_message(socket, data)
    print resp

    # TEST: Get device 1 status
    data = { 'id':1, 'action': {'type': 'get' }, 'close_connection':False }
    resp = client.send_vera_message(socket, data)
    print resp

    # TEST: Turn device 1 off
    data = { 'id':1, 'action': {'type': 'set', 'attribute': {'power': 0} }, 'close_connection':True }
    resp = client.send_vera_message(socket, data)
    print resp

    # TEST: Get device 1 status
    data = { 'id':1, 'action': {'type': 'get' }, 'close_connection':True }
    resp = client.send_vera_message(socket, data)
    print resp

    # Remove the security assets copied earlier
    os.remove('rootCA.pem')
    os.remove('client.crt')
    os.remove('client.key')
    os.remove('psk.bin')
    
    # Close the connection
    client.close_connection_to_vera(socket)
    sys.exit()
        
if __name__ == '__main__':
    main()
