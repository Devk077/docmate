__module_name__ = "torch_compatibility"

"""
PyTorch compatibility fix for Streamlit file watcher issues.

This module provides a workaround for the torch.classes issue that occurs
with PyTorch 2.7+ and Streamlit's file watching mechanism.
"""

import sys
import warnings
from types import ModuleType


def patch_torch_classes():
    """
    Patch torch.classes to prevent Streamlit file watcher errors.

    The issue occurs when Streamlit tries to inspect torch.classes.__path__._path
    but the newer PyTorch version doesn't expose it in the expected way.
    """
    try:
        import torch

        # Check if torch.classes exists and needs patching
        if hasattr(torch, "_classes") and hasattr(torch._classes, "__getattr__"):
            # Create a wrapper that handles the problematic __path__ attribute
            original_getattr = torch._classes.__getattr__

            def safe_getattr(name):
                if name == "__path__":
                    # Return a mock object that has _path attribute
                    class MockPath:
                        _path = []

                    return MockPath()
                return original_getattr(name)

            # Replace the __getattr__ method
            torch._classes.__getattr__ = safe_getattr

        # Also patch torch.classes if it exists
        if hasattr(torch, "classes"):
            if not hasattr(torch.classes, "__path__"):
                # Add a mock __path__ attribute
                class MockPath:
                    _path = []

                torch.classes.__path__ = MockPath()

    except Exception as e:
        # If patching fails, just warn and continue
        warnings.warn(f"Could not patch torch.classes: {e}", UserWarning)


def apply_streamlit_fixes():
    """Apply all necessary fixes for Streamlit compatibility."""

    # Apply torch.classes patch
    patch_torch_classes()

    # Suppress additional warnings that might appear
    warnings.filterwarnings("ignore", message=".*torch.classes.*")
    warnings.filterwarnings("ignore", message=".*__path__._path.*")
    warnings.filterwarnings("ignore", message=".*no running event loop.*")

    print("Applied PyTorch compatibility fixes for Streamlit")


if __name__ == "__main__":
    apply_streamlit_fixes()
