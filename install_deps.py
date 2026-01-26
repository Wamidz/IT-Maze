#!/usr/bin/env python3
"""Install dependencies for IT-Maze"""
import subprocess
import sys

def install_pygame():
    """Try to install pygame with various approaches"""

    # Try 1: Install setuptools with distutils
    print("Attempting to install setuptools...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "setuptools<70"])

    # Try 2: Install pygame from cached wheel
    print("Attempting to install pygame...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame==2.1.4", "--prefer-binary"])
        print("✓ pygame 2.1.4 installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install pygame 2.1.4")
        return False

if __name__ == "__main__":
    if install_pygame():
        print("\n✓ Dependencies installed successfully!")

        # Verify
        try:
            import pygame
            print(f"✓ pygame {pygame.__version__} is now available")
        except ImportError:
            print("✗ pygame could not be imported")
            sys.exit(1)
    else:
        print("\n✗ Failed to install dependencies")
        sys.exit(1)
