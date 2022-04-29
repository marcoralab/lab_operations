# get groups and group IDs from Minerva
groupinfo=$(ssh minerva 'id $USER' | \
  tr " " "\n" | \
  grep groups | \
  sed -e 's/(/\t/g' -e 's/)//g' -e 's/groups=//' | \
  tr "," "\n")"\n"

# print to terminal
echo attempting to add the following groups:
cat <(printf "$groupinfo")

# add to computer if they don't already exist
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

if [ ! -f /etc/synthetic.conf ] && grep -q "sc" /etc/synthetic.conf; then
  sudo echo sc >> /etc/synthetic.conf
  sudo echo hpc >> /etc/synthetic.conf
fi

sudo chmod 644 /etc/synthetic.conf

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

# shea is a pain
# I bet he's not going to read this script

echo finished configuring for SSHFS
echo please make sure SSHFS is installed and then restart

#done

