#!/usr/bin/env python3

import profile
from cookiecutter.main import cookiecutter
from cookiecutter.generate import OutputDirExistsException
import os
from copy import deepcopy
import yaml

def install_lsf_profile(use_defaults=False, project='acc_LOAD',
                        overwrt=False, p_name='choose'):
    confdir = os.path.expanduser('~/.config/snakemake')
    if use_defaults and p_name in ['choose', 'choose_quiet']:
        p_name = 'lsf'
    defaults = {'LSF_UNIT_FOR_LIMITS': 'MB', 'default_mem_mb': 4096,
                'default_queue': 'premium', 'default_project': project,
                'max-jobs-per-second': 5, 'max_status_checks_per_second': 5,
                'max_status_checks': 5, 'wait_between_tries': 0.5,
                'latency_wait': 10, 'use_conda': True, 'use_singularity': True,
                'print_shell_commands': True, 'jobs': 2000,
                'profile_name': p_name}
    
    pathcheck = lambda x: os.path.isdir(os.path.join(confdir, x))
    
    if not overwrt:
        if pathcheck('lsf') and p_name == 'choose':
            print('Warning: don\'t choose lsf as the profile name,'
                  'since it exists already.')
        elif pathcheck(p_name) and p_name != 'choose_quiet':
            raise OutputDirExistsException

    outpath = cookiecutter('gh:Snakemake-Profiles/lsf', extra_context=defaults,
                           output_dir=confdir, overwrite_if_exists=overwrt,
                           no_input=use_defaults)

    return outpath

def install_local_profile(lsf_profile={}, use_defaults='if_no_lsf',
                          settings={}, profile_name='local', overwrt=False):
    confdir = os.path.expanduser('~/.config/snakemake')

    defaults = {'latency-wait': '10',
                'use-conda': 'True',
                'use-singularity': 'True',
                'printshellcmds': 'True',
                'restart-times': '0',
                'jobs': '1'}

    use_defaults = ((use_defaults == 'if_no_lsf' and lsf_profile == '') or
                    use_defaults is True)
    
    assert settings is False or type(settings) is dict, \
           'settings must be a dictionary'
    use_settings = len(settings) > 0 and type(settings) is dict
    assert ((type(settings) is dict and len(settings) > 0)
            or use_settings is False), 'settings must be a dictionary'

    if use_defaults:
        conf = deepcopy(defaults)
    elif lsf_profile:
        lsf_profile_cnf = os.path.join(lsf_profile, 'config.yaml')
        assert os.path.isdir(lsf_profile) and os.path.isfile(lsf_profile_cnf), \
               'LSF profile does not exist!'
        with open(lsf_profile_cnf, 'r') as f:
             lsf_profile_dict = yaml.safe_load(f)
        conf_ = {k: v for k, v in lsf_profile_dict.items() if k in defaults}
        conf = deepcopy(defaults)
        conf.update(deepcopy(conf_))
        conf['jobs'] = '1'
    elif use_settings:
        conf = {}

    if use_settings:
        conf.update(settings)
    
    assert os.path.sep not in profile_name, 'profile name should not be a path'
    outdir = os.path.join(confdir, profile_name)
    if os.path.exists(outdir):
        if not overwrt:
            raise OutputDirExistsException
    else:
        os.mkdir(outdir)

    with open(os.path.join(outdir, 'config.yaml'), 'w') as f:
        yaml.dump(conf, f, default_flow_style=False)

