import os
import subprocess
import sys

def build():
    # PyInstaller command arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "BiliCommentBot",
        "--hidden-import", "ttkbootstrap",
        "--collect-all", "ttkbootstrap",
        "--clean",
        "gui.py"
    ]
    
    print("Starting build process...")
    print(f"Command: {' '.join(args)}")
    
    try:
        subprocess.check_call(args)
        print("\nBuild completed successfully!")
        print(f"Executable can be found in: {os.path.join(os.getcwd(), 'dist', 'BiliCommentBot.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    build()
