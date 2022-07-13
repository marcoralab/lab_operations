#!/usr/bin/env bash

set -euo pipefail # STRICT MODE

shelltype=$(basename $SHELL)
if echo $SHELL | grep -q "fish"; then
  SHELLCONF=$HOME/.config/fish/config.fish
  shelltype=
elif echo $SHELL | grep -q "bash"; then
  SHELLCONF=$HOME/.bash_profile
elif echo $SHELL | grep -q "zsh"; then
  SHELLCONF=$HOME/.zshrc
else
  SHELLCONF="other"
fi

if echo $HOME | grep -q "^/hpc/users/"; then
  if [ -z ${CONDA_PREFIX+x} ]
  curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/.condarc > $HOME/.condarc
  echo -e "\n\nconda config --set auto_activate_base false\n" >> $HOME/.condarc
  mkdir -p /sc/arion/work/$USER/conda/envs
  mkdir -p /sc/arion/work/$USER/conda/pkgs
  conda_prefix="/sc/arion/work/$USER/conda/miniconda3"
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash Miniconda3-latest-Linux-x86_64.sh -bp $conda_prefix
  rm Miniconda3-latest-Linux-x86_64.sh
  $conda_prefix/bin/conda init $shelltype
  if [[ $SHELLCONF == "other" ]]; then
    echo "Unknown shell. Please follow guide to setup anaconda"
    exit 1
  fi
  source $SHELLCONF
  conda install -y mamba
  mamba init
  mamba create -y -n py3.10 python=3.10 snakemake ipython ipdb jupyterlab \
    biopython visidata miller flippyr mamba gh git code-server vim radian \
    pygit2 powerline-status r-base=4.1 r-essentials r-languageserver

  printf "\n\n conda activate py3.10\n" >> $SHELLCONF
else
  lcl_pkgs="snakemake ipython ipdb jupyterlab biopython \
    visidata miller flippyr pygit2 powerline-status"
  newconda=0
  if ! conda --help &> /dev/null; then
    newconda=1
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
    if [[ $SHELLCONF == "other" ]]; then
      echo "Unknown shell. Please follow guide to setup anaconda"
      exit 1
    fi
    source $SHELLCONF
  fi
  conda install -y mamba
  
  if [[ $newconda -eq 0]]; then
    mamba install -y $lcl_pkgs
    mamba update -y mamba conda
    mamba update -y $lcl_pkgs
  else
    mamba install -y python=3.10 $lcl_pkgs
  fi
fi

export SETUP_SCRIPT=1
wget https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/setup.py
python3 setup.py
rm setup.py

echo "Run \"source $SHELLCONF\" to activate changes."