def install_lsf8_profile(lsf_profile={}, use_defaults='if_no_lsf', project='acc_LOAD',
                         settings={}, profile_name='lsf8', overwrt=False):
    confdir = os.path.expanduser('~/.config/snakemake')

    defaults = {'max-jobs-per-second': 10, 'max-status-checks-per-second': 1,
                'wait-between-tries': 0.5, 'latency-wait': 10,
                'printshellcmds': True, 'jobs': 2000,
                'software-deployment-method': ['conda', 'singularity'],
                'executor': 'lsf',
                'default_queue': 'premium', 'default_project': project}

    use_defaults = ((use_defaults == 'if_no_lsf' and lsf_profile == '') or
                    use_defaults is True)
    
    assert settings is False or type(settings) is dict, \
           'settings must be a dictionary'
    use_settings = len(settings) > 0 and type(settings) is dict
    assert ((type(settings) is dict and len(settings) > 0)
            or use_settings is False), 'settings must be a dictionary'

    if use_defaults:
        conf = deepcopy(defaults)
    elif lsf_profile:
        lsf_profile_cnf = os.path.join(lsf_profile, 'config.yaml')
        assert os.path.isdir(lsf_profile) and os.path.isfile(lsf_profile_cnf), \
               'LSF profile does not exist!'
        with open(lsf_profile_cnf, 'r') as f:
             lsf_profile_dict = yaml.safe_load(f)
        conf_ = {k: v for k, v in lsf_profile_dict.items() if k in defaults}
        conf = deepcopy(defaults)
        conf.update(deepcopy(conf_))
    elif use_settings:
        conf = {}

    if use_settings:
        conf.update(settings)

    conf['default-resources'] = {}
    conf['default-resources']['lsf_queue'] = conf.pop('default_queue')
    conf['default-resources']['lsf_project'] = conf.pop('default_project')

    assert os.path.sep not in profile_name, 'profile name should not be a path'
    outdir = os.path.join(confdir, profile_name)
    if os.path.exists(outdir):
        if not overwrt:
            raise OutputDirExistsException
    else:
        os.mkdir(outdir)

    with open(os.path.join(outdir, 'config.yaml'), 'w') as f:
        yaml.dump(conf, f, default_flow_style=False)

def install_local8_profile(lsf_profile={}, use_defaults='if_no_lsf',
                           settings={}, profile_name='local8', overwrt=False):
    confdir = os.path.expanduser('~/.config/snakemake')

    defaults = {'latency-wait': 10, 'printshellcmds': True, 'jobs': 1,
                'software-deployment-method': ['conda', 'singularity']}

    use_defaults = ((use_defaults == 'if_no_lsf' and lsf_profile == '') or
                    use_defaults is True)
    
    assert settings is False or type(settings) is dict, \
           'settings must be a dictionary'
    use_settings = len(settings) > 0 and type(settings) is dict
    assert ((type(settings) is dict and len(settings) > 0)
            or use_settings is False), 'settings must be a dictionary'

    if use_defaults:
        conf = deepcopy(defaults)
    elif lsf_profile:
        lsf_profile_cnf = os.path.join(lsf_profile, 'config.yaml')
        assert os.path.isdir(lsf_profile) and os.path.isfile(lsf_profile_cnf), \
               'LSF profile does not exist!'
        with open(lsf_profile_cnf, 'r') as f:
             lsf_profile_dict = yaml.safe_load(f)
        conf_ = {k: v for k, v in lsf_profile_dict.items() if k in defaults}
        conf = deepcopy(defaults)
        conf.update(deepcopy(conf_))
        conf['jobs'] = '1'
    elif use_settings:
        conf = {}

    if use_settings:
        conf.update(settings)

    assert os.path.sep not in profile_name, 'profile name should not be a path'
    outdir = os.path.join(confdir, profile_name)
    if os.path.exists(outdir):
        if not overwrt:
            raise OutputDirExistsException
    else:
        os.mkdir(outdir)

    with open(os.path.join(outdir, 'config.yaml'), 'w') as f:
        yaml.dump(conf, f, default_flow_style=False)


