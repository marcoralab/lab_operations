#!/usr/bin/env python3

import os
import socket
import subprocess
import pathlib
import sys
# import pandas as pd
import csv
import shutil
import urllib.request

def octal_to_string(octal):
    octal = int(f'{octal:o}')
    result = ''
    value_letters = [(4,'r'),(2,'w'),(1,'x')]
    # Iterate over each of the digits in octal
    for digit in [int(n) for n in str(octal)]:
        # Check for each of the permissions values
        for value, letter in value_letters:
            if digit >= value:
                result += letter
                digit -= value
            else:
                result += '-'
    return result

def nicepath(path, *args):
    if type(path) in [str, pathlib.PosixPath]:
        path = [path]
    if args:
        path += args
    return os.path.join(*[os.path.normpath(x) for x in path])

def mkdir(path, *args, **kwargs):
    if type(path) in [str, pathlib.PosixPath]:
        path = [path]
    if args:
        path += args
    path = nicepath(path)
    mkdirkwargs = {k: v for k, v in kwargs.items() if k != 'fixperms'}
    valid_modes = [0o500, 0o510, 0o511, 0o550, 0o551, 0o555,
                   0o700, 0o710, 0o711, 0o750, 0o751, 0o755,
                   0o770, 0o771, 0o775, 0o777]

    setmode = False
    if 'mode' in kwargs.keys():
        err = 'Bad mode for folder: {}'.format(octal_to_string(kwargs['mode']))
        assert kwargs['mode'] in valid_modes, err
        setmode = True

    if not os.path.exists(path):
        os.makedirs(path, **mkdirkwargs)
    elif 'fixperms' in kwargs.keys() and kwargs['fixperms'] is True:
        assert setmode is True, 'Mode not specified'
        os.chmod(path, kwargs['mode'])

def make_key(home):
    f_elyptic = nicepath(home, '.ssh/id_ed25519')
    if not os.path.isfile(f_elyptic):
        print("Elyptic key does not yet exist. Creating it now.")
        cmd_elyptickey = ('ssh-keygen -t ed25519 -a 100 '
                          f'-f {f_elyptic} -P ""')
        r = subprocess.Popen(cmd_elyptickey, shell=True)
        r.communicate()
        assert r.returncode == 0, 'Error generating elyptic key'
    else:
        print('Elyptic key already exists. Skipping ssh-keygen')

## Read command line options and perform initial setup

if len(sys.argv) == 4:
    sname = sys.argv[1]
    usr = sys.argv[2]
    hname = sys.argv[3]
else:
    raise ValueError("Must provide server_name, server_user, and server_address")

hdir = os.path.expanduser("~")

file_conf = nicepath(hdir, ".screenshare.hosts")
confcols = ["sname", "port", "usr", "hname"]
conf = []
nrow_conf = 0
found = False

if os.path.exists(file_conf):
    with open(file_conf, newline='') as f:
        reader = csv.reader(f, delimiter=' ')
        for row in reader:
            conf.append(dict(zip(confcols, row)))
    nrow_conf = len(conf)

    for entry in conf:
        if entry["sname"] == sname:
            found = True
            response = input(f"{sname} already in config. Overwrite (y/N) ")
            if response.lower() in ["y", "yes"]:
                entry["usr"] = usr
                entry["hname"] = hname
                port = int(entry["port"])
            elif response.lower() in ["n", "no", ""]:
                print("Keeping current config.")
                sys.exit(1)
            else:
                print("Response not recognized. Exiting.")
                sys.exit(1)
            break

    if not found:
        port = max(int(e["port"]) for e in conf) + 1
        conf.append({"sname": sname, "port": str(port), "usr": usr, "hname": hname})
else:
    port = 5901
    conf = [{"sname": sname, "port": str(port), "usr": usr, "hname": hname}]
    nrow_conf = 1

# Write back the updated config
with open(file_conf, "w", newline='') as f:
    writer = csv.writer(f, delimiter=' ')
    for entry in conf:
        writer.writerow([entry[col] for col in confcols])

## Set up ssh

sshdir = nicepath(hdir, ".ssh")
mkdir(sshdir, mode=0o700)
make_key(hdir)
cmd_copykey = f'ssh-copy-id {usr}@{hname}'
r = subprocess.Popen(cmd_copykey, shell=True)
r.communicate()
assert r.returncode == 0, 'Error copying elyptic key to remote server'

## Download screenshare app

app_url = "https://raw.githubusercontent.com/marcoralab/lab_operations/refs/heads/main/scripts/launch_screenshare.zip"
app_path = nicepath(hdir, "Applications")
download_path = nicepath(hdir, "Downloads", "launch_screenshare.zip")
urllib.request.urlretrieve(app_url, download_path)
cmd_unzip = f'unzip -d {app_path} {download_path}'
r = subprocess.Popen(cmd_copykey, shell=True)
r.communicate()
assert r.returncode == 0, 'Error extracting app'

## Set up function in zshrc

zsh_func_name = "sshvnc"
zsh_func = f'''
# BEGIN {zsh_func_name}
function {zsh_func_name}() {{
  local config_file="$HOME/.screenshare.hosts"
  if [[ ! -f "$config_file" ]]; then
    echo "Config file not found: $config_file" >&2
    return 1
  fi

  if (( $# == 0 )); then
    if (( $(wc -l < "$config_file") == 1 )); then
      line=$(<"$config_file")
    else
      echo "Expected exactly one entry in config when no argument is given." >&2
      return 1
    fi
  elif (( $# == 1 )); then
    line=$(awk -v key="$1" '$1 == key {{ print; exit }}' "$config_file")
    if [[ -z "$line" ]]; then
      echo "No entry found for: $1" >&2
      return 1
    fi
  else
    echo "Too many arguments." >&2
    return 1
  fi
  read -r sname port usr hname <<< "$line"
  ssh -L ${{port}}:localhost:5900 "${{usr}}@${{hname}}" -fNT
  open vnc://localhost:${{port}}
}}
# END {zsh_func_name}
'''

zshrc_path = os.path.expanduser("~/.zshrc")

# Read existing zshrc
if os.path.exists(zshrc_path):
    backup_path = zshrc_path + ".bak"
    shutil.copy2(zshrc_path, backup_path)
    with open(zshrc_path, "r") as f:
        zshrc_lines = f.read()
else:
    zshrc_lines = ""

# Replace existing block if present, else append
if f"# BEGIN {zsh_func_name}" in zshrc_lines and f"# END {zsh_func_name}" in zshrc_lines:
    import re
    zshrc_lines = re.sub(
        rf"# BEGIN {zsh_func_name}.*?# END {zsh_func_name}",
        zsh_func, zshrc_lines, flags=re.DOTALL)
    print(f"Updated existing '{zsh_func_name}' function in ~/.zshrc.")
else:
    zshrc_lines += f"\n\n{zsh_func}\n"
    print(f"Added new '{zsh_func_name}' function to ~/.zshrc.")

# Write back the updated zshrc
with open(zshrc_path, "w") as f:
    f.write(zshrc_lines)

print("To use the updated function, run: source ~/.zshrc")
if nrow_conf == 1:
    print(f"You can then connect by running {zsh_func_name} [{sname}]")
else:
    print(f"You can then connect by running {zsh_func_name} {sname}")
print("Or you can run the 'Launch Screenshare' app.")
