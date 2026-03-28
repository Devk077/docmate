#!/bin/bash

# DoqToq Environment Activation Script
# This script activates the doqtoq conda environment and sets up the development environment

echo "Activating DoqToq development environment..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not available. Please install Anaconda/Miniconda first."
    exit 1
fi

# Check if doqtoq environment exists
if ! conda env list | grep -q "^doqtoq "; then
    echo "Error: doqtoq environment does not exist."
    echo "Please create it first using: conda env create -f environment.yaml"
    exit 1
fi

# Activate the environment
echo "Activating conda environment: doqtoq"
eval "$(conda shell.bash hook)"
conda activate doqtoq

# Verify activation
if [[ "$CONDA_DEFAULT_ENV" == "doqtoq" ]]; then
    echo "Successfully activated doqtoq environment"
    echo "Python version: $(python --version)"
    echo "Environment location: $CONDA_PREFIX"

    # Check if pre-commit is properly set up
    if command -v pre-commit &> /dev/null; then
        echo "Pre-commit is installed and ready"
        if [[ -f .git/hooks/pre-commit ]]; then
            echo "Pre-commit hooks are installed"
        else
            echo "Pre-commit hooks not installed. Run: pre-commit install"
        fi
    else
        echo "Pre-commit not found. Installing..."
        pip install pre-commit
        pre-commit install
    fi

    echo ""
    echo "DoqToq development environment is ready!"
    echo "Available commands:"
    echo "   streamlit run app/main.py     - Start the application"
    echo "   pre-commit run --all-files    - Run code quality checks"
    echo "   python -m pytest tests/       - Run tests"
    echo "   conda deactivate              - Exit this environment"
    echo ""
else
    echo "Failed to activate doqtoq environment"
    exit 1
fi