if __name__ == '__main__':
    confdir = os.path.expanduser('~/.config/snakemake')
    print('Setting up LSF profile.')
    profile_name='choose'
    try:
        import click
        proj = click.prompt('Minerva Project:', default='acc_LOAD')
        tf_default = click.confirm('Use all defaults?',
                                   default=True)
        tf_overwrite = False
        if tf_default and os.path.isdir(os.path.join(confdir, 'lsf')):
            print('lsf profile already exists.')
            if click.confirm('Overwrite LSF profile?', default=True):
                tf_overwrite = True
            else:
                profile_name = click.prompt('Profile Name:')
        else:
            profile_name='choose_quiet'
        use_click = True
    except ModuleNotFoundError:
        print('Python package \'click\' is missing.')
        yn = input('Quit to install click for the best experience? [y/N]:')
        if yn[0].lower() == 'y':
            import sys
            sys.exit(1)
        yn = input('Use all defaults (acc_LOAD only) [Y/n]:')
        tf_default = yn[0].lower() == 'y' or not yn
        if tf_default:
            proj = 'acc_LOAD'
        tf_overwrite = False
        use_click = False
    
    try:
        outpath = install_lsf_profile(use_defaults=tf_default,
                                      project=proj, overwrt=tf_overwrite,
                                      p_name=profile_name)
    except OutputDirExistsException:
        print('lsf profile already exists.')
        if use_click:
            if click.confirm('Overwrite LSF profile?', default=True):
                outpath = install_lsf_profile(use_defaults=tf_default,
                                              project=proj, overwrt=True)
            else:
                profile_name = click.prompt('Profile Name:')
                outpath = install_lsf_profile(use_defaults=tf_default,
                                              project=proj, p_name=profile_name)
        else:
            raise

    if not use_click:
        print('Setting up local profile.')
        install_local_profile(lsf_profile=outpath)
        try:
            install_lsf8_profile(lsf_profile=outpath)
            install_local8_profile(lsf_profile=outpath)
        except:
            print("Failed to install Snakemake 8 profiles!")
        exit(0)

    if click.confirm('Create local profile?', default=True):
        try:
            local_name = click.prompt('Name of the local profile', default='local')
            prompt = 'Use settings from lsf profile? Will use defaults otherwise.'
            local_uselsf = click.confirm(prompt, default=True)
            if local_uselsf:
                install_local_profile(lsf_profile=outpath, profile_name=local_name)
            else:
                install_local_profile(profile_name=local_name)
        except OutputDirExistsException:
            print('local profile already exists.')
            overwrite_local = True
            if not click.confirm('Overwrite local profile?', default=True):
                local_name = click.prompt('Profile Name:')
                overwrite_local = False
            if local_uselsf:
                install_local_profile(lsf_profile=outpath, profile_name=local_name,
                                      overwrt=overwrite_local)
            else:
                install_local_profile(profile_name=local_name, overwrt=overwrite_local)
        except:
            print("Failed to install Snakemake 7 local profile!")

    if click.confirm('Create Snakemake 8 lsf profile?', default=True):
        lsf8_name = click.prompt('Name of the local profile', default='lsf8')
        prompt = 'Use settings from lsf profile? Will use defaults otherwise.'
        try:
            lsf8_uselsf = click.confirm(prompt, default=True)
            if lsf8_uselsf:
                install_lsf8_profile(lsf_profile=outpath,
                                     profile_name=lsf8_name)
            else:
                install_lsf8_profile(profile_name=lsf8_name)
        except OutputDirExistsException:
            print('LSF Snakemake 8 profile already exists.')
            overwrite_lsf8 = True
            if not click.confirm('Overwrite LSF Snakemake 8 profile?', default=True):
                lsf8_name = click.prompt('Profile Name:')
                overwrite_lsf8 = False
            if lsf8_uselsf:
                install_lsf8_profile(lsf_profile=outpath, profile_name=lsf8_name,
                                     overwrt=overwrite_lsf8)
            else:
                install_lsf8_profile(profile_name=lsf8_name, overwrt=overwrite_lsf8)
        except:
            print("Failed to install Snakemake 8 lsf profile!")

    if click.confirm('Create Snakemake 8 local profile?', default=True):
        local8_name = click.prompt('Name of the Snakemake 8 local profile', default='local8')
        prompt = 'Use settings from lsf profile? Will use defaults otherwise.'
        try:
            local8_uselsf = click.confirm(prompt, default=True)
            if local8_uselsf:
                install_local8_profile(lsf_profile=outpath,
                                       profile_name=local8_name)
            else:
                install_local8_profile(profile_name=local8_name)
        except OutputDirExistsException:
            print('Snakemake 8 local profile already exists.')
            overwrite_local8 = True
            if not click.confirm('Overwrite Snakemake 8 local profile?', default=True):
                local8_name = click.prompt('Profile Name:')
                overwrite_local8 = False
            if local8_uselsf:
                install_local8_profile(lsf_profile=outpath, profile_name=local8_name,
                                       overwrt=overwrite_local8)
            else:
                install_local8_profile(profile_name=local8_name, overwrt=overwrite_local8)
        except:
            print("Failed to install Snakemake 8 local profile!")
