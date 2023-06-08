#!/usr/bin/env bash

set -euo pipefail # STRICT MODE
pyversion="3.10"
rversion="4.2"

shelltype=$(basename $SHELL)
echo "Using $shelltype"

if [[ "$shelltype" == "fish" ]]; then
  export SHELLCONF=$HOME/.config/fish/config.fish
elif [[ "$shelltype" == "bash" ]]; then
  export SHELLCONF=$HOME/.bash_profile
elif [[ "$shelltype" == "zsh" ]]; then
  export SHELLCONF=$HOME/.zshrc
else
  export SHELLCONF="other"
fi

minerva=0

if echo $HOME | grep -q "^/hpc/users/"; then
  minerva=1
  curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/.condarc > $HOME/.condarc
  echo -e "\nauto_activate_base: false\n" >> $HOME/.condarc
  mkdir -p /sc/arion/work/$USER/conda/envs
  mkdir -p /sc/arion/work/$USER/conda/pkgs
  
  newconda=0
  if ! conda --help &> /dev/null; then
    export newconda=1
    conda_prefix="/sc/arion/work/$USER/conda/miniconda3"
    conda_inst=Miniconda3-latest-Linux-x86_64.sh
    curl https://repo.anaconda.com/miniconda/$conda_inst > $conda_inst
    bash $conda_inst -bp $conda_prefix
    rm $conda_inst
    $conda_prefix/bin/conda init $shelltype
    if [[ $SHELLCONF == "other" ]]; then
      echo "Unknown shell. Please rerun this script to continue."
      exit 1
    elif [[ $shelltype == "bash" ]]; then
      __conda_setup=$("$conda_prefix/bin/conda" 'shell.bash' 'hook' 2> /dev/null)
      if [ $? -eq 0 ]; then
        eval "$__conda_setup"
      else
        if [ -f "$conda_prefix/etc/profile.d/conda.sh" ]; then
          . "$conda_prefix/etc/profile.d/conda.sh"
        else
          export PATH="$conda_prefix/bin:$PATH"
        fi
      fi
      unset __conda_setup
    else
      $conda_prefix/bin/conda init bash
      export PS1=''
      source $HOME/.bash_profile
    fi
  else
    conda deactivate
  fi

  if ! mamba --help &> /dev/null; then
    conda install -y mamba
    mamba clean --index-cache
    mamba update -y mamba conda
  elif [[ $newconda -eq 0 ]]; then
    mamba clean --index-cache
    mamba update -y mamba conda
  fi
  
  mamba init

  if conda env list | grep -qvE "^py$pyversion\s+"; then
    mamba create -y -n py$pyversion python=$pyversion snakemake ipython ipdb \
      jupyterlab biopython visidata miller flippyr gh git vim pygit2 \
      powerline-status click cookiecutter squashfs-tools radian \
      r-base=$rversion r-essentials r-languageserver
  fi
  
  if [[ "$shelltype" == "bash" ]]; then
    printf "\n\nconda activate py$pyversion\n" >> $HOME/.bashrc
  else
    printf "\n\nconda activate py$pyversion\n" >> $SHELLCONF  
  fi
  conda activate py$pyversion
else
  lcl_pkgs="snakemake ipython ipdb jupyterlab biopython \
    visidata miller flippyr pygit2 powerline-status"
  newconda=0
  if ! conda --help &> /dev/null; then
    export newconda=1
    curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/local.condarc > $HOME/.condarc
    if [ "$(uname)" == "Darwin" ]; then
      conda_inst="Miniconda3-latest-MacOSX-x86_64.sh"
    else
      conda_inst="Miniconda3-latest-Linux-x86_64.sh"
    fi
    curl https://repo.anaconda.com/miniconda/$conda_inst > $conda_inst
    bash $conda_inst -b
    rm $conda_inst
    $HOME/miniconda3/bin/conda init $shelltype
    if [[ $SHELLCONF == "other" ]]; then
      echo "Unknown shell. Please rerun this script to continue."
      exit 1
    elif [[ $SHELLCONF == "bash" ]]; then
      source $SHELLCONF
    else
      $HOME/miniconda3/bin/conda init bash
      source $HOME/.bash_profile
    fi
    
    conda install -y mamba
    mamba clean --index-cache
    mamba update -y mamba conda
    mamba install -y python=$pyversion $lcl_pkgs
  fi

  if [[ $newconda -eq 0 ]]; then
    if [ ! -f $HOME/.condarc ]; then
      curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/local.condarc > $HOME/.condarc
    fi
    if ! mamba --help &> /dev/null; then
      conda install -y mamba
    fi
    mamba clean --index-cache
    mamba update -y mamba conda
    mamba install -y $lcl_pkgs
    mamba update -y $lcl_pkgs
  fi

  mamba init
fi

export SETUP_SCRIPT=1
curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/setup.py > setup.py
python3 setup.py
rm setup.py

if [[ $minerva -eq 1 ]]; then
  curl -fsSL https://code-server.dev/install.sh | \
    bash -s -- --prefix ~/local --method standalone
  if ! grep -q singularity $SHELLCONF; then
    echo "Adding Singularity to $shelltype configuration ($SHELLCONF)"
    echo "ml singularity/3.10.3 2> /dev/null" >> $SHELLCONF
  fi
  if ! grep -q singularity ~/.bashrc; then
    echo "Adding Singularity to .bashrc"
    echo "ml singularity/3.10.3 2> /dev/null" >> ~/.bashrc
  fi
fi

echo "Run \"source $SHELLCONF\" to activate changes."
