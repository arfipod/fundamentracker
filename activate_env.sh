#!/bin/bash

# Check if the script is being sourced or run directly
if [ "$0" = "$BASH_SOURCE" ]; then
    echo "⚠️ Warning: This script must be sourced to modify your current shell."
    echo "Please run it like this:"
    echo "  source activate_env.sh"
    echo "or"
    echo "  . activate_env.sh"
    exit 1
fi

if [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
    echo "Virtual environment is now active!"
else
    echo "❌ Error: Virtual environment '.venv' not found in the current directory."
    echo "You may need to create it first runnig: python3 -m venv .venv"
fi
