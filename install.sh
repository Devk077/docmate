#!/bin/bash
# DoqToq Installation Script
# Supports multiple installation methods and environments

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_MIN_VERSION="3.10"
DOQTOQ_ENV_NAME="doqtoq"
INSTALL_METHOD=""
INSTALL_DEV=false
SKIP_DEPS=false

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    cat << EOF
DoqToq Installation Script

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -m, --method METHOD Installation method: conda, pip, docker
    -d, --dev           Install development dependencies
    -s, --skip-deps     Skip dependency checks
    -e, --env NAME      Environment name (default: doqtoq)

EXAMPLES:
    $0 --method conda           # Install with conda
    $0 --method pip --dev       # Install with pip + dev dependencies
    $0 --method docker          # Build and run with Docker
    $0 --skip-deps              # Skip system dependency checks

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -m|--method)
                INSTALL_METHOD="$2"
                shift 2
                ;;
            -d|--dev)
                INSTALL_DEV=true
                shift
                ;;
            -s|--skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            -e|--env)
                DOQTOQ_ENV_NAME="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python_version() {
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        return 1
    fi

    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local required_version=$PYTHON_MIN_VERSION

    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python $python_version is installed, but Python $required_version or higher is required"
        return 1
    fi

    print_success "Python $python_version is installed"
    return 0
}

# Check system dependencies
check_dependencies() {
    if [ "$SKIP_DEPS" = true ]; then
        print_warning "Skipping dependency checks"
        return 0
    fi

    print_status "Checking system dependencies..."

    # Check Python
    if ! check_python_version; then
        print_error "Python version check failed"
        exit 1
    fi

    # Check Git
    if ! command_exists git; then
        print_warning "Git is not installed. Some features may not work."
    fi

    print_success "System dependencies check completed"
}

# Auto-detect best installation method
detect_install_method() {
    if [ -n "$INSTALL_METHOD" ]; then
        return 0
    fi

    print_status "Auto-detecting best installation method..."

    if command_exists conda; then
        INSTALL_METHOD="conda"
        print_status "Found conda, using conda installation method"
    elif command_exists docker; then
        INSTALL_METHOD="docker"
        print_status "Found docker, using docker installation method"
    elif command_exists pip3 || command_exists pip; then
        INSTALL_METHOD="pip"
        print_status "Found pip, using pip installation method"
    else
        print_error "No suitable installation method found. Please install conda, docker, or pip."
        exit 1
    fi
}

# Install with conda
install_conda() {
    print_status "Installing DoqToq with conda..."

    # Check if environment exists
    if conda env list | grep -q "^$DOQTOQ_ENV_NAME "; then
        print_warning "Environment '$DOQTOQ_ENV_NAME' already exists"
        read -p "Do you want to remove it and create a new one? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            conda env remove -n "$DOQTOQ_ENV_NAME"
        else
            print_status "Using existing environment"
        fi
    fi

    # Create environment from YAML
    if [ -f "environment.yaml" ]; then
        print_status "Creating environment from environment.yaml..."
        conda env create -f environment.yaml -n "$DOQTOQ_ENV_NAME"
    else
        print_status "Creating environment with Python..."
        conda create -n "$DOQTOQ_ENV_NAME" python=3.12 -y
        conda activate "$DOQTOQ_ENV_NAME"
        pip install -r requirements.txt
    fi

    if [ "$INSTALL_DEV" = true ]; then
        print_status "Installing development dependencies..."
        conda activate "$DOQTOQ_ENV_NAME"
        pip install -r requirements-dev.txt
    fi

    print_success "Conda installation completed!"
    print_status "To activate the environment, run: conda activate $DOQTOQ_ENV_NAME"
}

# Install with pip
install_pip() {
    print_status "Installing DoqToq with pip..."

    # Check if we should create a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$DOQTOQ_ENV_NAME"
        source "$DOQTOQ_ENV_NAME/bin/activate"
    fi

    # Upgrade pip
    python3 -m pip install --upgrade pip

    # Install requirements
    pip install -r requirements.txt

    if [ "$INSTALL_DEV" = true ]; then
        print_status "Installing development dependencies..."
        pip install -r requirements-dev.txt
    fi

    print_success "Pip installation completed!"
    if [ -z "$VIRTUAL_ENV" ]; then
        print_status "To activate the environment, run: source $DOQTOQ_ENV_NAME/bin/activate"
    fi
}

# Install with Docker
install_docker() {
    print_status "Installing DoqToq with Docker..."

    # Build Docker image
    print_status "Building Docker image..."
    docker build -f Dockerfile.venv -t doqtoq:latest .

    # Create docker-compose.yml if it doesn't exist
    if [ ! -f "docker-compose.yml" ]; then
        print_status "Creating docker-compose.yml..."
        cat > docker-compose.yml << EOF
version: '3.8'
services:
  doqtoq:
    image: doqtoq:latest
    ports:
      - "8501:8501"
    environment:
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - MISTRAL_API_KEY=\${MISTRAL_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
EOF
    fi

    print_success "Docker installation completed!"
    print_status "To run DoqToq, use: docker-compose up"
}

# Setup environment variables
setup_env() {
    if [ ! -f ".env" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your API keys"
        print_status "Required API keys:"
        print_status "  - GOOGLE_API_KEY (for Google Gemini)"
        print_status "  - MISTRAL_API_KEY (for Mistral AI)"
    else
        print_status ".env file already exists"
    fi
}

# Post-installation setup
post_install() {
    print_status "Running post-installation setup..."

    # Create necessary directories
    mkdir -p data/uploads
    mkdir -p logs

    # Setup environment variables
    setup_env

    # Install pre-commit hooks if development mode
    if [ "$INSTALL_DEV" = true ] && command_exists pre-commit; then
        print_status "Installing pre-commit hooks..."
        pre-commit install
    fi

    print_success "Post-installation setup completed!"
}

# Main installation function
main() {
    print_status "DoqToq Installation Script"
    print_status "========================="

    parse_args "$@"
    check_dependencies
    detect_install_method

    case $INSTALL_METHOD in
        conda)
            install_conda
            ;;
        pip)
            install_pip
            ;;
        docker)
            install_docker
            ;;
        *)
            print_error "Unknown installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac

    post_install

    # Print final instructions
    print_success "🎉 DoqToq installation completed successfully!"
    print_status ""
    print_status "Next steps:"
    case $INSTALL_METHOD in
        conda)
            print_status "1. Activate environment: conda activate $DOQTOQ_ENV_NAME"
            print_status "2. Edit .env file with your API keys"
            print_status "3. Run DoqToq: streamlit run app/main.py"
            ;;
        pip)
            print_status "1. Activate environment: source $DOQTOQ_ENV_NAME/bin/activate"
            print_status "2. Edit .env file with your API keys"
            print_status "3. Run DoqToq: streamlit run app/main.py"
            ;;
        docker)
            print_status "1. Edit .env file with your API keys"
            print_status "2. Run DoqToq: docker-compose up"
            print_status "3. Open http://localhost:8501 in your browser"
            ;;
    esac
    print_status ""
    print_status "For help and documentation, visit: https://github.com/shre-db/doqtoq"
}

# Run main function
main "$@"
