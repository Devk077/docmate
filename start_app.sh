#!/bin/bash

# DoqToq Startup Script
# Starts the Streamlit app after enforcing Qdrant dependency compatibility.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer the repo-local virtualenv if no environment is active.
if [[ -z "${VIRTUAL_ENV:-}" && -x "$SCRIPT_DIR/doqtoq-env/bin/python" ]]; then
    export PATH="$SCRIPT_DIR/doqtoq-env/bin:$PATH"
fi

PYTHON_BIN="$(command -v python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
    echo "Error: Python is not available in PATH."
    exit 1
fi

check_qdrant_stack() {
    "$PYTHON_BIN" - <<'PY'
from importlib.metadata import version

import langchain_qdrant  # noqa: F401
import qdrant_client  # noqa: F401

print("qdrant-client:", version("qdrant-client"))
print("langchain-qdrant:", version("langchain-qdrant"))
print("protobuf:", version("protobuf"))
PY
}

repair_qdrant_stack() {
    PIP_DISABLE_PIP_VERSION_CHECK=1 "$PYTHON_BIN" -m pip install --upgrade \
        "protobuf>=5.29.0,<7.0.0" \
        "qdrant-client>=1.15.1,<2.0.0" \
        "langchain-qdrant>=1.1.0,<2.0.0"
}

# Set environment variables to suppress warnings
export TORCH_WARN=0
export PYTORCH_DISABLE_TORCH_FUNCTION_WARN=1
export TOKENIZERS_PARALLELISM=false

# Fix for PyTorch 2.7+ compatibility with Streamlit file watcher
export STREAMLIT_DISABLE_WATCHDOG_WARNING=1
export STREAMLIT_FILE_WATCHER_TYPE=none

echo "Checking Qdrant dependencies..."
if ! check_qdrant_stack; then
    echo "Qdrant dependency mismatch detected. Attempting automatic repair..."
    if ! repair_qdrant_stack; then
        echo ""
        echo "Error: Automatic Qdrant repair failed."
        echo "Run this manually once network access is available:"
        echo "  $PYTHON_BIN -m pip install --upgrade \"protobuf>=5.29.0,<7.0.0\" \"qdrant-client>=1.15.1,<2.0.0\" \"langchain-qdrant>=1.1.0,<2.0.0\""
        exit 1
    fi

    echo "Re-validating Qdrant dependencies..."
    if ! check_qdrant_stack; then
        echo "Error: Qdrant dependency validation still fails after repair."
        exit 1
    fi
fi

echo "Starting DoqToq application..."
echo "The application will be available at: http://localhost:8501"
echo ""

"$PYTHON_BIN" -m streamlit run app/main.py \
    --server.port 8501 \
    --server.headless true \
    --server.fileWatcherType none
