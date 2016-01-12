# Talking to Your House
#### Integrating Amazon Echo with the Vera Home Automation Controller

## Table of Contents
1. [Introduction](https://github.com/adp162/alexa-vera-bridge#introduction)
2. [Overview](https://github.com/adp162/alexa-vera-bridge#overview)
3. [Quick Start](https://github.com/adp162/alexa-vera-bridge#quick-start)
4. [Background](https://github.com/adp162/alexa-vera-bridge#background)
   1. [Alexa Skills Kit](https://github.com/adp162/alexa-vera-bridge#alexa-skills-kit-ask)
   2. [AWS Lambda](https://github.com/adp162/alexa-vera-bridge#amazon-web-services-aws-lambda)
   3. [Python](https://github.com/adp162/alexa-vera-bridge#python)
   4. [Client/Server Communications](https://github.com/adp162/alexa-vera-bridge#clientserver-communications)
   5. [Raspbian](https://github.com/adp162/alexa-vera-bridge#raspbian)
   6. [Universal Plug and Play](https://github.com/adp162/alexa-vera-bridge#universal-plug-and-play-upnp)
5. [Teaching Alexa a New Trick](https://github.com/adp162/alexa-vera-bridge#teaching-alexa-a-new-trick)
   1. [Signing up for Accounts](https://github.com/adp162/alexa-vera-bridge#signing-up-for-accounts)
   2. [Create a new Lambda Function](https://github.com/adp162/alexa-vera-bridge#create-a-new-lambda-function)
   3. [Register a New Alexa Skill](https://github.com/adp162/alexa-vera-bridge#register-a-new-alexa-skill)
   4. [Customizing our New Skill](https://github.com/adp162/alexa-vera-bridge#customizing-our-new-skill)
   5. [Setting up the Client](https://github.com/adp162/alexa-vera-bridge#setting-up-the-client)
   6. [Testing the Skill](https://github.com/adp162/alexa-vera-bridge#testing-the-skill)
6. [Hearing Alexa at Home](https://github.com/adp162/alexa-vera-bridge#hearing-alexa-at-home)
   1. [Security Considerations](https://github.com/adp162/alexa-vera-bridge#security-considerations)
   2. [A Few Other Considerations](https://github.com/adp162/alexa-vera-bridge#a-few-other-considerations)
   3. [Setting up the Server](https://github.com/adp162/alexa-vera-bridge#setting-up-the-server)
7. [Talking to Vera](https://github.com/adp162/alexa-vera-bridge#talking-to-vera)
8. [Related Work](https://github.com/adp162/alexa-vera-bridge#related-work)

## Introduction
Speech as an interface to the recently introduced cadre of digital “smart” things has been sorely lacking.  With the release of Echo, Amazon realized they struck a chord with consumers who had been waiting for a more natural way to engage with their devices.  Echo brought two key technologies to bear to allow this to happen – far-field speech recognition and natural language processing.  Echo is the hardware responsible for the signal processing required to extract clean speech out of a noisy environment while Alexa is the cloud service that converts this speech into text and extracts the user's intent from that text.

The beauty of Echo/Alexa is that the interaction model isn’t limited to certain applications.  Echo/Alexa is a platform on which any applications can be built.  The rest of this primer focuses on building an application to interact with devices used in home automation.  In particular, we focus on using the Alexa Skills Kit (ASK) to interface with the Vera smart home hub.  The primer is divided into several sections.  The Overview section introduces the high level architecture.  The Quick Start section gives setup instructions if you basically understand what you're doing.  The Background section introduces all the concepts covered at a high level.  It is useful to at least browse this section to make sure you understand the various pieces being put together.  Subsequent sections go into greater detail on each component.

## Overview
![architecture](https://cloud.githubusercontent.com/assets/16480218/12191735/00d317ae-b58d-11e5-8d52-45060c3e3232.png)
###### Figure 1 - System Architecture

At a high level, our goal is to have our Echo control our Vera home automation hub.  To do so, we rely on some Amazon services and a Raspberry Pi computer.  The Raspberry Pi can easily be substituted for a PC as all it is doing is running a simple server written in Python.  Figure 1 is divided in a local network (i.e. everything behind our router) where all our devices are located and the Internet, where the Amazon services are located.  The solid black lines indicate physical connections (e.g. wired or wireless Ethernet) while the orange pipes indicate logical connections between devices (i.e. sockets).

Bridging the line between the local network and the Internet can be tricky to do correctly, so we devote some time to discussing security considerations for our approach in a later section.  Technically, there are similar issues to take into account for the Amazon services running inside the cloud (specifically the AWS cloud) but we can gloss over those details as AWS does a great job of abstracting away that complexity for the user.  We can also assume that the connection between Echo and Alexa is secure.  There is more on this in a later section but the basic protocol is HTTP with SSL/TLS (HTTPS) to authenticate the server and encrypt the connection (to prevent eavesdropping and other attacks).  User authentication is done through the Alexa companion application.

## Quick Start
TODO - finish filling this out
* Register for Amazon accounts (links)
* Create the lambda function
* create the alexa skill
* create certificates
* upload lambda function (modify config)
* install/run server (modify config)

## Background
This section gives a brief description of the topics covered in this example.  An in depth treatment of everything is not possible, so references are provided.  The primer is self contained so you should be able to complete the implementation without consulting external resources.  However, modifications or more advanced configurations will probably require further reading.

#### Alexa Skills Kit (ASK)
ASK is a platform provided by Amazon for building voice-driven skills.  A skill is developed by specifying a set of criteria by which to interpret spoken utterances.  You can think of writing new skills as analogous to writing a program, only the structure is more limited with Alexa skills.  Skills are specified by their Intent Schema.  Intents describe actions we want to take based on spoken commands.  The interaction flow with a custom Alexa skill is shown in Figure 2.

![alexa_skills_flow](https://cloud.githubusercontent.com/assets/16480218/12194104/24b0ea38-b5a2-11e5-8656-7f653ff694f4.png)
###### Figure 2 - Alexa Skills Kit Flow

##### References
* [ASK Homepage](https://developer.amazon.com/appsandservices/solutions/alexa/alexa-skills-kit)
* [ASK Getting Started Guide](https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/getting-started-guide)

#### Amazon Web Services (AWS) Lambda
Lambda is an on-demand compute service provided by AWS.  Ordinarily, a web service would require a continuously running server to handle requests.  With Lambda, compute resources are allocated and freed on demand.  Lambda functions run on machines that run Amazon Linux – a Linux distribution provided by Amazon.  Lambda is extensively documented if you want to learn more about the execution environment.  With the AWS Free Tier up to 1 million Lambda requests per month are free.

##### References
* [Lambda documentation](http://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
* [Installing AWS CLI](http://docs.aws.amazon.com/cli/latest/userguide/installing.html)
* [AWS CLI Lambda Reference](http://docs.aws.amazon.com/cli/latest/reference/lambda/index.html)

#### Python
Python is a general purpose, high level programming language.  It consistently ranks high in the list of the most popular languages and is a great language to learn programming with.  Python currently comes in two main versions 2 (latest Python 2.7.11) and 3 (latest Python 3.5.1) and can be downloaded from http://www.python.org.  There are compatibility differences between the two versions but Python 3 will likely gradually replace Python 2.  Currently AWS Lambda uses Python 2.7.  The code in this primer was written and tested with Python 2.7.  Note that there are dependencies that require Python 2.7.9 or later (for the ssl library).

##### References
* [Official Python documentation](https://www.python.org/doc/)
* [Online Interactive Tutorials](http://www.learnpython.org/)
* [Code Academy - Python](https://www.codecademy.com/learn/python)
* [Cryptography in Python](http://www.laurentluce.com/posts/python-and-cryptography-with-pycrypto/)

#### Client/Server Communications
The components in the architecture in Figure 1 talk to each other over a network.  One of the most common ways of doing this is with TCP sockets.  This is a huge topic by itself and limited information is provided in this primer.  The Reference section provides a good starting point to learn more.

##### References
* [Sockets (Python)](https://docs.python.org/2/howto/sockets.html)
* [Certificates](https://en.wikipedia.org/wiki/Public_key_certificate)
* [TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security)
* [Being your own CA](http://datacenteroverlords.com/2012/03/01/creating-your-own-ssl-certificate-authority/)
* [SSL/TLS best practices](https://hynek.me/articles/hardening-your-web-servers-ssl-ciphers/)
* [NSA security recommendations](https://www.nsa.gov/ia/programs/suiteb_cryptography/index.shtml)

#### Raspbian
Raspbian is a distribution of Linux for the Raspberry Pi.  It is based on Debian (as is the popular desktop distribution Ubuntu) and there is a wealth of information available online.  It is useful to note that a distribution does not equal an operating system.  In other words, Raspbian is not Linux.  Rather, a distribution packages the operating system (Linux) along with packages (applications) that are pre-compiled for a particular architecture (Rasperry Pi).

##### References
* [Raspberry Pi Forums](https://www.raspberrypi.org/forums/)
* [Setting up NoIP on Raspberry Pi](http://cookuop.co.uk/install-noip-on-raspberry-pi/)

#### Universal Plug and Play (UPnP)
UPnP is a networking protocol for device to device communication.  Vera uses UPnP to talk to devices and created their own software platform LuuP (Lua-UPnP) which combines the scripting language Lua with UPnP.  Vera also exposes its UPnP interface over HTTP, which is the method this primer uses to interact with Vera.

##### References
* [Vera HTTP interface](http://wiki.micasaverde.com/index.php/UI_Notes#The_HTTP_interface)
* [Vera Controller UI](http://wiki.micasaverde.com/index.php/UI_Simple)
* [UPnP Commands](http://wiki.micasaverde.com/index.php/Luup_Requests)

## Teaching Alexa a New Trick

### Signing up for Accounts
First, you need to sign up for a few accounts to access the things we’ll be using for Echo and AWS.  The ASK registration happens through the standard developer portal (https://developer.amazon.com).  Simply register for an account using your existing Amazon credentials.  You’ll also need to register an AWS account at https://aws.amazon.com.  You can use your Amazon credentials but will need to provide a credit card number.  The AWS Free Tier provides free access to a number of services permanently and free access to some things for 12 months.  Everything we need falls under the permanent free category, but take care if you play around with other services since they automatically bill after the 12-month trial period.

### Create a New Lambda Function
We’ll first need to create a Lambda function to handle requests from our Echo.  This is a simple option so that we don’t have to run our own web service.  Log into your AWS account.  A key to understanding how AWS works is that services operate in geographic regions (corresponding to where Amazon has data centers).  For some things (like running a web server) you want to deploy instances of machines or storage across multiple regions for redundancy.  For Alexa skills in Lambda there is actually only a single region (US East) that services that skill.  If you don’t have this region selected, then you’ll get a warning when trying to create the Lambda function.  Also, if you ever login and don’t see things you have created, don’t panic, ensure that the appropriate region where you created those things is selected.  With US East (it will show “N. Virginia”) selected click the AWS Lambda link.  The following steps will setup our Lambda function to link to our Alexa skill.

1. Click “Get Started Now”.  
2. In the filter box type “alexa” and select the “alexa-skills-kit-color-expert-python” blueprint.  This will let us write our function in Python.
3. Click “Next” and name the function “myTestSkill”.  Leave everything else as the defaults and click “Next” again.
4. Once the function is created note the ARN (located in the upper right corner of the page).  We’ll need to provide this ARN to our Alexa Skill.

### Register a New Alexa Skill
With ARN in hand, it is time to register the new skill in the developer portal.  Initially, you’ll be restricted to viewing your skill on your devices, but if you ever want to “publish” the skill so anyone can use it there is a certification process you can go through (similar to publishing an app in an app store).  The steps to register a new skill are as follows:

1. From the developer portal click “Apps & Services” then “Alexa”.
2. Click “Getting Started” under Alexa Skills Kit and then “Add a New Skill”.
3. Fill in the Skill Information page (Name: “MyTestSkill”, Invocation Name: “My Test”, Endpoint: “Lambda ARN”, copy ARN from Lambda) and click “Next”.

Now, we need to give Alexa some context so she can interpret what was said.  There is a lot to read and understand around designing voice interfaces, but since we’re using the default Lambda blueprint we can follow that example as a template for our interaction model.  In the default blueprint we implement a “color picker” that allows us to tell Alexa what our favorite color is.  In order for Alexa to parse the utterance we need to define intents and provide sample data.  An intent is simply an action that fulfills a user’s spoken requests.  Intents can have arguments associated with them called slots.  Each slot has a name and a data type.  There are some built in types but specifying custom types is also possible.  The intents are defined as a JSON formatted structure.

We have an intent that sets the color (MyColorIsIntent) and one that gets the color (WhatsMyColorIntent).  The help intent is a built in intent to prompt the user when Alexa can’t understand what we’re trying to say.  Notice that the MyColorIsIntent has a slot associated with it with a data type LIST_OF_COLORS.  This is a custom type that we need to define.  To do this we simply click “Add Slot Type” then type the name in “Enter Type” and a list of all possible values (one per line) in the “Enter Values” box.

The last piece of information we supply are sample utterances.  These serve as patterns that let Alexa match up what was said to various intents and to appropriately parse arguments (slots) to those intents.  For the sample utterances it is important to try and cover as many variations as possible for each intent.

### Customizing our New Skill
Now that we have the basic pieces in place, we need to modify our skill so that it does something useful.  For this primer we will illustrate a basic device/action paradigm and leave it to the reader to extend this example.  At this point it is probably useful to rename our skill so that we can speak to Alexa in a more natural way.  Change the name to “VeraControllerSkill” and the invocation name to “vera”.  Now let’s define our intents.

```
{
  "intents": [
    {
      "intent": "DeviceSetIntent",
      "slots": [
        {
          "name": "Device",
          "type": "AMAZON.NUMBER"
        },
        {
          "name": "Action",
          "type": "LIST_OF_ACTIONS"
        }
      ]
    },
...
  ]
}
```

Next, we add our new type, LIST_OF_ACTIONS, and give it the possible values of “on” and “off”.  Finally, we define sample utterances and map them to intents.

```
DeviceSetIntent to set device {Device} to {Action}
DeviceSetIntent to turn {Action} device {Device}
DeviceSetIntent set device {Device} to {Action}
DeviceSetIntent to turn device {Device} {Action}
DeviceSetIntent turn device {Device} {Action}
```

As you interact with the skill you will likely need to add more sample utterances to make the interaction as natural as possible. For a complete list of intents/utterances see the `ask/` directory.

### Setting up the Client
Next, we will upload the code for our Lambda function that will serve as the client.  Note that while this code is fairly similar to the blueprint example, we have to do a little more work to package it to send to Lambda.  The reason is that we rely on some external files (certificates, configuration file, etc).  These must be packaged in a single zip file along with our code before being uploaded.

Setup the client as follows:

1. Modify the `upload.sh` script with the files to include in the package.
2. Create the client certificate (see `security/README`).
3. Make sure you have the AWS CLI tools installed (see `lambda/README`).
3. Create and upload the bundle (run `upload.sh`).

### Testing the Skill
With the interaction model defined and our client code uploaded, the last thing we need to do is enable testing and enter a description for our skill (if desired).  Testing can be used to hear spoken responses from Alexa’s text-to-speech engine and also to see responses to utterances from the Lambda function we created.  Don’t worry about any of the fields that say “Required for Certification”.  These only become relevant if we ever want to publish our skill for anyone to use.
Now we can make sure that the new skill works from Echo.  From the Alexa app click “Skills” and use the search bar to find “MyTestSkill”.  You should see the information you typed in the description fields in the app.  You need to make sure you’re logged in with the same account as your development account since this skill isn’t published for the world to see.  Try saying various utterances and make sure the responses are working.  You should also check the AWS Lambda console (“Monitoring” tab) which lets you know how often your function was invoked.  For more debugging, Lambda functions also print information to logs.  This feature is called CloudWatch and is a helpful tool for debugging Lambda functions.

## Hearing Alexa at Home
Up to this point, we have a mechanism for Alexa to understand what we say (through our new skill) and execute some code on our behalf (through Lambda) but we still need to bridge the gap between code that executes on Lambda and devices that live in our home.  This section introduces a mechanism that lets our Lambda function talk to a computer in our house.  That computer can then relay commands to Vera or do anything else we might want to do.

The computer we use is a small embedded one called a Raspberry Pi.  This Pi runs a Broadcom System-on-Chip (SoC) that provides an ARM CPU core and various additional functions (networking, graphics, etc.)  The Pi is very low cost ($35) and functional enough for most tasks.  Configuring a Pi is outside the scope of this guide, but several tutorials exist online.  For our purposes all that is needed is the current Raspbian distribution (Jessie) and to configure the Pi to connect to the internet (usually via Wi-Fi).  Additionally, it can be helpful to hook the Pi up to a display (via HDMI) and have a keyboard and mouse (either USB or Bluetooth).  As a last resort, it can be helpful to have a serial cable to configure the Pi through the console.

With the Raspberry Pi configured with internet access we will now walk through setting up a server on the Pi that will accept connections (TCP socket) from our Lambda function and then turn that into a UPnP command to relay to Vera over the HTTP interface.

### Security Considerations
At this point, it is important to pause and consider the security implications of what we’re doing.  Opening up communications between computers exposes us to the risk that someone with malicious intent can connect to our devices and cause harm (i.e. steal data, spy on us, etc.).  To mitigate this risk, we secure our connection as shown in Figure 3.  The client (Lambda function) is represented by the character Alice while the server (Raspberry Pi) is represented by Bob.  The attacker, who we assume is able to monitor our communications, is Eve.  Mallory (not pictured) is a slightly more nefarious attacker who we assume can insert herself in the middle of our conversation and alter, inject, or replay messages.  Finally, Trent is a trusted 3rd party who can vet Alice’s and Bob’s identities.  Our goal is to send a message from Alice to Bob and ideally preserve privacy, authenticity, and integrity.

![security](https://cloud.githubusercontent.com/assets/16480218/12194171/b8a0a31e-b5a2-11e5-9552-16347cc56689.png)
###### Figure 3 - Security Configuration

Ideally, we'd like the server to know the client is who he says he is and vice versa.  We can address these problems using a protocol called SSL/TLS.  SSL/TLS specifies a mechanism to exchange a secret key, allows parties to authenticate each other using certificates, and specifies a message integrity check to ensure the message wasn't tampered with in transit.  The secret key exchange is based on the principles of public-key cryptography, while certificates provide proof of an entity's ownership of a public key.  Certificates rely on a trusted 3rd party vetting the owner of a key.  How this vetting works in the real world is pretty interesting.  Trusted 3rd parties are known as certificate authorities (CA) and are companies that, for a fee, sign digital certificates for other entities.  What makes CAs special is that their certificates (from which our root of trust originates) are embedded in software that everyone uses (e.g. Web browsers).  The system isn’t perfect though and sometimes CAs get compromised and we need to remove the now untrusted root-of-trust from our browsers.  Other times companies will install their own root certificates on equipment they sell.  Open your browser and take a look at the root certificates you have.  You will be amazed at how many 3rd parties you trust to keep you protected on the Internet!

While we may conceptually have a sound security scheme in place, there are implementation considerations as well.  We need to choose from the many available protocols and ciphers, but how?  The answer, unfortunately, is not entirely straightforward.  New attacks against protocols and ciphers are always being developed and what was considered secure in the past might not be today.  That being said, we can follow generally established best practices.  OpenSSL is a fairly universally used implementation of all the protocols we'll mention.  It is suggested to use a version greater than 1.0.1c+ mostly for newer protocol support.  Both the Raspberry Pi and Lambda (which runs on machines with an Amazon Linux image) come with version 1.0.1k.  Python comes with a built-in module (ssl) that gives us access to the OpenSSL functionality we'll need.

The source code has more details of the implementation, but in a nutshell we use TLSv1.2 with 256 bit keys and require certificate verification on both ends of the connection.  The README in the `security/` directory describes the process for creating our own CA and keys/certificates for our devices.

### A Few Other Considerations
Another point worth mentioning is how the Lambda function running in the cloud finds our Raspberry Pi to talk to.  Since the Raspberry Pi is on the local network (see Figure 1), it only has a local IP address (192.168.0.100).  The only IP address visible to the Lambda function is the one that our ISP assigns to our router (54.240.196.170 in this example).  What we have to do is to setup port forwarding (also called Network Address Translation, or NAT) on our router so that traffic to our Internet IP is routed to the Raspberry Pi.  Configuring this is router dependent, but it is typically rule based (and sometimes integrated with firewall rules).  For the example illustrated in Figure 1 the rules might look like those in Table 1.  Note, rules are typically followed in order until one matches, which is why we have a “catch-all” rule last.  The first rule says to allow traffic on port 3000 from any Internet address and forward it to our Raspberry Pi.  The second rule denies all other incoming traffic.

Service | Action | LAN | WAN
:------:|:------:|:---:|:--:
TCP:3000 | Allow | 192.168.0.100 | Any
\*:\* | Deny | Any | Any

###### Table 1 – NAT Rules (for incoming requests)

Finally, note that in the config file for the Lambda function you can specify a hostname or IP address for the server.  Most people will just have an IP address assigned by their ISP.  The problem is that this is typically dynamic meaning it can change from time to time and break the Lambda function.  The way to solve this problem is with DNS, a service that translates hostnames (that stay consistent) to IP addresses.  There are many free and paid ways to do DNS, which is outside the scope of this guide.

### Setting up the Server
Basically, the server code takes care of listening for incoming connection requests (from our Lambda function) and processing the packets that come over those connections.  We use a very simple request/response protocol as our application level protocol.  There are many protocols we could use off the shelf (e.g. MQTT, HTTP, BOSH) but most of these are overly complicated for our simple example.  Our protocol simply consists of messages with a length and payload.  The length occupies the first four bytes of the packet and indicates payload length.  The payload is simply a JSON object that contains the action we want the Raspberry Pi to perform.  At a high level, the payload contains the data necessary to generate the UPnP request to the Vera controller.  The protocol is intentionally designed to be simple so that it is easily extensible.  After considering what you want to do, it may make more sense to switch to a different protocol.

We will setup the server as follows:

1. Copy the Python code in `server/` to the Raspberry Pi (or whatever machine will run the server).
2. Run `install_daemon.sh` to make the server persist (Linux/Mac only).
3. Setup CA and server certificate (see `security/README`).
4. Make modifications to `server.cfg`.
5. Check the server using the provided test utility (`test_client.py`).
6. Setup NAT on your router.

After following the above steps we should have a server running on our Raspberry Pi that accepts incoming connections and parses our simple messaging protocol to send UPnP commands to our Vera over HTTP.  

At this point, we should be able to do almost a full end-to-end test of our system.  Try giving echo some commands and following the path of execution (ASK->Lambda->Raspberry Pi->Vera).  If the command fails, use the various debug tools mentioned in the preceding sections to pinpoint where the failure is happening.  Have patience.  This is a fairly complicated system with a lot going on.  We have not discussed how to actually format commands to send to Vera over the HTTP interface, which we will do in the next section.

## Talking to Vera
Vera exposes a fairy convenient interface to remotely control existing devices and scenes over HTTP.  In Vera parlance, our Raspberry Pi (specifically the Python server on our Pi) acts as a Vera “controller”.  The interface is documented in various pages provided under the Background:UPnP section.  We use the Python ‘requests’ module to issue our HTTP requests.  The source code contains additional comments on some of the functionality available.  A brief description of some of the commands is presented here.  Note that it is very easy to test this interface outside of the Raspberry Pi using any browser or the Linux (Mac) curl utility.

To access the Vera interface we need to know our Vera’s IP address.  The port that exposes the interface is 3480.  The first thing to check is that Vera is up and running.  For this, we use the ‘lu_alive’ request (assuming Vera’s IP is 192.168.0.50):

```
curl http://192.168.0.50:3480/data_request?id=lu_alive
```

If everything is working, we should see the response ‘OK’.  To poll status, we use the ‘status’ request:

```
curl http://192.168.0.50:3480/data_request?id=status
```

This returns information on the current state of all devices and can be quite long.  The returned data format is JSON (JavaScript Object Notation) which is just a human-readable data format used in a lot of web applications.  Python has libraries that make it easy to work with JSON formatted data.  It can be useful to get a shortened version of the status output by using the DataVersion attribute.  This gets a delta between the current state and the state at the time indicated by DataVersion.

```
curl http://192.168.0.50:3480/data_request?id=status&DataVersion=123456789
```

UPnP devices consist of a device type and service (a collection of actions you can perform on the device).  A device is defined by an XML file and can be viewed through the Vera UI.  To do something to a device we use the ‘lu_action’ request and provide the device and service we want to change.  For example, a device type might be “urn:schemas-upnp-org:device:BinaryLight:1” which has a service “urn:upnp-org:serviceId:SwitchPower1” which has an action “SetTarget”.  Actions can have arguments associated with them as well, for example, newTargetValue to set the new state of the light.  The device might also have variables associated with the service, for example, “Status” which uses “0” or “1” to indicate the state of the light.

Turning this light on can be done with the following request:

```
curl http://192.168.0.50:3480/data_request?id=lu_action&DeviceType=urn:schemas-upnp-org:device:BinaryLight:1&serviceId=urn:upnp-org:serviceId:SwitchPower1&action=SetTarget&newTargetValue=1
```

Devices can also be referred to by number (DeviceNum), which is a much shorter version than the DeviceType string.  The ‘lu_action’ is the primary way our server interfaces with Vera.  As you add functionality, you’ll need to customize the server to translate between messages we receive from Lambda and UPnP commands.  This example currently supports getting/setting simple on/off devices and running scenes.

## Related Work
This project took inspiration from a few other people's work that you can check out if you're interested.

####[Alexa Lambda Linux (ALL)](https://github.com/goruck/all/)
This project uses a very similar architecture to connect Alexa to a home security system. A key difference is the use of a real-time Linux kernel to do the required button push emulation. There is also some hardware hacking involved to interface with the panel itself.

####[Philips Hue Emulator](https://github.com/armzilla/amazon-echo-ha-bridge)
For a while, Echo has supported controlling select smart devices through its interface. Among these are the Philips Hue lightbulbs. This clever project makes an arbitrary device look like a Hue lightbulb to the Echo. Eseentially, it accomplishes the same thing we do in this example. The one potential downside is that it isn't as flexible as our skills implementation.

####[EventWatcher](http://forum.micasaverde.com/index.php?topic=16984.0)
EventWatcher is a plugin written for Vera that exposes a lot more information over the HTTP interface we use in this project. You could extend this example to do a lot more using functionality present in EventWatcher.