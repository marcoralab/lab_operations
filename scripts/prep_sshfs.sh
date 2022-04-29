#!/usr/bin/env bash

# get groups and group IDs from Minerva
echo "Getting groups from Minerva; enter Minerva password and token if prompted"
groupinfo=$(ssh minerva 'id $USER' | \
  tr " " "\n" | \
  grep groups | \
  sed -e 's/(/\t/g' -e 's/)//g' -e 's/groups=//' | \
  tr "," "\n")"\n"

# print to terminal
echo Attempting to add the following groups:
cat <(printf "$groupinfo")

# add to computer if they don't already exist
echo "Adding Minerva groups; enter local password if prompted"
while read GID GROUP; do
  if dscl . list /Groups | grep -q '^name: '"$GROUP"'$'; then
    echo "warning: group \"$GROUP\" already exists; not adding!"
  elif dscl . list /Groups | grep -q '^gid: '"$GID"'$'; then
    echo "warning: GID \"$GID\" already exists; not adding!"
  else
    sudo dscl . -create /Groups/"$GROUP"
    sudo dscl . -create /Groups/"$GROUP" gid "$GID"
    sudo dscl . -create /Groups/"$GROUP" GroupMembership $USER
  fi
done < <(printf "$groupinfo")

mkdir -p $HOME/mounts/sc && mkdir -p $HOME/mounts/sc && chmod -R 777 $HOME/mounts

if [ ! -f /etc/synthetic.conf ] || ! grep -q "sc" /etc/synthetic.conf; then
  echo "Initializing Minerva directories; enter local password if prompted"
  sudo bash -c "echo sc\t$HOME/mounts/sc >> /etc/synthetic.conf"
  sudo bash -c "echo hpc\t$HOME/mounts/hpc >> /etc/synthetic.conf"
fi
sudo chmod 644 /etc/synthetic.conf

echo Adding SSHFS scripts if absent
mkdir -p $HOME/local/scripts

[[ -f $HOME/local/scripts/mc ]] || cat > $HOME/local/scripts/mc <<EOL
#!/usr/bin/env bash
cd

mount | grep -q /sc && diskutil unmount force /sc
mount | grep -q /hpc && diskutil unmount force /hpc
killall -9 sshfs

sshfs -o noappledouble -o volname=minerva_sc -o follow_symlinks minerva:/sc /sc/
sshfs -o noappledouble -o volname=minerva_hpc -o follow_symlinks minerva:/hpc /hpc/
cd -
EOL

[[ -f $HOME/local/scripts/mu ]] || cat > $HOME/local/scripts/mu <<EOL
#!/usr/bin/env bash
mount | grep -q /sc && diskutil unmount force /sc
mount | grep -q /hpc && diskutil unmount force /hpc
killall -9 sshfs
EOL

chmod +x $HOME/local/scripts/mc
chmod +x $HOME/local/scripts/mu

if ! which mc > /dev/null; then
  echo 'export PATH=$HOME/local/scripts:$PATH' >> $HOME/.zshrc
fi

echo Done. Please make sure SSHFS is installed and then restart

