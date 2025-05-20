#!/bin/zsh

set -euo pipefail

USERNAME_="hb"
FULLNAME="Homebrew User"
HOMEDIR="/usr/local/${USERNAME_}"
SHELL="/bin/bash"
MAX_UID=499
MIN_UID=200  # Don't go too low; <200 is typically reserved
PASSWORD="-"

# Check if user already exists
if id "$USERNAME_" &>/dev/null; then
    echo "User '$USERNAME_' already exists. Exiting."
    exit 1
fi

# Find a free UID < 500
UID_USE=$MAX_UID
while [ "$UID_USE" -ge "$MIN_UID" ]; do
    if ! dscl . -list /Users UniqueID | awk '{print $2}' | grep -q "^${UID_USE}$"; then
        break
    fi
    UID_USE=$((UID - 1))
done

if [ "$UID" -lt "$MIN_UID" ]; then
    echo "No available UID found between $MIN_UID and $MAX_UID. Exiting."
    exit 2
fi

echo "Using UID $UID_USE for user '$USERNAME_'"

# Create the user
sudo sysadminctl -addUser "$USERNAME_" \
    -fullName "$FULLNAME" \
    -UID "$UID_USE" \
    -shell "$SHELL" \
    -home "$HOMEDIR" \
    -password "$PASSWORD"

# Create and set ownership of the home directory
sudo mkdir -p "$HOMEDIR"
sudo chown "$USERNAME_:staff" "$HOMEDIR"

# Hide user from login screen (redundant with UID < 500, but for safety)
sudo defaults write /Library/Preferences/com.apple.loginwindow HiddenUsersList -array-add "$USERNAME_"
sudo dscl . -create "/Users/$USERNAME_" IsHidden 1
sudo dscl . -create "/Users/$USERNAME_" UserShell /usr/bin/false
if grep -q "^DenyUsers" /etc/ssh/sshd_config; then
  echo "Please add $USERNAME_ to the DenyUsers option in /etc/ssh/sshd_config"
else
  echo "DenyUsers $USERNAME_" | sudo tee -a /etc/ssh/sshd_config > /dev/null
  sudo launchctl stop com.openssh.sshd
  sudo launchctl start com.openssh.sshd
fi

echo "User '$USERNAME_' created with UID $UID_USE and home $HOMEDIR"

sudo dseditgroup -o edit -a "$USERNAME_" -t user admin
cd $HOMEDIR
sudo -u hb /bin/bash -ic "HOME=$HOMEDIR $(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
cd -

sudo mv /usr/local/bin/brew /usr/local/bin/brewdo
cat << 'EOF' | sudo tee -a /usr/local/bin/brew > /dev/null
#!/bin/zsh
if [[ "$USER" != "hb" ]]; then
    homedir="/usr/local/hb"
    orig_dir="$PWD"
    trap 'sudo dseditgroup -o edit -d hb -t user admin; cd "$orig_dir"' EXIT
    cd "$homedir" || return 1
    sudo dseditgroup -o edit -a hb -t user admin
    sudo -u hb env HOME="$homedir" brewdo "$@"
else
    brewdo "$@"
fi
EOF
sudo chmod +x /usr/local/bin/brew
