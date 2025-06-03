#!/bin/zsh

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo "$0" "$@"
fi

USERNAME_="hb"
FULLNAME="Homebrew User"
HOMEDIR="/usr/local/${USERNAME_}"
SHELL="/bin/bash"
MAX_UID=499
MIN_UID=200
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
    UID_USE=$((UID_USE - 1))
done

if [ "$UID_USE" -lt "$MIN_UID" ]; then
    echo "No available UID found between $MIN_UID and $MAX_UID. Exiting."
    exit 2
fi

echo "Using UID $UID_USE for user '$USERNAME_'"

# Create the user
sysadminctl -addUser "$USERNAME_" \
    -fullName "$FULLNAME" \
    -UID "$UID_USE" \
    -shell "$SHELL" \
    -home "$HOMEDIR" \
    -password "$PASSWORD"

# Create and set ownership of the home directory
mkdir -p "$HOMEDIR"
chown "${USERNAME_}:staff" "$HOMEDIR"

echo "User '$USERNAME_' created with UID $UID_USE and home $HOMEDIR"

# Temporarily add user to admin for Homebrew install
dseditgroup -o edit -a "$USERNAME_" -t user admin

# Run Homebrew installer as the new user
pushd "$HOMEDIR" > /dev/null
sudo -u "$USERNAME_" env HOME="$HOMEDIR" /bin/bash -c \
  "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
popd > /dev/null

# Remove from admin group
dseditgroup -o edit -d "$USERNAME_" -t user admin

# Hide user from login screen
defaults write /Library/Preferences/com.apple.loginwindow HiddenUsersList -array-add "$USERNAME_"
dscl . -create "/Users/$USERNAME_" IsHidden 1
dscl . -create "/Users/$USERNAME_" UserShell /usr/bin/false

# Restrict SSH
if grep -q "^DenyUsers" /etc/ssh/sshd_config; then
  echo "Please manually add $USERNAME_ to DenyUsers in /etc/ssh/sshd_config"
else
  echo "DenyUsers $USERNAME_" >> /etc/ssh/sshd_config
  launchctl stop com.openssh.sshd
  launchctl start com.openssh.sshd
fi

# Wrap brew with elevation handling
BREW_BIN="/opt/homebrew/bin"
if [ ! -x "$BREW_BIN/brew" ]; then
  echo "Warning: brew not found in $BREW_BIN. Skipping wrapping."
  exit 3
fi

if [ ! -f "$BREW_BIN/brewdo" ]; then
  sudo mv "$BREW_BIN/brew" "$BREW_BIN/brewdo"
fi

cat << 'EOF' | tee "$BREW_BIN/brew" > /dev/null
#!/bin/zsh
if [[ "$USER" != "hb" ]]; then
    homedir="/usr/local/hb"
    orig_dir="$PWD"
    trap 'sudo dseditgroup -o edit -d hb -t user admin; cd "$orig_dir"' EXIT
    cd "$homedir" || exit 1
    sudo dseditgroup -o edit -a hb -t user admin
    sudo -u hb env HOME="$homedir" brewdo "$@"
else
    brewdo "$@"
fi
EOF

chmod +x "$BREW_BIN/brew"
