#!/usr/bin/python
import socket, ssl
import json
import sys
import requests

"""
JSON message format example (Client->Server):
{
    "id": 1,
    "action":
    {
        "type": "set", (Also "get", "run")
        "attribute": 
        {
            "power": 1
        }
    },
    "close_connection": true
}

JSON message format example (Server->Client):
{
    "status": 0,
    "err_str": null,
    "id": 1,
    "data":
    {
        "status": "1",
        "name": "Bedroom Outlet"
    }
}
"""

def handle_msg(s, msg):
    VERA_IP = '0.0.0.0' # FIXME
    
    print 'got msg: ' + msg
    # Parse the received message.
    data = json.loads(msg)
    if data == None:
        print 'Failed to decode message!'
        resp = {'status': 1, 'err_str': 'bad message format', 'data': None}
        s.sendall(json.dumps(resp))
        return True
    
    # Turn message into appropriate Vera action
    # Currently, we support 3 types of actions (get/set/run). Get/set apply to
    # devices while run appies to scenes
    obj_id = data['id']
    action = data['action']['type']
    if action == 'run':
        vera_params = {'id':'lu_action', 'output_format':'json',
                       'SceneNum':str(obj_id),
                       'serviceId':'urn:micasaverde-com:serviceId:HomeAutomationGateway1',
                       'action':'RunScene'
                      }
    elif action == 'set':
        vera_params = {'id':'lu_action', 'output_format':'json',
                       'DeviceNum':str(obj_id),
                       'serviceId':'urn:upnp-org:serviceId:SwitchPower1',
                       'action':'SetTarget',
                       'newTargetValue': str(data['action']['attribute']['power'])
                      }
    elif action == 'get':
        vera_params = {'id':'status'}

    else:
        print 'invalid action'
        resp = {'status': 1, 'err_str': 'invalid action', 'data': None}
        s.sendall(json.dumps(resp))
        return True
    
    # Send the appropriate HTTP request to Vera
    dest = 'http://' + VERA_IP + ':3480/data_request'
    r = requests.get(dest, params=vera_params)
    if r.status_code != 200:
        print 'Error contacting Vera!'
        resp = {'status': 2, 'err_str': 'error contacting Vera', 'data': None}
        s.sendall(json.dumps(resp))
        return True
                        
    # Get the returned JSON from Vera (only for 'get' action)
    resp_data = None
    if action == 'get':
        status = r.json()

        for dev in status['devices']:
            if dev['id'] == obj_id:
                for state in dev['states']:
                    if state['variable'] == 'Status':
                        verastate = state['value']
                    if state['variable'] == 'ConfiguredName':
                        veraname = state['value']
        resp_data = {'status':verastate, 'name':veraname}
    
    # Send the response
    resp = {'status': 0, 'err_str': None, 'data': resp_data}
    print 'sending: ' + json.dumps(resp)
    s.sendall(json.dumps(resp))
    
    return data['close_connection']
        
def main():
    # Define the port that we will listen on
    PORT = 3000
    
    # Define paths to our security assets
    CA_PATH = './base_rootCA.pem'
    SERVER_CERT_PATH = './.crt' # FIXME
    SERVER_KEY_PATH = './.key' # FIXME
    
    print 'Configuring security parameters.'
    
    # Create the SSL context to authenticate client
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_verify_locations(CA_PATH)
    context.load_cert_chain(certfile=SERVER_CERT_PATH, keyfile=SERVER_KEY_PATH)
    context.verify_mode = ssl.CERT_REQUIRED
    
    # Create the socket (For SSL we must use SOCK_STREAM)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the socket to the port
    print 'starting lambda_listener on ' + socket.gethostname() + ':' + str(PORT)
    print
    # Do some error checking as binds can fail if the port is being used by
    # someone else
    try:
        s.bind(('', PORT))
    except socket.error as msg:
        print 'socket bind() failed!'
        print '(err ' + str(msg[0]) + '): ' + msg[1]
        sys.exit()
        
    # start listening (with max 3 connections queued)
    s.listen(3)

    # Now that the server is listening, we can enter our main loop where we
    # wait for connections
    while True:
        # accept() will block until a client has tried to connect
        (new_s, addr) = s.accept()
        print 'connection from ' + addr[0] + ':' + str(addr[1])
        
        # Wrap the socket in our SSL context to protect communications 
        secure_s = context.wrap_socket(new_s, server_side=True)
        
        # The message protocol is pretty simple. It is a 4 byte header and payload.
        # The header is simply the payload length.
        client_done = False
        
        while client_done == False:
            # Wait for a new message
            msg = secure_s.read()
        
            # Parse the message
            client_done = handle_msg(secure_s, msg)
        
        # Close the connection
        secure_s.close()
        print 'closed connection'
        
if __name__ == '__main__':
    main()
