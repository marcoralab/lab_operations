#/usr/bin/env python

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
                                'SockServiceName': '5901'}

ret = subprocess.run(['launchctl', 'unload', '-w', orig_file])
if ret.check_returncode():
    raise Exception("Could not unload plist!")

with open(targ_file, 'wb') as plist_file:
    plistlib.dump(plist, plist_file, sort_keys=False)

with open(launch_file, 'wb') as plist_file:
    plistlib.dump(plist_launcher, plist_file, sort_keys=False)

ret = subprocess.run(['launchctl', 'load', '-w', launch_file])
locfwd = '-L 5901:localhost:5900'
vnccmd = 'open vnc://localhost:5901'
usr = os.getlogin()
hname = socket.getfqdn()
sshcmd = f'ssh {locfwd} {usr}@{hname} -fNT'
cmd_elyptickey = ('ssh-keygen -t ed25519 -a 100 '
                  f'-f ~/.ssh/id_ed25519 -P ""')

print('Please run the following commands where you will be accessing this computer:')
print('If you do not have a ed25519 key, run this:')
print(cmd_elyptickey)
print('\n\nThen run the following:')
print(f'ssh-copy-id {usr}@{hname}')
print('\nThis will allow you to connect in the future' +
      '\nwithout entering your password repeatedly.')
print('\n\nThen run the following command to install the connection alias:')
print(f'''echo -e 'alias labdesk="{sshcmd} && {vnccmd}"' >> ~/.zshrc''')
print('\nYou can just run "labdesk" to connect now.')

