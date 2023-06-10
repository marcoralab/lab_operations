import os
import re
import sys
import importlib
import shutil
import subprocess
import pygit2
import pathlib
from tqdm import tqdm

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
        cmd_rsakey = ('ssh-keygen -t rsa -b 4096 '
                      f'-f {f_rsa} -P ""')
        r = subprocess.Popen(cmd_rsakey, shell=True)
        r.communicate()
        assert r.returncode == 0, 'Error generating RSA key'
    else:
        print('Keys already exist. Skipping RSA ssh-keygen')

    if not os.path.isfile(f_elyptic):
        cmd_elyptickey = ('ssh-keygen -t ed25519 -a 100 '
                          f'-f {f_elyptic} -P ""')
        r = subprocess.Popen(cmd_elyptickey, shell=True)
        r.communicate()
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
    if os.path.islink(dst):
        return os.readlink(dst)
    else:
        return dst

def compare_paths(x, y):
    def forcomp(path):
        nice = nicepath(path)
        unlinked = os.path.realpath(nice)
        return os.path.abspath(unlinked)
    return forcomp(x) == forcomp(y)

class GitRemoteCallbacks(pygit2.RemoteCallbacks):
    """
    Custom Git remote callbacks class for progress tracking during repository operations.

    Args:
        message (str, optional): The message to display before the progress bar. Default is None.
        op (str, optional): The operation description to display in the progress bar. Default is None.

    Attributes:
        pbar (tqdm.tqdm): The progress bar object.

    """

    def __init__(self, message=None, op=None):
        super().__init__()
        if message:
            print(message)
        args = {'colour': '#00ff00', 'smoothing': 0.1, 'postfix': 'objects'}
        if op:
            args['desc'] = op
        self.pbar = tqdm(**args)

    def transfer_progress(self, stats):
        """
        Progress tracking callback for Git transfer operations.

        Args:
            stats (pygit2.TransferProgress): The transfer progress statistics.

        Returns:
            None

        """
        self.pbar.total = stats.total_objects
        self.pbar.n = stats.indexed_objects
        self.pbar.refresh()

def pull(repo, remote_name='origin', branch='main', repo_name='Repo', remote_url=None):
    """
    Pulls updates from a remote Git repository.
    Adapted from https://github.com/MichaelBoselowitz/pygit2-examples/blob/master/examples.py

    Args:
        repo (pygit2.Repository): The Git repository object.
        remote_name (str): The name of the remote. Default is 'origin'.
        branch (str): The branch to pull. Default is 'main'.
        repo_name (str): The name of the repository for printing purposes. Default is 'Repo'.
        remote_url (str): The new URL for the remote. If provided, it will be updated.

    Returns:
        None
    """
    remote = repo.remotes[remote_name]
    old_url = remote.url
    try:
        try:
            remote.fetch()
        except:
            if remote_url:
                remote.url = remote_url
                remote.save()
                remote.fetch()
            else:
                raise
        remote_master_id = repo.lookup_reference(f'refs/remotes/{remote_name}/{branch}').target
        merge_result, _ = repo.merge_analysis(remote_master_id)
        if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
            print(f'{repo_name} is up to date')
            return
        elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
            repo.checkout_tree(repo.get(remote_master_id))
            try:
                master_ref = repo.lookup_reference(f'refs/heads/{branch}')
                master_ref.set_target(remote_master_id)
            except KeyError:
                repo.create_branch(branch, repo.get(remote_master_id))
            repo.head.set_target(remote_master_id)
            print(f'{repo_name} has been updated')
        elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
            repo.merge(remote_master_id)
            if repo.index.conflicts is not None:
                for conflict in repo.index.conflicts:
                    print(f'Conflicts found in: {conflict[0].path}')
                print('Conflicts found. Not updating.')
                return
            user = repo.default_signature
            tree = repo.index.write_tree()
            commit = repo.create_commit('HEAD', user, user, 'Merge!', tree,
                                        [repo.head.target, remote_master_id])
            # Clean up the repository state to avoid the Git CLI thinking we are still merging.
            repo.state_cleanup()
            print(f'{repo_name} has been merged and updated')
        else:
            raise AssertionError('Unknown merge analysis result')
    except:
        remote.url = old_url
        raise

def update_repository(repo_name, url, path, branch='main'):
    """
    Clones or updates a Git repository.

    Args:
        repo_name (str): The name of the repository for printing purposes.
        url (str): The URL of the Git repository.
        path (str): The local path where the repository should be cloned or updated.
        branch (str): The branch to pull. Default is 'main'.

    Returns:
        None
    """
    if not os.path.isdir(path):
        callback = GitRemoteCallbacks(f'Cloning {repo_name}...', 'Cloning')
        repo = pygit2.clone_repository(url, path, callbacks=callback)
    else:
        print(f'Updating {repo_name}...')
        repo = pygit2.Repository(path)
        pull(repo, branch=branch, repo_name=repo_name, remote_url=url)

