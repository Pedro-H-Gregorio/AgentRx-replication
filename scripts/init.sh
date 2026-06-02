#!/bin/bash

# Prints a message in a given color.
log() {
    local color_name="$1"
    local message="$2"
    local color_code

    case "${color_name}" in
        green)  color_code="\e[1;92m" ;;
        red)    color_code="\e[1;31m" ;;
        yellow) color_code="\e[1;33m" ;;
        blue)   color_code="\e[1;34m" ;;
        *)      color_code="\e[0m" ;;
    esac
    
    # Print the colored message, followed by a reset to default color
    echo -e "${color_code}${message}\e[0m"
}

log "green" "Checking for system dependencies (make, uv)..."

if ! command -v make &> /dev/null; then
    log "red" "'make' is not installed or not in your PATH. 'make' is required.

    Please install 'make' using your system's package manager:
      - Debian/Ubuntu: sudo apt install make (or build-essential)
      - Fedora/RHEL:   sudo dnf install make
      - macOS (Recommended): xcode-select --install
      - macOS (Homebrew):    brew install make
      - Windows:       choco install make (or use WSL)"
    
    exit 1
fi

if ! command -v uv &> /dev/null; then
    log "blue" "'uv' is not installed. Installing via official install script..."

    if command -v curl &> /dev/null; then
        curl -Ls https://astral.sh/uv/install.sh | bash
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | bash
    else
        log "red" "Error: Neither curl nor wget is available to download the install script."
        exit 1
    fi

    export PATH="$HOME/.cargo/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        log "red" "Failed to install 'uv'. Please check your installation manually."
        exit 1
    fi
fi

log "green" "Syncing Python dependencies with 'uv sync'..."
uv sync --all-groups

log "green" "Installing pre-commit hooks..."
uv run -- pre-commit install &>/dev/null || log "yellow" "Could not install pre-commit hooks. Make sure 'git' is installed and you are in a Git repository."

log "green" "Initialization script finished successfully."