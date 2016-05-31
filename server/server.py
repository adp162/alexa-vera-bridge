#!/usr/bin/python
import socket, ssl
import json
import sys
import requests
import ConfigParser
import argparse

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

def handle_msg(s, vera_ip, vera_port, msg):
    
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
    dest = 'http://' + vera_ip + ':' + vera_port + '/data_request'
    print
    print 'sending to: ' + dest
    print 'params: ' + str(vera_params)
    print

    try:
        r = requests.get(dest, params=vera_params)
    except requests.exceptions.RequestException as e:
        print e
        resp = {'status': 2, 'err_str': 'requests exception', 'data': None}
        s.sendall(json.dumps(resp))
        return True

    if r.status_code != 200:
        print 'Non-200 response from Vera'
        print 'Code: ' + str(r.status_code)
        resp = {'status': 2, 'err_str': 'bad response from Vera', 'data': None}
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
    # Read the configuration file
    cfg = ConfigParser.RawConfigParser()
    
    # If the user provides a file use that, otherwise use the default
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='path to server config file')
    args = parser.parse_args()
    cfg_file = './server.cfg'
    if args.config is not None:
        cfg_file = args.config
    try:
        cfg.readfp( open(cfg_file) )
    except:
        print 'error reading configuration file: ' + cfg_file
        sys.exit()

    # Setup the defaults
    port = 3000
    vera_port = 3480

    # Make sure we have the required sections in the config file
    if cfg.has_section('vera'):
        if cfg.has_option('vera', 'ip'):
            vera_ip = cfg.get('vera', 'ip')
        else:
            print 'missing Vera IP address'
            sys.exit()

        if cfg.has_option('vera', 'port'):
            vera_port = cfg.getint('vera', 'port')
    else:
        print 'missing [vera] section in configuration file'
        sys.exit()

    if cfg.has_option('server', 'port'):
        port = cfg.getint('server', 'port')

    # See what security options are specified in the config file
    # Valid combinations are:
    #   1) none - just do regular connection (INSECURE)
    #   2) just the section - use ssl/tls but with no auth
    #   3) root_ca only - ssl/tls with client validation
    #   4) root_ca plus client cert/key- give out certificate to client
    security = 'none'
    if cfg.has_section('security'):
        security = 'ssl'
        if cfg.has_option('security', 'root_ca'):
            security = 'ssl_client_auth'
            root_ca = cfg.get('security', 'root_ca')
            if cfg.has_option('security', 'cert') and cfg.has_option('security', 'key'):
                security='ssl_mutual_auth'
                cert = cfg.get('security', 'cert')
                key = cfg.get('security', 'key')

    print ('configuring server security profile as "' + security + '"')
    
    # Open up the port and listen for connections
    # Create the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the socket to the port
    print 'starting server on ' + socket.gethostname() + ':' + str(port)
    print
    # Do some error checking as binds can fail if the port is being used by
    # someone else
    try:
        s.bind(('', port))
    except socket.error as msg:
        print 'socket bind() failed!'
        print '(err ' + str(msg[0]) + '): ' + msg[1]
        sys.exit()

    # start listening (with max 3 connections queued)
    s.listen(3)

    # Setup the SSL context based on assets provided in the config file
    if security == 'none':
        # No need to create an SSL context
        pass
    elif security == 'ssl':
        # Create defautl SSL context with no authentication
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif security == 'ssl_client_auth':
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_verify_locations(root_ca)
        context.verify_mode = ssl.CERT_REQUIRED
    elif security == 'ssl_mutual_auth':
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_verify_locations(root_ca)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(certfile=cert, keyfile=key)

    # Now that the server is listening, we can enter our main loop where we
    # wait for connections
    while True:
        # accept() will block until a client has tried to connect
        (new_s, addr) = s.accept()
        print 'connection from ' + addr[0] + ':' + str(addr[1])
        
        # Wrap the socket in our SSL context to protect communications
        if security == 'none':
            secure_s = new_s
        else:
            secure_s = context.wrap_socket(new_s, server_side=True)

        # Kick off a thread to handle the new client
        # TODO
        
        # FIXME - this goes in the client thread
        # Should have 2 loops - recv header loop followed by recv msg loop
        # the client will always wait for a response from the server, but
        # close connection tells the server that the client is done
        # We should also check for rcv() returning '' as this means the socket died
        # Have a max length on the message
        #header: <msg length 4 bytes, version 2 bytes, enc 2 bytes, iv 16 bytes?>
        #body: json object (potentially encrypted)

        client_done = False
        while client_done == False:
            # Wait for a new message
            msg = secure_s.recv(1024)
        
            # Handle the message
            # Pass in IP address and port of vera (as strings). These are used to form
            # the URL to send the request to Vera.
            client_done = handle_msg(secure_s, vera_ip, str(vera_port), msg)
        
        # Close the connection
        secure_s.close()
        print 'closed connection'
        
if __name__ == '__main__':
    main()
