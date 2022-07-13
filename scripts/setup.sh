#!/usr/bin/env bash

set -euo pipefail # STRICT MODE
pyversion="3.10"

shelltype=$(basename $SHELL)
if [[ "$shelltype" == "fish" ]]; then
  SHELLCONF=$HOME/.config/fish/config.fish
  shelltype=
elif [[ "$shelltype" == "bash" ]]; then
  SHELLCONF=$HOME/.bash_profile
elif [[ "$shelltype" == "zsh" ]]; then
  SHELLCONF=$HOME/.zshrc
else
  SHELLCONF="other"
fi

if echo $HOME | grep -q "^/hpc/users/"; then
  curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/.condarc > $HOME/.condarc
  echo -e "\n\nconda config --set auto_activate_base false\n" >> $HOME/.condarc
  mkdir -p /sc/arion/work/$USER/conda/envs
  mkdir -p /sc/arion/work/$USER/conda/pkgs
  
  newconda=0
  if ! conda --help &> /dev/null; then
    export newconda=1
    conda_prefix="/sc/arion/work/$USER/conda/miniconda3"
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -bp $conda_prefix
    rm Miniconda3-latest-Linux-x86_64.sh
    $conda_prefix/bin/conda init $shelltype
    if [[ $SHELLCONF == "other" ]]; then
      echo "Unknown shell. Please rerun this script to continue."
      exit 1
    fi
    source $SHELLCONF
  else
    conda deactivate
  fi

  if ! mamba --help &> /dev/null; then
    conda install -y mamba
  elif [[ $newconda -eq 0 ]]; then
    mamba update mamba
  fi
  
  mamba init

  if conda env list | grep -qE "^py$pyversion\s+"; then
    mamba create -y -n py$pyversion python=$pyversion snakemake ipython ipdb \
      jupyterlab biopython visidata miller flippyr mamba gh git code-server \
      vim radian pygit2 powerline-status \
      r-base=4.1 r-essentials r-languageserver
  fi
  
  printf "\n\n conda activate py$pyversion\n" >> $SHELLCONF
  mamba activate py$pyversion
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
    wget https://repo.anaconda.com/miniconda/$conda_inst
    bash $conda_inst -b
    rm $conda_inst
    $HOME/miniconda3/bin/conda init $shelltype
    if ! [[ $SHELLCONF == "other" ]]; then
      echo "Unknown shell. Please rerun this script to continue."
      exit 1
    fi
    source $SHELLCONF
    conda install -y mamba
    mamba install -y python=$pyversion $lcl_pkgs
  fi

  if [[ $newconda -eq 0 ]]; then
    if ! mamba --help &> /dev/null; then
      conda install -y mamba
    fi
    mamba install -y $lcl_pkgs
    mamba update -y mamba conda
    mamba update -y $lcl_pkgs
  fi

  mamba activate
fi

export SETUP_SCRIPT=1
wget https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/setup.py
python3 setup.py
rm setup.py

echo "Run \"source $SHELLCONF\" to activate changes."