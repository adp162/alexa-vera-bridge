#!/usr/bin/python
import socket, ssl
import json
import sys
import requests
import ConfigParser
import argparse
import threading
from avbmsg import AVBMessage

"""
This is the underlying data format that AVBMessage wraps in a header
and optionally encrypts. The various fields are as follows:

id: The numeric device id we want to interact with
action: A block that specifies the type of action and attribute data
  (only used for "set" action type)

  type: Type of action, currently support get/set/run
    - "get" - returns information about the device
    - "set" - sets the specified attributes to the specified values
    - "run" - only applies to scenes
  attribute: The only valid attribute is "power" for on/off type devices

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
    }
}

status: 0 indicates success, 1 an error, 2 simulated mode
err_str: a string indicating what failed that Alexa will dictate
id: the device id
data: data returned for a "get" action type

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

def handle_msg(s, vera_ip, vera_port, msg, psk):
    print 'got msg: ' + msg.dumps()
    resp_data = None

    # Create the message to send the response
    if psk is not None:
        resp = AVBMessage(encoding=AVBMessage.ENC_AES_CBC, psk=psk)
    else:
        resp = AVBMessage()

    # Parse the received message.
    data = msg.get_data()
    if data == None:
        print 'Failed to decode message!'
        resp_data = {'status': 1, 'err_str': 'bad message format', 'data': None}
        resp.set_data(resp_data)
        s.sendall(resp.dumps())
        return False

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
        resp_data = {'status': 1, 'err_str': 'invalid action', 'data': None}
        resp.set_data(resp_data)
        s.sendall(resp.dumps())
        return False

    if vera_ip is not None:
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
            resp_data = {'status': 2, 'err_str': 'requests exception', 'data': None}
            resp.set_data(resp_data)
            s.sendall(resp.dumps())
            return False

        if r.status_code != 200:
            print 'Non-200 response from Vera'
            print 'Code: ' + str(r.status_code)
            resp_data = {'status': 2, 'err_str': 'bad response from Vera', 'data': None}
            resp.set_data(resp_data)
            s.sendall(resp.dumps())
            return False
                        
        # Get the returned JSON from Vera (only for 'get' action)
        if action == 'get':
            status = r.json()

            verastate = 'unknown'
            veraname = 'unknown'
            for dev in status['devices']:
                if dev['id'] == obj_id:
                    for state in dev['states']:
                        if state['variable'] == 'Status':
                            verastate = state['value']
                        if state['variable'] == 'ConfiguredName':
                            veraname = state['value']
            resp_data = {'status': 0, 'err_str': None, 'data': {'status':verastate, 'name':veraname}}
        else:
            resp_data = {'status': 0, 'err_str': None, 'data': None}

        # Send the response
        resp.set_data(resp_data)
        print 'sending: ' + resp.dumps()
        s.sendall(resp.dumps())
    else:
        # Send the simulated response (echo received data back)
        resp_data = {'status': 2, 'err_str': 'vera simulation', 'data': data}
        resp.set_data(resp_data)
        print 'sending: ' + resp.dumps()
        s.sendall(resp.dumps())

    return True

# Entry point for new thread to handle specific client connection
def client_thread(secure_s, ip, port, psk):
    if psk is not None:
        m = AVBMessage(encoding=AVBMessage.ENC_AES_CBC, psk=psk)
    else:
        m = AVBMessage()
    
    while True:
        # Get a new message header
        chunks = []
        nb = 0
        while nb < AVBMessage.HEADER_SIZE:
            chunk = secure_s.recv(AVBMessage.HEADER_SIZE - nb)
            if chunk == '':
                print 'connection broken or closed by client'
                return
            chunks.append(chunk)
            nb += len(chunk)
        msg = ''.join(chunks)

        # Get the length and wait for the rest
        m.loads(msg)
        while nb < m.len():
            chunk = secure_s.recv(min(m.len() - nb, 1024))
            if chunk == '':
                print 'connection broken or closed by client'
                return
            chunks.append(chunk)
            nb += len(chunk)
        msg = ''.join(chunks)

        # Handle the message
        # Pass in IP address and port of vera (as strings). These are used to form
        # the URL to send the request to Vera.
        m.loads(msg)
        if not handle_msg(secure_s, ip, str(port), m, psk):
            print 'error handling message, server closing connection'
            secure_s.close()
            return

def main():
    # Read the configuration file
    cfg = ConfigParser.RawConfigParser()
    
    # If the user provides a file use that, otherwise use the default
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='path to server config file')
    parser.add_argument('--no-vera', action='store_true', help='switch to not send anything to Vera')
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
    #   3) root_ca plus client cert/key- give out certificate to client
    # Optionally, if psk is specified then we will use it to encrypt the message body
    security = 'none'
    psk = None
    if cfg.has_section('security'):
        security = 'ssl'
        if cfg.has_option('security', 'root_ca') and cfg.has_option('security', 'cert') and cfg.has_option('security', 'key'):
            security = 'ssl_mutual_auth'
            root_ca = cfg.get('security', 'root_ca')
            cert = cfg.get('security', 'cert')
            key = cfg.get('security', 'key')

        if cfg.has_option('security', 'psk'):
            try:
                f = open(cfg.get('security', 'psk'), 'r')
                # Note that the newline gets read, so we need to strip it
                psk = f.read().rstrip('\n')
                f.close()
            except IOError as e:
                print 'I/O error({0}): {1}'.format(e.errno, e.strerror)
                psk = None

    print ('configuring server security profile as "' + security + '"')
    if psk is not None:
        print ('using PSK from ' + cfg.get('security', 'psk'))

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

    # start listening (with max 5 connections queued)
    s.listen(5)

    # Setup the SSL context based on assets provided in the config file
    if security == 'none':
        # No need to create an SSL context
        pass
    elif security == 'ssl':
        # Setting recommended for max compatibility. Note however that SSLv2
        # and v3 are not considered secure.
        # See: https://docs.python.org/2/library/ssl.html
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.set_ciphers('HIGH')
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif security == 'ssl_mutual_auth':
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_verify_locations(root_ca)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(certfile=cert, keyfile=key)

    # If the switch to turn off Vera communication was specified we will
    # overwrite the vera_ip with None
    if args.no_vera:
        print 'Vera communication disabled.'
        vera_ip = None

    # Now that the server is listening, we can enter our main loop where we
    # wait for connections
    client_threads = []
    while True:
        print 'waiting for connection...'
        # accept() will block until a client has tried to connect
        (new_s, addr) = s.accept()
        print 'connection from ' + addr[0] + ':' + str(addr[1])
        
        # Wrap the socket in our SSL context to protect communications
        if security == 'none':
            secure_s = new_s
        else:
            secure_s = context.wrap_socket(new_s, server_side=True)

        # Kick off a thread to handle the new client
        t = threading.Thread(target=client_thread, args=(secure_s, vera_ip, vera_port, psk,))
        t.start()
        client_threads.append(t)
        print client_threads
        
if __name__ == '__main__':
    main()
