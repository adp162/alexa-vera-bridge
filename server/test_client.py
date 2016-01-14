#!/usr/bin/python
import sys
import os

def main():
    # To run the client code we have to change to that directory since a bunch of
    # files in there are pathed relative to that directory. We also have to add that
    # path to the module import path.
    os.chdir('../lambda')
    sys.path.append('./')

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

    # TODO - add more test cases

    # Close the connection
    client.close_connection_to_vera(socket)
    sys.exit()
        
if __name__ == '__main__':
    main()
