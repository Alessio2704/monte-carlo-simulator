#!/bin/bash
set -e

echo "Welcome to the ValuaScript Installer for macOS & Linux!"

# --- Configuration ---
APP_INSTALL_DIR="$HOME/.valuascript-tools"
BIN_INSTALL_DIR="/usr/local/bin"
REPO="Alessio2704/monte-carlo-simulator"

# --- Detect OS and Architecture ---
OS_TYPE="$(uname -s)"
CPU_ARCH="$(uname -m)"

case "$OS_TYPE" in
    Linux)
        ENGINE_ASSET_SUFFIX="linux-x64"
        ;;
    Darwin)
        if [ "$CPU_ARCH" = "arm64" ]; then
            ENGINE_ASSET_SUFFIX="macos-arm64"
        else
            ENGINE_ASSET_SUFFIX="macos-x64"
        fi
        ;;
    *)
        echo "Error: Unsupported operating system '$OS_TYPE'."
        exit 1
        ;;
esac

# --- Fetch Latest Release URLs ---
echo "Fetching latest release information from GitHub..."
LATEST_RELEASE_API_URL="https://api.github.com/repos/$REPO/releases/latest"
ASSETS_JSON=$(curl -sL "$LATEST_RELEASE_API_URL")

DOWNLOAD_URL_ENGINE=$(echo "$ASSETS_JSON" | grep "browser_download_url.*${ENGINE_ASSET_SUFFIX}.zip" | cut -d '"' -f 4 | head -n 1)
DOWNLOAD_URL_VSIX=$(echo "$ASSETS_JSON" | grep "browser_download_url.*.vsix" | cut -d '"' -f 4 | head -n 1)
VSIX_NAME=$(basename "$DOWNLOAD_URL_VSIX")

if [ -z "$DOWNLOAD_URL_ENGINE" ]; then
    echo "Error: Could not find an engine release asset for your system ($ENGINE_ASSET_SUFFIX)."
    exit 1
fi

# --- Download and Install Engine ---
echo "Creating installation directory at $APP_INSTALL_DIR..."
mkdir -p "$APP_INSTALL_DIR"

TMP_FILE=$(mktemp)
echo "Downloading ValuaScript Engine from: $DOWNLOAD_URL_ENGINE"
curl -L "$DOWNLOAD_URL_ENGINE" -o "$TMP_FILE"

echo "Unzipping files to permanent location..."
unzip -o "$TMP_FILE" -d "$APP_INSTALL_DIR"

if [ "$OS_TYPE" = "Darwin" ]; then
    echo "Removing macOS quarantine attributes..."
    xattr -cr "$APP_INSTALL_DIR" 2>/dev/null || true
fi

chmod +x "$APP_INSTALL_DIR/vse"

# --- Create Symbolic Links ---
echo "Ensuring command-line shortcut directory exists..."
if [ ! -d "$BIN_INSTALL_DIR" ]; then
    echo "Directory $BIN_INSTALL_DIR not found. Creating it now (requires sudo)..."
    sudo mkdir -p "$BIN_INSTALL_DIR"
fi
echo "Creating command-line shortcut in $BIN_INSTALL_DIR (requires sudo)..."
sudo ln -sf "$APP_INSTALL_DIR/vse" "$BIN_INSTALL_DIR/vse"


# --- Install vsc from PyPI ---
echo "Installing the vsc compiler from PyPI..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install it to continue."
    exit 1
fi

if [ "$OS_TYPE" = "Darwin" ]; then
    if ! command -v brew &> /dev/null; then
        echo "Warning: Homebrew not found. Falling back to installing pipx with pip." >&2
        python3 -m pip install --user --upgrade pipx
    else
        echo "Using Homebrew to install/upgrade pipx..."
        brew install pipx
    fi

elif [ "$OS_TYPE" = "Linux" ]; then

    if ! command -v pipx &> /dev/null; then
        echo "Attempting to install pipx using common package managers or pip..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y pipx
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y pipx
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm python-pipx
        fi
    fi
    if ! command -v pipx &> /dev/null; then
        echo "pipx not found via package manager, falling back to pip..."
        python3 -m pip install --user --upgrade pipx
    fi
fi

# If pipx was installed via pip to the user's local directory, that directory
# might not be in the PATH yet for this script session.
# We add it manually to the script's PATH to ensure the next commands work.
if ! command -v pipx &> /dev/null; then
    export PATH="$HOME/.local/bin:$PATH"
fi

pipx ensurepath
echo "Installing ValuaScript Compiler with pipx..."
pipx install valuascript-compiler

# --- Install VS Code Extension ---
if [ -z "$DOWNLOAD_URL_VSIX" ]; then
    echo "Warning: Could not find a .vsix extension file in the release assets. Skipping."
else
    echo "Attempting to install the ValuaScript VS Code extension..."
    CODE_CMD=""
    # Search for the 'code' command in common locations
    if command -v code &> /dev/null; then
        CODE_CMD="code"
    elif [ -f "/usr/local/bin/code" ]; then
        CODE_CMD="/usr/local/bin/code"
    elif [ -f "/snap/bin/code" ]; then # For Linux with Snap
        CODE_CMD="/snap/bin/code"
    elif [ "$OS_TYPE" = "Darwin" ] && [ -f "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]; then
        CODE_CMD="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
    fi

    if [ -z "$CODE_CMD" ]; then
        echo "Warning: VS Code command-line tool ('code') not found in PATH."
        echo "Please install the extension manually from the downloaded file:"
        echo "$APP_INSTALL_DIR/$VSIX_NAME"
    else
        echo "Found VS Code. Downloading and installing extension..."
        curl -L "$DOWNLOAD_URL_VSIX" -o "$APP_INSTALL_DIR/$VSIX_NAME"
        
        # Install the extension
        "$CODE_CMD" --install-extension "$APP_INSTALL_DIR/$VSIX_NAME" || echo "Failed to install extension. VS Code might not be running."

        echo "✅ VS Code extension installed."
    fi
fi

# --- Cleanup ---
rm "$TMP_FILE"

echo ""
echo "✅ ValuaScript installation is complete!"
echo "Please open a new terminal session to use 'vsc' and 'vse'."