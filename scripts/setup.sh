#!/usr/bin/env bash

set -euo pipefail # STRICT MODE
pyversion="3.10"
rversion="4.3"

export MAMBA_NO_BANNER=1
windows=0

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

source_bashrc() {
  set +u +e +o pipefail
  source $HOME/.bashrc
  set -euo pipefail
}

minerva=0

if echo $HOME | grep -q "^/hpc/users/"; then
  minerva=1
  echo Downloading .condarc to home direcctory
  curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/.condarc > $HOME/.condarc 2> /dev/null
  echo -e "\nauto_activate_base: false\n" >> $HOME/.condarc
  echo Ensuring conda and mamba are installed and updated
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
      source_bashrc
    fi
    echo Done installing Mambaforge
  elif [ -n "${CONDA_PREFIX+x}" ]; then
    source_bashrc
    set +u
    conda deactivate
    set -u
  else
    source_bashrc
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

  if ! conda env list | grep -qE "^py$pyversion\s+"; then
    echo Installing py$pyversion environment
    mamba create -y -n py$pyversion python=$pyversion snakemake=7.32.4 ipython ipdb \
      jupyterlab biopython visidata miller flippyr gh git vim pygit2 tmux \
      htop powerline-status click cookiecutter squashfs-tools radian \
      r-base=$rversion r-essentials r-languageserver tqdm r-httpgd
  fi

  if [[ "$shelltype" == "bash" ]]; then
    SHELLCONF_activate="$HOME/.bashrc"
  else
    SHELLCONF_activate="$SHELLCONF"
  fi
  if ! grep -q "conda activate py$pyversion" "$SHELLCONF_activate"; then
    printf "\n\nconda activate py$pyversion\n" >> $SHELLCONF_activate
  fi
  conda activate py$pyversion || source_bashrc
else
  lcl_pkgs="snakemake=7.32.4 ipython jupyterlab biopython \
    visidata flippyr pygit2 vim ipdb \
    tmux wget gh curl gawk sed grep nodejs tqdm"
  # add miller and powerline-status when arm64 supported
  newconda=0
  if ! conda --help &> /dev/null; then
    export newconda=1
    echo Downloading .condarc to home direcctory
    curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/config_files/local.condarc > $HOME/.condarc 2> /dev/null
    echo Ensuring conda and mamba are installed and updated
    conda_inst=Mambaforge-$(uname)-$(uname -m).sh
    curl -L "https://github.com/conda-forge/miniforge/releases/latest/download/$conda_inst" > $conda_inst
    bash $conda_inst -b
    rm $conda_inst
    $HOME/mambaforge/bin/conda init $shelltype
    $HOME/mambaforge/bin/mamba init $shelltype
    if [[ $shelltype == "other" ]]; then
      echo "Unknown shell. Please rerun this script to continue."
      exit 1
    elif [[ $shelltype == "bash" ]]; then
      if [ -z ${WSL_DISTRO_NAME+x} ]; then
        source $SHELLCONF
      else
        windows=1
        source "$HOME/mambaforge/etc/profile.d/conda.sh"
      fi
    else
      $HOME/mambaforge/bin/conda init bash
      $HOME/mambaforge/bin/mamba init bash
      source $HOME/.bash_profile
    fi
    mamba update -y mamba conda
    set +u
    mamba install -y python=$pyversion $lcl_pkgs
    set -u
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
    mamba install -y $lcl_pkgs -c conda-forge
    mamba update -y $lcl_pkgs -c conda-forge
  fi

  if [[ $newconda -ne 0 ]] || ! mamba activate &> /dev/null; then
    mamba init
    mamba init $shelltype
  fi
fi

echo Starting python install script
export SETUP_SCRIPT=1

curl https://raw.githubusercontent.com/marcoralab/lab_operations/main/scripts/setup.py > setup_lab.py
if [[ $windows -eq 1 ]]; then
  $(dirname $CONDA_EXE)/python3 setup_lab.py || \
    echo Main setup script failed. Please tell Brian.
else
  python3 setup_lab.py || echo Main setup script failed. Please tell Brian.
fi
rm setup_lab.py

if [[ $minerva -eq 1 ]]; then
  if ! grep -q singularity $SHELLCONF; then
    echo "Adding Singularity to $shelltype configuration ($SHELLCONF)"
    echo "ml singularity/3.6.4 2> /dev/null" >> $SHELLCONF
  fi
  if ! grep -q singularity ~/.bashrc; then
    echo "Adding Singularity to .bashrc"
    echo "ml singularity/3.6.4 2> /dev/null" >> ~/.bashrc
  fi
fi

if [[ $windows -eq 1 ]]; then
  echo "Run \"source .bashrc\" to activate changes."
else
  echo "Run \"source $SHELLCONF\" to activate changes."
fi
