#!/usr/bin/python
import sys
import os
from shutil import copyfile
import argparse
import time
import threading

# Actually use the client code to test sending server message
# Note that you must have ../lambda in your PYTHONPATH variable for this
# to work (e.g. export PYTHONPATH=../lambda)
import client

# Thread to send a bunch of messages to the server
def client_thread(i):
    print 'starting thread ' + str(i)

    data = [ { 'id':1, 'action': {'type': 'get' } },
             { 'id':2, 'action': {'type': 'set', 'attribute': {'power': 0} } },
             { 'id':3, 'action': {'type': 'run' } },
             { 'id':4, 'action': {'type': 'get' } },
             { 'id':5, 'action': {'type': 'set', 'attribute': {'power': 1} } },
             { 'id':6, 'action': {'type': 'run' } } ]

    # Send the messages a bunch of times
    for j in range(100):
        send_data(data)

    print 'thread ' + str(i) + ' finished'

# Pass in a list of data (or single element)
def send_data(data):
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

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', help='action type', type=str, choices=['get', 'set', 'run'])
    parser.add_argument('-d', '--device', help='device id', type=int)
    parser.add_argument('-c', '--command', help='the command to send', type=str, choices=['on', 'off'])
    args = parser.parse_args()

    # Change to lambda directory because all the client.py functions assume the
    # files they need (certs, config, etc.) are in the same directory
    print 'in ' + os.getcwd()
    os.chdir('../lambda')
    print 'changed to ' + os.getcwd()

    # Temporarily copy sample security assets to lambda directory
    copyfile('../security/sample/rootCA.pem', './rootCA.pem')
    copyfile('../security/sample/client.crt', './client.crt')
    copyfile('../security/sample/client.key', './client.key')
    copyfile('../security/sample/psk.bin', './psk.bin')

    # Did we specify any of the optional arguments?
    if args.action or args.device or args.command:
        # Do some sanity checks
        if args.action is None or args.device is None:
            parser.error('You must specify device, and action')
        if args.action == 'set' and args.command is None:
            parser.error('You must specify a command with set action')

        # Setup the data, run the request, then exit
        attr = None
        if args.command == 'on':
            attr = {'power': 1}
        elif args.command == 'off':
            attr = {'power': 0}
        data = { 'id':args.device, 'action': {'type': args.action, 'attribute': attr } }
        run_test(0, data)
    else:
        # TEST: Run scene 1
        print 'Running test #1'
        data = { 'id':1, 'action': {'type': 'run' } }
        send_data(data)
        print

        # TEST: Run scene 2
        print 'Running test #2'
        data = { 'id':2, 'action': {'type': 'run' } }
        send_data(data)
        print

        # TEST: Turn device 1 on and get status
        print 'Running test #3'
        data = [ { 'id':1, 'action': {'type': 'set', 'attribute': {'power': 1} } },
                 { 'id':1, 'action': {'type': 'get' } } ]
        send_data(data)
        print

        # TEST: Get status, turn device 1 off, get status again
        print 'Running test #4'
        data = [ { 'id':1, 'action': {'type': 'get' } },
                 { 'id':1, 'action': {'type': 'set', 'attribute': {'power': 0} } },
                 { 'id':1, 'action': {'type': 'get' } } ]
        send_data(data)
        print

        # TEST: leave socket open (eventually server should kill)
        print 'Running test #5'
        (socket, msg) = client.open_connection_to_vera()
        print 'sleeping for 10s...'
        # Server will close() the socket
        time.sleep(10)
        try:
            resp = client.send_vera_message(socket, { 'id':1, 'action': {'type': 'get' } } )
        except RuntimeError as e:
            print 'Failed correctly with: ' + str(e)
        print

        # TEST: poorly formatted message (should catch AVBMessage exception)
        print 'Running test #6'
        (socket, msg) = client.open_connection_to_vera()
        try:
            resp = client.send_vera_message(socket, 'bad message')
        except ValueError as e:
            print 'Failed correctly with: ' + str(e)
        print

        # TEST: message too long (should catch AVBMessage exception)
        print 'Running test #7'
        (socket, msg) = client.open_connection_to_vera()
        try:
            # Send a super long tag to ensure resulting JSON string is too long
            resp = client.send_vera_message(socket, { 't'*9999:1 } )
        except ValueError as e:
            print 'Failed correctly with: ' + str(e)
        print

        # TEST: bombard server with simultaneous requests
        print 'Running test #8'
        threads = []
        for i in range(10):
            t = threading.Thread(target=client_thread, args=(i,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print

    # Remove the security assets copied earlier
    os.remove('rootCA.pem')
    os.remove('client.crt')
    os.remove('client.key')
    os.remove('psk.bin')
        
if __name__ == '__main__':
    main()