os_type = get_os_type()

shell = os.path.basename(os.environ['SHELL'])

home = os.environ['HOME']
isminerva = bool(re.search("hpc", home))

assert 'SETUP_SCRIPT' in os.environ.keys(), 'Run setup.sh instead!'
assert os.environ['SETUP_SCRIPT'] == '1', 'Run setup.sh instead!'

for x in ['scripts', 'src', 'bin']: mkdir([home, 'local', x])

path_labops = nicepath([home, 'local', 'src', 'lab_operations'])

update_repository(
    repo_name='Scripts and config files',
    url='https://github.com/marcoralab/lab_operations.git',
    path=path_labops)

update_repository(
    repo_name='RStudio script',
    url='https://github.com/BEFH/rstudio-server-conda.git',
    path=nicepath([home, 'local', 'src', 'rstudio_server']),
    branch="master")

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
bindir = nicepath([home, 'local', 'bin'])
scriptdir_team = nicepath(['/sc/arion/projects/load', 'scripts'])

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
            f.write(f'\nfish_add_path -g "{bindir}"\n')
            if isminerva:
                f.write(f'\nfish_add_path -g "{scriptdir_team}"\n')
        else:
            f.write(f'\nexport PATH="{scriptdir}:$PATH"\n')
            f.write(f'\nexport PATH="{bindir}:$PATH"\n')
            if isminerva:
                f.write(f'\nexport PATH="{scriptdir_team}:$PATH"\n')

mkdir([home, '.ssh'], mode=0o700)

if not isminerva:
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

    f_rslink = link_if_absent(nicepath([path_rstudio, 'singularity', 'rstudio_minerva']),
                              destdir=[home, 'local', 'scripts'])

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

    print('setting up singularity cache')
    user = os.environ['USER']
    cachedir = ['/sc/arion/work', user, 'singularity', 'cache']
    sdir = [home, '.singularity']
    mkdir(cachedir)
    mkdir(sdir)
    cachedir_home = nicepath(sdir + ['cache'])
    if os.path.islink(cachedir_home):
        os.remove(cachedir_home)
    elif os.path.exists(cachedir_home):
        for root, dirs, files in os.walk(cachedir_home,
                                         topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
    os.symlink(nicepath(cachedir), cachedir_home)

    print('installing LSF profile for snakemake')
    # load in profile script as a module
    profscript = nicepath([home, 'local', 'src', 'lab_operations',
                           'scripts', 'setup_snakemake_profiles.py'])
    spec = importlib.util.spec_from_file_location('snakeprofile', profscript)
    sp = importlib.util.module_from_spec(spec)
    sys.modules['snakeprofile'] = sp
    spec.loader.exec_module(sp)
    import click
    #Add the profile
    confdir = os.path.expanduser('~/.config/snakemake')
    proj = click.prompt('Minerva Project:', default='acc_LOAD')

    profile_name='lsf'
    tf_overwrite = False
    lsfexists = False
    makelsf = True
    outpath = os.path.join(confdir, 'lsf')

    if os.path.isdir(outpath):
        print('lsf profile already exists.')
        lsfexists = True
        mkprompt = 'Continue without creating new LSF profile?'
        makelsf = not click.confirm(mkprompt, default=True)

    if makelsf and lsfexists:
        if click.confirm('Overwrite LSF profile?', default=True):
            tf_overwrite = True
        else:
            profile_name = click.prompt('Profile Name:')
    else:
        profile_name='choose_quiet'

    if makelsf:
        try:
            outpath = sp.install_lsf_profile(use_defaults=True,
                                             project=proj,
                                             overwrt=tf_overwrite,
                                             p_name=profile_name)
        except sp.OutputDirExistsException:
            print('lsf profile already exists.')
            if click.confirm('Overwrite LSF profile?', default=True):
                outpath = sp.install_lsf_profile(use_defaults=tf_default,
                                                 project=proj,
                                                 overwrt=True)
            else:
                profile_name = click.prompt('New profile name:')
                outpath = sp.install_lsf_profile(use_defaults=tf_default,
                                                 project=proj,
                                                 p_name=profile_name)
        else:
            print("LSF profile installed.")


    try:
        sp.install_local_profile(lsf_profile=outpath, profile_name="local")
    except sp.OutputDirExistsException:
        print('"local" lsf profile already exists.')
        mkprompt = 'Continue without creating new local profile?'
        makelocal = not click.confirm(mkprompt, default=True)
        if makelocal and click.confirm('Overwrite local LSF profile?',
                                       default=True):
            sp.install_local_profile(lsf_profile=outpath,
                                     profile_name="local",
                                     overwrt=True)
        elif makelocal:
            local_name = click.prompt('New local profile name:')
            sp.install_local_profile(profile_name=local_name)
    else:
        print("Local profile installed.")
