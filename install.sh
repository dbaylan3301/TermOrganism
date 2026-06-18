#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/termorganism"

echo "Installing TermOrganism..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy project files
cp -r "$REPO_DIR/core" "$INSTALL_DIR/"
cp -r "$REPO_DIR/bin" "$INSTALL_DIR/"
cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/"

# Add to PATH if not already there
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "termorganism" "$SHELL_RC" 2>/dev/null; then
        echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\"" >> "$SHELL_RC"
        echo "Added to PATH in $SHELL_RC"
    fi
fi

echo "Installed to $INSTALL_DIR"
echo "Run 'source $SHELL_RC' or open a new terminal"
