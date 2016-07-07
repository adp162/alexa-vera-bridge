#!/usr/bin/python
import sys
import os
from shutil import copyfile

# Actually use the client code to test sending server message
# Note that you must have ../lambda in your PYTHONPATH variable for this
# to work (e.g. export PYTHONPATH=../lambda)
import client

# Pass in a list of data (or single element)
def run_test(num, data):
    print 'Running test #' + str(num)

    # Try connecting to the Vera server
    (socket, msg) = client.open_connection_to_vera()
    if socket == None:
        print 'Error connecting to AVBServer: ' + msg
        sys.exit()

    # Send the test messages and check response
    if type(data) is list:
        for d in data:
            resp = client.send_vera_message(socket, d)
            assert d == resp['data']
    else:
        resp = client.send_vera_message(socket, data)
        assert data == resp['data']

    # Close the connection
    client.close_connection_to_vera(socket)

def main():
    # NOTE: These tests should run with the server option "--no-vera" specified
    #   since they are designed to check the response matches the data sent.
    #   To send a real command to Vera, use the command line argument described
    #   below.

    # TODO argparse for real vera command

    # Change to lambda directory because all the client.py functions assume the
    # files they need (certs, config, etc.) are in the same directory
    os.chdir('../lambda')

    # Temporarily copy sample security assets to lambda directory
    copyfile('../security/sample/rootCA.pem', './rootCA.pem')
    copyfile('../security/sample/client.crt', './client.crt')
    copyfile('../security/sample/client.key', './client.key')
    copyfile('../security/sample/psk.bin', './psk.bin')

    # TEST: Run scene 1
    data = { 'id':1, 'action': {'type': 'run' } }
    run_test(1, data)

    # TEST: Run scene 2
    data = { 'id':2, 'action': {'type': 'run' } }
    run_test(2, data)

    # TEST: Turn device 1 on and get status
    data = [ { 'id':1, 'action': {'type': 'set', 'attribute': {'power': 1} } },
             { 'id':1, 'action': {'type': 'get' } } ]
    run_test(3, data)

    # TEST: Get status, turn device 1 off, get status again
    data = [ { 'id':1, 'action': {'type': 'get' } },
             { 'id':1, 'action': {'type': 'set', 'attribute': {'power': 0} } },
             { 'id':1, 'action': {'type': 'get' } } ]
    run_test(4, data)

    # TODO - more tests
    # TEST: leave socket open (eventually server should kill)
    # TEST: poorly formatted message (server should kill)
    # TEST: bombard server with simultaneous requests

    # Remove the security assets copied earlier
    os.remove('rootCA.pem')
    os.remove('client.crt')
    os.remove('client.key')
    os.remove('psk.bin')
        
if __name__ == '__main__':
    main()
