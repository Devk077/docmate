#!/bin/bash

# DoqToq Qdrant Setup Script
# Installs and configures Qdrant vector database for DoqToq
# Supports both Docker and native binary installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_DATA_DIR="./data/vectorstore/qdrant"
DEFAULT_BIN_DIR="./bin"
DEFAULT_QDRANT_VERSION="latest"

# Logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in DoqToq project directory
check_project_root() {
    if [[ ! -f "pyproject.toml" ]] || [[ ! -d "backend" ]]; then
        log_error "This script must be run from the DoqToq project root directory"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    local missing_deps=()

    case $1 in
        "docker")
            if ! command -v docker &> /dev/null; then
                missing_deps+=("docker")
            fi
            if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
                missing_deps+=("docker-compose or docker compose plugin")
            fi
            ;;
        "native")
            if ! command -v curl &> /dev/null; then
                missing_deps+=("curl")
            fi
            if ! command -v tar &> /dev/null; then
                missing_deps+=("tar")
            fi
            ;;
    esac

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and try again"
        exit 1
    fi
}

# Get user preferences
get_user_preferences() {
    echo
    log_info "=== DoqToq Qdrant Setup ==="
    echo

    # Installation method
    echo "Choose installation method:"
    echo "1) Docker (recommended for development)"
    echo "2) Native binary"
    echo
    read -p "Enter your choice [1]: " install_method
    install_method=${install_method:-1}

    case $install_method in
        1)
            INSTALL_METHOD="docker"
            ;;
        2)
            INSTALL_METHOD="native"
            ;;
        *)
            log_error "Invalid choice. Please select 1 or 2."
            exit 1
            ;;
    esac

    # Data directory
    echo
    log_info "Qdrant will store vector data in a persistent directory."
    read -p "Data directory [$DEFAULT_DATA_DIR]: " QDRANT_DATA_DIR
    QDRANT_DATA_DIR=${QDRANT_DATA_DIR:-$DEFAULT_DATA_DIR}

    # For native installation, get additional preferences
    if [[ "$INSTALL_METHOD" == "native" ]]; then
        # Qdrant version
        echo
        log_info "Available versions: https://github.com/qdrant/qdrant/releases"
        read -p "Qdrant version [$DEFAULT_QDRANT_VERSION]: " QDRANT_VERSION
        QDRANT_VERSION=${QDRANT_VERSION:-$DEFAULT_QDRANT_VERSION}

        # Binary directory
        echo
        log_info "Choose where to install Qdrant binary:"
        echo "1) Project directory ($DEFAULT_BIN_DIR) [recommended]"
        echo "2) System directory (/usr/local/bin) [requires sudo]"
        echo "3) Custom directory"
        echo
        read -p "Enter your choice [1]: " bin_choice
        bin_choice=${bin_choice:-1}

        case $bin_choice in
            1)
                QDRANT_BIN_DIR="$DEFAULT_BIN_DIR"
                USE_SUDO=false
                ;;
            2)
                QDRANT_BIN_DIR="/usr/local/bin"
                USE_SUDO=true
                ;;
            3)
                read -p "Enter custom directory: " QDRANT_BIN_DIR
                if [[ "$QDRANT_BIN_DIR" == /usr/* ]] || [[ "$QDRANT_BIN_DIR" == /opt/* ]]; then
                    USE_SUDO=true
                else
                    USE_SUDO=false
                fi
                ;;
            *)
                log_error "Invalid choice."
                exit 1
                ;;
        esac
    fi

    # Summary
    echo
    log_info "=== Configuration Summary ==="
    echo "Installation method: $INSTALL_METHOD"
    echo "Data directory: $QDRANT_DATA_DIR"
    if [[ "$INSTALL_METHOD" == "native" ]]; then
        echo "Qdrant version: $QDRANT_VERSION"
        echo "Binary directory: $QDRANT_BIN_DIR"
        echo "Use sudo: $USE_SUDO"
    fi
    echo
    read -p "Continue with this configuration? [Y/n]: " confirm
    confirm=${confirm:-Y}

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories..."

    # Create data directory
    mkdir -p "$QDRANT_DATA_DIR"
    log_success "Created data directory: $QDRANT_DATA_DIR"

    # Create binary directory for native installation
    if [[ "$INSTALL_METHOD" == "native" ]]; then
        if [[ "$USE_SUDO" == "true" ]]; then
            sudo mkdir -p "$QDRANT_BIN_DIR"
        else
            mkdir -p "$QDRANT_BIN_DIR"
        fi
        log_success "Created binary directory: $QDRANT_BIN_DIR"
    fi
}

# Install Docker version
install_docker() {
    log_info "Setting up Qdrant with Docker..."

    # Create .env file with Qdrant settings if it doesn't exist
    if [[ ! -f ".env" ]]; then
        log_info "Creating .env file with Qdrant configuration..."
        cat > .env << EOF
# Vector Database Configuration
VECTOR_DB_PROVIDER=qdrant

# Qdrant Configuration
QDRANT_MODE=server
QDRANT_URL=http://localhost:6333
QDRANT_PATH=$QDRANT_DATA_DIR

# Add your other environment variables here
# GOOGLE_API_KEY=your_key_here
# MISTRAL_API_KEY=your_key_here
EOF
        log_success "Created .env file"
    else
        log_info "Updating existing .env file..."
        # Add Qdrant config if not present
        if ! grep -q "QDRANT_URL" .env; then
            echo "" >> .env
            echo "# Qdrant Configuration" >> .env
            echo "QDRANT_URL=http://localhost:6333" >> .env
            echo "QDRANT_PATH=$QDRANT_DATA_DIR" >> .env
        fi
        log_success "Updated .env file"
    fi

    # Start Qdrant service
    log_info "Starting Qdrant service..."
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile qdrant up -d qdrant
    else
        docker compose --profile qdrant up -d qdrant
    fi

    # Wait for Qdrant to be ready
    log_info "Waiting for Qdrant to be ready..."
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:6333/health > /dev/null 2>&1; then
            log_success "Qdrant is ready!"
            break
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Qdrant failed to start within timeout"
            exit 1
        fi

        log_info "Attempt $attempt/$max_attempts - waiting for Qdrant..."
        sleep 2
        ((attempt++))
    done

    # Display status
    echo
    log_success "Qdrant Docker installation completed!"
    echo
    echo "Qdrant is now running:"
    echo "  - REST API: http://localhost:6333"
    echo "  - gRPC API: http://localhost:6334"
    echo "  - Data directory: $QDRANT_DATA_DIR"
    echo "  - Dashboard: http://localhost:6333/dashboard"
    echo
    echo "To manage Qdrant:"
    echo "  - Stop: docker-compose --profile qdrant down"
    echo "  - Start: docker-compose --profile qdrant up -d"
    echo "  - Logs: docker-compose logs qdrant"
}

# Get architecture for native installation
get_architecture() {
    local arch
    arch=$(uname -m)

    case $arch in
        x86_64)
            echo "x86_64"
            ;;
        aarch64|arm64)
            echo "aarch64"
            ;;
        *)
            log_error "Unsupported architecture: $arch"
            exit 1
            ;;
    esac
}

# Get OS for native installation
get_os() {
    local os
    os=$(uname -s | tr '[:upper:]' '[:lower:]')

    case $os in
        linux)
            echo "unknown-linux-gnu"
            ;;
        darwin)
            echo "apple-darwin"
            ;;
        *)
            log_error "Unsupported OS: $os"
            exit 1
            ;;
    esac
}

# Install native binary
install_native() {
    log_info "Installing Qdrant native binary..."

    local arch os download_url
    arch=$(get_architecture)
    os=$(get_os)

    # Construct download URL
    if [[ "$QDRANT_VERSION" == "latest" ]]; then
        # Get latest version from GitHub API
        local latest_version
        latest_version=$(curl -s https://api.github.com/repos/qdrant/qdrant/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
        if [[ -z "$latest_version" ]]; then
            log_error "Failed to get latest Qdrant version"
            exit 1
        fi
        QDRANT_VERSION="$latest_version"
        log_info "Latest Qdrant version: $QDRANT_VERSION"
    fi

    download_url="https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-${arch}-${os}.tar.gz"

    log_info "Downloading Qdrant from: $download_url"

    # Download and extract
    local temp_dir
    temp_dir=$(mktemp -d)

    if ! curl -L "$download_url" -o "$temp_dir/qdrant.tar.gz"; then
        log_error "Failed to download Qdrant"
        rm -rf "$temp_dir"
        exit 1
    fi

    log_info "Extracting Qdrant binary..."
    if ! tar -xzf "$temp_dir/qdrant.tar.gz" -C "$temp_dir"; then
        log_error "Failed to extract Qdrant"
        rm -rf "$temp_dir"
        exit 1
    fi

    # Install binary
    log_info "Installing Qdrant binary to $QDRANT_BIN_DIR..."
    if [[ "$USE_SUDO" == "true" ]]; then
        sudo cp "$temp_dir/qdrant" "$QDRANT_BIN_DIR/"
        sudo chmod +x "$QDRANT_BIN_DIR/qdrant"
    else
        cp "$temp_dir/qdrant" "$QDRANT_BIN_DIR/"
        chmod +x "$QDRANT_BIN_DIR/qdrant"
    fi

    # Cleanup
    rm -rf "$temp_dir"

    # Create systemd service (optional)
    if [[ "$USE_SUDO" == "true" ]] && command -v systemctl &> /dev/null; then
        read -p "Create systemd service for Qdrant? [y/N]: " create_service
        if [[ "$create_service" =~ ^[Yy]$ ]]; then
            create_systemd_service
        fi
    fi

    # Create .env file
    if [[ ! -f ".env" ]]; then
        log_info "Creating .env file with Qdrant configuration..."
        cat > .env << EOF
# Vector Database Configuration
VECTOR_DB_PROVIDER=qdrant

# Qdrant Configuration
QDRANT_MODE=local
QDRANT_PATH=$QDRANT_DATA_DIR

# Add your other environment variables here
# GOOGLE_API_KEY=your_key_here
# MISTRAL_API_KEY=your_key_here
EOF
        log_success "Created .env file"
    fi

    echo
    log_success "Qdrant native installation completed!"
    echo
    echo "Qdrant binary installed at: $QDRANT_BIN_DIR/qdrant"
    echo "Data directory: $QDRANT_DATA_DIR"
    echo
    echo "To start Qdrant manually:"
    if [[ "$QDRANT_BIN_DIR" == "$DEFAULT_BIN_DIR" ]]; then
        echo "  $QDRANT_BIN_DIR/qdrant --storage-path $QDRANT_DATA_DIR"
    else
        echo "  qdrant --storage-path $QDRANT_DATA_DIR"
    fi
    echo
    echo "Qdrant will be available at:"
    echo "  - REST API: http://localhost:6333"
    echo "  - gRPC API: http://localhost:6334"
    echo "  - Dashboard: http://localhost:6333/dashboard"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."

    local service_file="/etc/systemd/system/qdrant.service"
    local abs_data_dir
    abs_data_dir=$(realpath "$QDRANT_DATA_DIR")

    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=qdrant
Group=qdrant
ExecStart=$QDRANT_BIN_DIR/qdrant --storage-path $abs_data_dir
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Create qdrant user
    if ! id "qdrant" &>/dev/null; then
        sudo useradd --system --no-create-home --shell /bin/false qdrant
    fi

    # Set permissions
    sudo chown -R qdrant:qdrant "$abs_data_dir"

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable qdrant
    sudo systemctl start qdrant

    log_success "Systemd service created and started"
    echo "  - Status: sudo systemctl status qdrant"
    echo "  - Logs: sudo journalctl -u qdrant -f"
    echo "  - Stop: sudo systemctl stop qdrant"
    echo "  - Start: sudo systemctl start qdrant"
}

# Main installation function
main() {
    check_project_root
    get_user_preferences
    check_dependencies "$INSTALL_METHOD"
    create_directories

    case $INSTALL_METHOD in
        "docker")
            install_docker
            ;;
        "native")
            install_native
            ;;
    esac

    echo
    log_success "Qdrant setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Update your DoqToq configuration to use Qdrant"
    echo "2. Run the DoqToq application"
    echo "3. Test vector operations with your documents"
    echo
    log_info "For more information, see: docs/VECTORDB_PHASE2.md"
}

# Handle script interruption
trap 'log_error "Setup interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"
