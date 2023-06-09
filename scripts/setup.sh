#!/usr/bin/env bash

set -euo pipefail # STRICT MODE
pyversion="3.11"
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
    echo Installing conda and mamba using Mambaforge
    conda_prefix="/sc/arion/work/$USER/conda/mambaforge"
    conda_inst=Mambaforge-$(uname)-$(uname -m).sh
    curl -L "https://github.com/conda-forge/miniforge/releases/latest/download/$conda_inst" > $conda_inst
    bash $conda_inst -bp $conda_prefix
    rm $conda_inst
    echo Initializing conda
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
    echo Done installing Mambaforge
  else
    conda deactivate
  fi

  if ! mamba --help &> /dev/null; then
    echo Installing mamba
    conda install -y mamba
    mamba clean --index-cache -y
  elif [[ $newconda -eq 0 ]]; then
    mamba clean --index-cache -y
  fi
  echo Updating mamba and conda
  mamba update -y mamba conda
  
  if ! mamba activate &> /dev/null; then
    echo Initializing mamba
    mamba init
    mamba init $shelltype
  fi
  
  if conda env list | grep -qvE "^py$pyversion\s+"; then
    echo Installing py$pyversion environment
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
    conda_prefix="/sc/arion/work/$USER/conda/mambaforge"
    conda_inst=Mambaforge-$(uname)-$(uname -m).sh
    curl -L "https://github.com/conda-forge/miniforge/releases/latest/download/$conda_inst" > $conda_inst
    bash $conda_inst -b
    rm $conda_inst
    $HOME/mambaforge/bin/conda init $shelltype
    if [[ $SHELLCONF == "other" ]]; then
      echo "Unknown shell. Please rerun this script to continue."
      exit 1
    elif [[ $SHELLCONF == "bash" ]]; then
      source $SHELLCONF
    else
      $HOME/mambaforge/bin/conda init bash
      source $HOME/.bash_profile
    fi
    mamba update -y mamba conda
    mamba install -y python=$pyversion $lcl_pkgs
  fi

  if [[ $newconda -eq 0 ]]; then
    if [ ! -f $HOME/.condarc ]; then
      curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/local.condarc > $HOME/.condarc
    fi
    if ! mamba --help &> /dev/null; then
      conda install -y mamba
      mamba clean --index-cache -y
    fi
    mamba update -y mamba conda
    mamba install -y $lcl_pkgs
    mamba update -y $lcl_pkgs
  fi

  if ! mamba activate &> /dev/null; then
    mamba init
    mamba init $shelltype
  fi
fi

echo Starting python install script
export SETUP_SCRIPT=1
curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/setup.py > setup.py
python3 setup.py || echo Main setup script failed. Please tell Brian.
rm setup.py

if [[ $minerva -eq 1 ]]; then
  echo Installing/updating code server
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
