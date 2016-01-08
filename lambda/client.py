"""
This code handles voice interactions with the Vera example, built
using the Alexa Skills Kit.
"""

from __future__ import print_function
import socket, ssl
import json

def lambda_handler(event, context):

    # Route the incoming request based on type (LaunchRequest, IntentRequest,
    # etc.) The JSON body of the request is provided in the event parameter.
    print('event.session.application.applicationId=' +
          event['session']['application']['applicationId'])
    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    if (event['session']['application']['applicationId'] != 
        'amzn1.echo-sdk-ams.app.30b2da0d-fa39-4590-bd59-c9104c84832c'):
        raise ValueError('Invalid Application ID')

    req = event['request']
    ses = event['session']
    
    # On a new session, open the connection to Vera
    if event['session']['new']:
        print('on_session_started rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        
    if req['type'] == 'LaunchRequest':
        print('on_launch rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        return on_launch(req, ses)
    elif req['type'] == 'IntentRequest':
        print('on_intent rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        return on_intent(req, ses)
    elif req['type'] == 'SessionEndedRequest':
        print('on_session_ended rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        return on_session_ended(req, ses)

"""
Called when the user launches the skill without specifying what they want
"""
def on_launch(launch_request, session):
    # Play the welcome response
    return get_welcome_response()

"""
Called when the user specifies an intent for this skill
"""
def on_intent(intent_request, session):
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    
    # open a socket to our server
    socket, err_msg = open_connection_to_vera()
    if socket == None:
        return get_error_response(err_msg)
    
    # Dispatch to your skill's intent handlers
    if intent_name == "DeviceGetIntent":
        r = get_device(socket, intent, session)
    elif intent_name == "DeviceSetIntent":
        r = set_device(socket, intent, session)
    elif intent_name == "RunSceneIntent":
        r = run_scene(socket, intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        r = get_welcome_response()
    else:
        raise ValueError("Invalid intent")
        
    close_connection_to_vera(socket)
    return r

"""
Called when the user ends the session.
Is not called when the skill returns should_end_session=true
"""
def on_session_ended(session_ended_request, session):
    return
    # Don't need to do anything here
    
# --------------- Functions that connect to the listening server ------------------

def open_connection_to_vera():
    # Define the port/hostname for the server that we will connect to
    PORT = 3000
    HOST = 'hostname.dynamic-dns.net' #FIXME
    
    # Define paths to our security assets
    CA_PATH = './rootCA.pem'
    CLIENT_CERT_PATH = './client.crt'
    CLIENT_KEY_PATH = './client.key'
    
    print ('Configuring security parameters.')
    
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
    print ('connect to ' + HOST + ':' + str(PORT))
    
    try:
        secure_s.connect((HOST, PORT))
    except socket.error as msg:
        print ('socket error: ' + msg[1])
        return (None, msg[1])
    
    # return the socket object so other functions can use it
    return (secure_s, None)

def close_connection_to_vera(s):
    # Close the socket
    s.close()
    print ('closed connection')

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


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    session_attributes = {}
    card_title = 'Welcome to Vera'
    speech_output = 'Welcome to the Vera control application. ' \
                    'You can get or set device attributes, or run a scene.'
    
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = 'Please give me a command, for example, run scene 5.'
    
    should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_error_response(msg):
    speech_output = 'There was an error. The error says ' + msg
    
    return build_response({}, build_speechlet_response(
        'vera error', speech_output, None, True))

def get_device(socket, intent, session):
    session_attributes = {}
    should_end_session = False

    if 'Device' in intent['slots']:
        device = intent['slots']['Device']['value']
        session_attributes = {} # TODO - what is the purpose of these?
        
        data = { 'id':int(device), 'action': {'type': 'get' },'close_connection':True }
        
        resp = send_vera_message(socket, data)
        if resp['status'] == 0:
            speech_output = 'Device ' + resp['data']['name'] + ' is ' + resp['data']['status']
        else:
            speech_output = 'Error. ' + resp['err_str']
        
        reprompt_text = None
        should_end_session = True
    else:
        speech_output = 'I\'m not sure what you mean. Please try again.'
        reprompt_text = 'You can say something like, run scene 1.'
    
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
    
def set_device(socket, intent, session):
    session_attributes = {}
    should_end_session = False

    if 'Device' in intent['slots'] and 'Action' in intent['slots']:
        device = intent['slots']['Device']['value']
        action = intent['slots']['Action']['value']
        session_attributes = {} # TODO - what is the purpose of these?
        
        if action == 'on':
            value = 1
        elif action == 'off':
            value = 0
        else:
            value = 0
        data = { 'id':int(device), 'action': {'type': 'set', 'attribute': {'power':value} },'close_connection':True }
        
        resp = send_vera_message(socket, data)
        if resp['status'] == 0:
            speech_output = 'Successfully turned device ' + device + " " + action
        else:
            speech_output = 'Error. ' + resp['err_str']
        
        reprompt_text = None
        should_end_session = True
    else:
        speech_output = 'I\'m not sure what you mean. Please try again.'
        reprompt_text = 'You can say something like, turn device 1 on.'
        
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def run_scene(socket, intent, session):
    session_attributes = {}
    should_end_session = False

    if 'Scene' in intent['slots']:
        scene = intent['slots']['Scene']['value']
        session_attributes = {} # TODO - what is the purpose of these?
        
        data = { 'id':int(scene), 'action': {'type': 'run' },'close_connection':True }
        
        resp = send_vera_message(socket, data)
        if resp['status'] == 0:
            speech_output = 'Successfully executed scene ' + scene 
        else:
            speech_output = 'Error. ' + resp['err_str']
        
        reprompt_text = None
        should_end_session = True
    else:
        speech_output = 'I\'m not sure what you mean. Please try again.'
        reprompt_text = 'You can say something like, run scene 1.'
    
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': 'SessionSpeechlet - ' + title,
            'content': 'SessionSpeechlet - ' + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }
