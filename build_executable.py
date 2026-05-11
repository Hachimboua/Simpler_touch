"""
Build a standalone executable for BlobTracker using PyInstaller.
Run this script to create a single .exe file that can be distributed and run anywhere.
"""
import subprocess
import sys
import os

def build_executable():
    """Build the BlobTracker executable."""
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    print("\nBuilding BlobTracker executable...")
    print("This may take a few minutes...\n")
    
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "blobtracker", "main.py")
    
    # Build the executable
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "BlobTracker",
        "--add-data", "blobtracker:blobtracker",
        main_py
    ]
    
    # Add icon if it exists
    if os.path.exists("blobtracker/blobtracker.ico"):
        cmd.insert(-1, "--icon")
        cmd.insert(-1, "blobtracker/blobtracker.ico")
    
    try:
        subprocess.check_call(cmd)
        print("\n✓ Build complete!")
        print(f"\nYour executable is ready: {script_dir}\\dist\\BlobTracker.exe")
        print("\nYou can now:")
        print("1. Double-click BlobTracker.exe to run the app")
        print("2. Move it anywhere on your computer")
        print("3. Create a shortcut on your desktop for easy access")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
