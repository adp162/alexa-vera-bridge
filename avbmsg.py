# Defines the class for an Alexa-Vera-Bridge Message
# These messages are passed from client (e.g. Lambda function)
# to server (e.g. code running on local network). The server is responsible
# for taking a message and turning it into a command to issue to
# Vera through the UpnP interface.
import json
import base64
# FIXME - should probably make these conditional imports
from Crypto.Cipher import AES
from Crypto import Random

class AVBMessage:
    # Constants
    HEADER_SIZE = 8
    LENGTH_FIELD_SIZE = 4
    VERSION_FIELD_SIZE = 2
    ENCODING_FIELD_SIZE = 2
    PSK_256_SIZE = 44 # bytes for 256 bit PSK encoded in base64
    IV_SIZE = 24 # bytes for 16 byte IV encoded in base64
    MAX_MESSAGE_SIZE = 9999

    # Message version enums
    VER_1 = 1

    # Encoding enums
    ENC_PLAIN = 1
    ENC_AES_CBC = 2

    def __init__(self, version=None, encoding=None, psk=None, data=None):
        # Fill in the header, defaults are version 1, plaintext encoding
        self.length = 8
        self.version = 1
        self.encoding = 1
        self.data = ''
        self.psk = ''
        self.iv = ''
        if data is not None:
            self.set_data(data)
        if version is not None:
            # Check that version is valid
            if version != AVBMessage.VER_1:
                raise ValueError('Unsupported version type')
            self.version = version
        if encoding is not None:
            # Check that encoding is a valid type
            if encoding != AVBMessage.ENC_PLAIN and encoding != AVBMessage.ENC_AES_CBC:
                raise ValueError('Unsupported encoding type')
            self.encoding = encoding
        if psk is not None:
            self.set_psk(psk)

    # This function takes a base64 encoded key as a string
    def set_psk(self, psk):
        # The key size allowed depends on the encryption being used.
        if self.encoding == AVBMessage.ENC_PLAIN:
            # No PSK for plaintext encoding, raise error
            raise ValueError('PSK not supported for ENC_PLAIN')
        elif self.encoding == AVBMessage.ENC_AES_CBC:
            # Key must be 16/24/32 bytes long (for our case, enforce 32 bytes)
            if len(psk) != AVBMessage.PSK_256_SIZE:
                raise ValueError('Bad PSK length')
            self.psk = psk
        
    # Return the currently set PSK as a base64 encoded string
    def get_psk(self):
        return self.psk

    # This function takes a dictionary object (data) and converts it to a JSON
    # string that is stored as the message body
    def set_data(self, data):
        # Turn to JSON string
        #FIXME - catch json errors
        self.data = json.dumps(data)
        self.iv = ''

        # Generate random IV and encrypt using PSK
        if self.encoding == AVBMessage.ENC_AES_CBC:
            r = Random.new()
            iv = r.read(AES.block_size)
            key = base64.b64decode(self.psk)
            enc_cipher = AES.new(key, AES.MODE_CBC, iv)
            pad = '*' * (AES.block_size - (len(self.data) % AES.block_size))
            enc = enc_cipher.encrypt(self.data + pad)

            # Replace with IV + encrypted string
            self.iv = base64.b64encode(iv)
            self.data = base64.b64encode(enc)

        # Update the header
        self.length = AVBMessage.HEADER_SIZE + len(self.iv) + len(self.data)
        if self.length > AVBMessage.MAX_MESSAGE_SIZE:
            raise ValueError('Message is too long')

    # This function returns the message contents as a dictionary
    def get_data(self):
        if self.data == '':
            return None
        data = self.data

        # Decrypt if needed
        if self.encoding == AVBMessage.ENC_AES_CBC:
            key = base64.b64decode(self.psk)
            iv = base64.b64decode(self.iv)
            dec_cipher = AES.new(key, AES.MODE_CBC, iv)
            dec = dec_cipher.decrypt(base64.b64decode(self.data))
            data = dec.rstrip('*')

        # Parse the JSON to a dict and return
        # FIXME - catch json errors
        return json.loads(data)

    # Returns the message length
    def len(self):
        return self.length

    # Function to print out the message in a nice format
    def pprint(self):
        print 'AVB Header'
        print '  Length:   {:d}'.format(self.length)
        print '  Version:  {:d}'.format(self.version)
        print '  Encoding: {:d}'.format(self.encoding)
        print 'AVB Body'
        if self.encoding == AVBMessage.ENC_AES_CBC:
            print '  IV: ' + self.iv
        print '  ' + str(self.get_data())

    # Function to dump the raw string representation of the message
    def dumps(self):
        hdr = '{:0{width}d}'.format(self.length, width=AVBMessage.LENGTH_FIELD_SIZE)
        hdr = hdr + '{:0{width}d}'.format(self.version, width=AVBMessage.VERSION_FIELD_SIZE)
        hdr = hdr + '{:0{width}d}'.format(self.encoding, width=AVBMessage.ENCODING_FIELD_SIZE)
        return hdr + self.iv + self.data

    # Funtion to load a message from a string (essentially a parser)
    def loads(self, msg):
        # Check to make sure minimum length is met
        if len(msg) < AVBMessage.HEADER_SIZE:
            raise ValueError('Message is too small')

        # Take the header bytes and populate fields
        i = 0
        self.length = int(msg[i:AVBMessage.LENGTH_FIELD_SIZE])
        i += AVBMessage.LENGTH_FIELD_SIZE
        self.version = int(msg[i:i+AVBMessage.VERSION_FIELD_SIZE])
        i += AVBMessage.VERSION_FIELD_SIZE
        self.encoding = int(msg[i:i+AVBMessage.ENCODING_FIELD_SIZE])
        i += AVBMessage.ENCODING_FIELD_SIZE

        # Strip out the IV if it is present
        if self.encoding == AVBMessage.ENC_AES_CBC:
            self.iv = msg[i:i+AVBMessage.IV_SIZE]
            i += AVBMessage.IV_SIZE

        # The rest of the message is data
        self.data = msg[i:]
