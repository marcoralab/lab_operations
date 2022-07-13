#!/usr/bin/env bash

set -euo pipefail # STRICT MODE

if echo $SHELL | grep -q "fish"; then
  SHELLCONF=$HOME/.config/fish/config.fish
elif echo $SHELL | grep -q "bash"; then
  SHELLCONF=$HOME/.bashrc
elif echo $SHELL | grep -q "zsh"; then
  SHELLCONF=$HOME/.zshrc
else
  SHELLCONF="other"
fi

if echo $HOME | grep -q "^/hpc/users/"; then
  curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/.condarc > $HOME/.condarc
  echo -e "\n\nconda config --set auto_activate_base false\n" >> $HOME/.condarc
  mkdir -p /sc/arion/work/$USER/conda/envs
  mkdir -p /sc/arion/work/$USER/conda/pkgs
  conda_prefix="/sc/arion/work/$USER/conda/miniconda3"
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash Miniconda3-latest-Linux-x86_64.sh -bp $conda_prefix
  rm Miniconda3-latest-Linux-x86_64.sh
  $conda_prefix/bin/conda init
  if [[ $SHELLCONF == "other" ]]; then
    echo "Unknown shell. Please follow guide to setup anaconda"
    exit 1
  fi
  source $SHELLCONF
  conda install mamba
  mamba init
  mamba create -y -n py3.10 python=3.10 snakemake ipython ipdb jupyterlab \
    biopython visidata miller flippyr mamba gh git code-server vim radian \
    pygit2 powerline-status r-base=4.1 r-essentials r-languageserver

  printf "\n\n conda activate py3.10\n" >> $SHELLCONF
else
  curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/local.condarc > $HOME/.condarc
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
  bash Miniconda3-latest-MacOSX-x86_64.sh -b
  rm Miniconda3-latest-MacOSX-x86_64.sh
  $HOME/miniconda3/bin/conda init
  if [[ $SHELLCONF == "other" ]]; then
    echo "Unknown shell. Please follow guide to setup anaconda"
    exit 1
  fi
  source $SHELLCONF
  conda install mamba
  mamba install snakemake ipython ipdb jupyterlab biopython visidata \
    miller flippyr pygit2 powerline-status
fi

SETUP_SCRIPT=1
wget https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/setup.py
python3 setup_local.py
rm setup.py

echo "Run \"source $SHELLCONF\" to activate changes."