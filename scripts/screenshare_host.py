#!/usr/bin/env python3

import plistlib
import os
import socket
import subprocess

# from https://gist.github.com/mhofman/171539fa11052aae785fd19d8b382664

orig_file = '/System/Library/LaunchDaemons/com.apple.screensharing.plist'
targ_file = '/Library/LaunchDaemons/com.apple.screensharing.plist'
launch_file = '/Library/LaunchDaemons/com.apple.screensharing.launcher.plist'

plist_launcher = {
    'Label': 'com.apple.screensharing.launcher',
    'LaunchOnlyOnce': True,
    'RunAtLoad': True,
    'KeepAlive': False,
    'ProgramArguments': [
        '/bin/launchctl', 'load', '-F', targ_file]}

with open(orig_file, 'rb') as plist_file:
    plist = plistlib.load(plist_file)

plist['Sockets']['Listener'] = {'SockNodeName': 'localhost',
                                'SockServiceName': 'vnc-server'}

ret = subprocess.run(['launchctl', 'unload', '-w', orig_file])
if ret.check_returncode():
    raise Exception("Could not unload plist!")

with open(targ_file, 'wb') as plist_file:
    plistlib.dump(plist, plist_file, sort_keys=False)

with open(launch_file, 'wb') as plist_file:
    plistlib.dump(plist_launcher, plist_file, sort_keys=False)

ret = subprocess.run(['launchctl', 'load', '-w', launch_file])

usr = os.getlogin()
hname = socket.getfqdn()
hname_short = hname.split(".")[0]

print('Please run the following command where you will be accessing this computer to complete setup:')
print(f'''python3 <(curl -s https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/screenshare_client) {hname_short} {usr} {hname}''')
print(f'\nYou can replace {hname_short} with a descriptive name for this computer')

