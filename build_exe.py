import os
import subprocess
import sys

VERSION = "V2.2"

def build():
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", f"BiliCommentBot_{VERSION}",
        "--hidden-import", "ttkbootstrap",
        "--collect-all", "ttkbootstrap",
        "--clean",
        "gui.py"
    ]
    
    print(f"Starting build process for {VERSION}...")
    print(f"Command: {' '.join(args)}")
    
    try:
        subprocess.check_call(args)
        print(f"\nBuild completed successfully!")
        print(f"Executable: {os.path.join(os.getcwd(), 'dist', f'BiliCommentBot_{VERSION}.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    build()
