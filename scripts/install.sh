#!/bin/bash
set -e

echo "Welcome to the ValuaScript Installer for macOS & Linux!"

# --- Configuration ---
APP_INSTALL_DIR="$HOME/.valuascript-tools"
BIN_INSTALL_DIR="/usr/local/bin"

# --- Detect OS and Architecture ---
OS_TYPE="$(uname -s)"
CPU_ARCH="$(uname -m)"

case "$OS_TYPE" in
    Linux)
        ASSET_SUFFIX="linux-x64"
        ;;
    Darwin)
        if [ "$CPU_ARCH" = "arm64" ]; then
            ASSET_SUFFIX="macos-arm64"
        else
            ASSET_SUFFIX="macos-x64" # For Intel Macs
        fi
        ;;
    *)
        echo "Error: Unsupported operating system '$OS_TYPE'."
        exit 1
        ;;
esac

# --- Fetch Latest Release URL ---
REPO="Alessio2704/monte-carlo-simulator"
LATEST_RELEASE_API_URL="https://api.github.com/repos/$REPO/releases/latest"
DOWNLOAD_URL=$(curl -sL "$LATEST_RELEASE_API_URL" | grep "browser_download_url.*${ASSET_SUFFIX}.zip" | cut -d '"' -f 4 | head -n 1)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not find a release asset for your system ($ASSET_SUFFIX)."
    exit 1
fi

# --- Download and Install ---
echo "Creating installation directory at $APP_INSTALL_DIR..."
mkdir -p "$APP_INSTALL_DIR"

TMP_FILE=$(mktemp)
echo "Downloading ValuaScript from: $DOWNLOAD_URL"
curl -L "$DOWNLOAD_URL" -o "$TMP_FILE"

echo "Unzipping files to permanent location..."
unzip -o "$TMP_FILE" -d "$APP_INSTALL_DIR"

if [ "$OS_TYPE" = "Darwin" ]; then
    echo "Removing macOS quarantine attributes..."
    xattr -cr "$APP_INSTALL_DIR" 2>/dev/null || true
fi

# Make binaries executable
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
    python3 -m pipx ensurepath

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
    python3 -m pipx ensurepath
fi

echo "Installing ValuaScript Compiler with pipx..."
pipx install valuascript-compiler

# --- Cleanup ---
rm "$TMP_FILE"

echo ""
echo "✅ ValuaScript has been installed successfully!"
echo "Please open a new terminal session to start using 'vsc' and 'vse'."