import os
import subprocess
import pygit2
import pathlib

# From pythoncircle.com
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

def nicepath(path):
    if type(path) in [str, pathlib.PosixPath]:
        path = [path]
    return os.path.join(*[os.path.normpath(x) for x in path])

def mkdir(path, **kwargs):
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

def get_os_type():
    name = os.uname().sysname
    assert name in ['Darwin', 'Linux'], 'OS not supported'
    name = name if name != 'Darwin' else 'MacOS'
    return name

def make_keys(home, overwrite=False):
    f_elyptic = nicepath([home, '.ssh/id_ed25519'])
    f_rsa = nicepath([home, '.ssh/id_rsa'])

    if ((overwrite or not os.path.isfile(f_rsa))
            and not os.path.isfile(f_elyptic)):
        if os.path.isfile(f_rsa):
            os.remove(f_rsa)
        cmd_rsakey = ['ssh-keygen', '-t', 'rsa', '-b', '4096',
                      '-f', f_rsa, '-N', '""']
        r = subprocess.run(cmd_rsakey)
        assert r.returncode == 0, 'Error generating RSA key'
    else:
        print('Keys already exist. Skipping RSA ssh-keygen')
    
    if not os.path.isfile(f_elyptic):
        cmd_elyptickey = ['ssh-keygen', '-t', 'ed25519', '-a', '100',
                          '-f', f_elyptic, '-N', '""']
        r = subprocess.run(cmd_elyptickey)
        assert r.returncode == 0, 'Error generating elyptic key'
    else:
        print('Keys already exist. Skipping elyptic ssh-keygen')

def link_if_absent(src, dst=None, destdir=None):
    src = nicepath(src)
    if destdir is not None:
        destdir = nicepath(destdir)
        if dst is None:
            dst = nicepath([destdir, os.path.basename(src)])
        else:
            dst = nicepath([destdir, dst])
    dst = nicepath(dst)
    dir = os.path.dirname(dst)
    assert os.path.exists(src), 'Source does not exist!'
    if not (os.path.exists(dst) or os.path.isdir(dst)):
        relpath = os.path.relpath(src, dir)
        os.symlink(relpath, dst)
    if os.path.islink('/Users/bfh/.tmux.conf'):
        return os.readlink(dst)
    else:
        return dst

def compare_paths(x, y):
    def forcomp(path):
        nice = nicepath(path)
        unlinked = os.path.realpath(nice)
        return os.path.abspath(unlinked)
    return forcomp(x) == forcomp(y)

os_type = get_os_type()

shell = os.path.basename(os.environ['SHELL'])

home = os.environ['HOME']

assert 'SETUP_SCRIPT' in os.environ.keys(), 'Run setup.sh instead!'
assert os.environ['SETUP_SCRIPT'] == '1', 'Run setup.sh instead!'

for x in ['scripts', 'src', 'bin']: mkdir([home, 'local', x])

class MyRemoteCallbacks(pygit2.RemoteCallbacks):
    def transfer_progress(self, stats):
        print(f'{stats.indexed_objects}/{stats.total_objects}')

path_labops = nicepath([home, 'local', 'src', 'lab_operations'])
if not os.path.isdir(path_labops):
    print('Cloning scripts and config files...')
    pygit2.clone_repository('http://github.com/marcoralab/lab_operations.git',
                            path_labops, callbacks=MyRemoteCallbacks())
else:
    print('Updating scripts and config files...')
    output = subprocess.check_output(['git', '-C', path_labops, 'pull'])

# Symlink config files

f_conf = [f for f in pathlib.Path(path_labops + "/config_files/").glob('*')
          if not f.name.endswith(".condarc")]

f_conflinks = [link_if_absent(src, destdir=home) for src in f_conf]

discrep_conf = {os.path.basename(x): y for x, y in zip(f_conf, f_conflinks)
                if not compare_paths(x, y)}

if len(discrep_conf) > 0:
    for f, realpath in discrep_conf.items():
        print(f'Warning: The config file {f} does not point to the lab repo.')
        if realpath == nicepath([home, f]):
            print('         It is a file in your home directory\n')
        else:
            print('         It points to the following file:')
            print(f'         {realpath}\n')

scriptdir = nicepath([home, 'local', 'scripts'])
if not scriptdir in os.environ['PATH'].split(':'):
    if shell == 'fish':
        shell_conf = nicepath([home, '.config', 'fish', 'config.fish'])
    elif shell == 'bash':
        shell_conf = nicepath([home, '.bashrc'])
    elif shell == 'zsh':
        shell_conf = nicepath([home, '.zshrc'])
    else:
        shell_conf = input("Enter absolute path to your shell config file:")
    
    with open(shell_conf, "a") as f:
        if shell == 'fish':
            f.write(f'\nfish_add_path -g "{scriptdir}"\n')
        else:
            f.write(f'\nexport PATH="{scriptdir}:$PATH"\n')

mkdir([home, '.ssh'], mode=0o700)

if os_type == 'MacOS':
    mkdir([home, '.ssh', 'cm_socket'], mode=0o700)
    configpath = nicepath([home, '.ssh', 'config'])
    minerva_username = input("Enter minerva username: ")
    ssh_config = '''Host minerva
  HostName minerva12.hpc.mssm.edu
  User {}
  ForwardX11Trusted yes
Host *
  ControlPath ~/.ssh/cm_socket/%r@%h:%p
  ControlMaster auto
  ControlPersist 1m
  Compression yes
  ServerAliveInterval 240
  ServerAliveCountMax 2
'''.format(minerva_username)
    if os.path.exists(configpath):
        print('Check that the following exists in your .ssh/config:')
        print('\n' + ssh_config + '\n\n')
    else:
        print('writing to ~/.ssh/config...')
        with open(configpath,"w") as f:
            f.writelines(ssh_config)
    os.chmod(configpath, 0o644)
    print('making ssh keys...')
    make_keys(home)

    f_scpt = [f for f in pathlib.Path(path_labops + "/scripts/").glob('*')
              if not f.name.startswith("setup")]

    f_scptlinks = [link_if_absent(src, destdir=[home, 'local', 'scripts'])
                   for src in f_scpt]
    
    discrep_srpt = {os.path.basename(x): y for x, y in zip(f_scpt, f_scptlinks)
                    if not compare_paths(x, y)}
    
    if len(discrep_srpt) > 0:
        for f, realpath in discrep_srpt.items():
            print(f'Warning: The script {f} does not point to the lab repo.')
            if realpath == nicepath([home, f]):
                print('         It is a file in your script directory\n')
            else:
                print('         It points to the following file:')
                print(f'         {realpath}\n')
else:
    print('making ssh keys...')
    make_keys(home, overwrite=True)    
    