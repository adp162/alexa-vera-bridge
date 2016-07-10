#!/bin/sh

# Install the server as a daemon that runs persistently
# This uses launchd for Mac and upstart for Linux

# Detect whether we're using Mac or Linux
OS=`uname`

# Check for upstart and that script is running as root

# Create the upstart conf file
echo "description \"Alexa-Vera-Bridge Python Server\""
echo "author \"Andrew Price\""
echo
echo "start on (local-filesystems and net-device-up)"
echo "stop on runlevel [06]"
echo
echo "respawn"
echo "exec /home/chadlung/myservice/myservice.py"

# Copy conf file to /etc/init/ and server files to /usr/bin?
