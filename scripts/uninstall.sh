#!/bin/bash
set -e

echo "Welcome to the ValuaScript Uninstaller for macOS & Linux!"

# --- Configuration ---
APP_INSTALL_DIR="$HOME/.valuascript-tools"
BIN_INSTALL_DIR="/usr/local/bin"
SYMLINK_VSE="$BIN_INSTALL_DIR/vse"

# --- Remove Symbolic Links ---
echo "Removing command-line shortcuts..."
if [ -L "$SYMLINK_VSE" ]; then
    # Check if we need sudo
    if [ ! -w "$BIN_INSTALL_DIR" ]; then
        echo "Sudo privileges are required to remove the shortcut from $BIN_INSTALL_DIR."
        sudo rm -f "$SYMLINK_VSE"
    else
        rm -f "$SYMLINK_VSE"
    fi
    echo "Removed '$SYMLINK_VSE'."
else
    echo "Shortcut '$SYMLINK_VSE' not found, skipping."
fi

# --- Uninstall vsc from pipx ---
if command -v pipx &> /dev/null; then
    echo "Uninstalling the vsc compiler..."
    pipx uninstall valuascript-compiler || echo "valuascript-compiler was not installed via pipx, skipping."
else
    echo "pipx not found, skipping compiler uninstallation."
fi

# --- Remove Installation Directory ---
if [ -d "$APP_INSTALL_DIR" ]; then
    echo "Removing installation directory at $APP_INSTALL_DIR..."
    rm -rf "$APP_INSTALL_DIR"
else
    echo "Installation directory not found, skipping."
fi

echo ""
echo "✅ ValuaScript has been uninstalled successfully."
echo "You may want to manually remove 'VSC_ENGINE_PATH' from your shell profile (~/.zshrc, ~/.bashrc, etc.)."