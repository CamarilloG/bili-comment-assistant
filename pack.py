"""
B站评论助手 V2.2 — 绿色打包脚本

将项目打包为「解压即用」的绿色版：
  1. 下载 Python 3.11 embeddable package
  2. 安装 pip 和项目依赖到内置 Python
  3. 复制项目源码 + 前端产物
  4. 生成启动器 start.bat
  5. 压缩为 zip

用法:
    python pack.py          # 完整打包
    python pack.py --skip-download  # 跳过 Python 下载（已有缓存时）

产物: dist/BiliCommentBot_V2.2_Portable.zip
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import argparse
from pathlib import Path

VERSION = "2.2"
APP_NAME = f"BiliCommentBot_V{VERSION}"
PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"

PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "dist" / "pack_build"
OUTPUT_DIR = PROJECT_ROOT / "dist"
CACHE_DIR = PROJECT_ROOT / "dist" / "cache"

EXCLUDE_PATTERNS = {
    "__pycache__", ".git", ".gitignore", ".cursor", "node_modules",
    "dist", "pack_build", "cache", ".env", "*.pyc", "debug-*.log",
    "login_qrcode.png", "comment_log.csv", "cookies.json",
    "废弃",  # 废弃代码与历史文档，不参与打包
}

SOURCE_DIRS = [
    "core", "modules", "web", "gui_tabs", "utils", "server",
    "ai_center", "bots",
]

SOURCE_FILES = [
    "gui.py", "main.py", "requirements.txt", "config.template.yaml",
]


def log(msg):
    try:
        print(f"  [*] {msg}")
    except UnicodeEncodeError:
        print(f"  [*] {msg.encode('ascii', 'replace').decode()}")


def step(msg):
    try:
        print(f"\n{'='*50}")
        print(f"  {msg}")
        print(f"{'='*50}")
    except UnicodeEncodeError:
        print(f"\n{'='*50}")
        print(f"  {msg.encode('ascii', 'replace').decode()}")
        print(f"{'='*50}")


def download_python_embed(skip_download=False):
    """Download and extract Python embeddable package."""
    cache_zip = CACHE_DIR / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    extract_dir = BUILD_DIR / "python"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)

    if not cache_zip.exists() and not skip_download:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        log(f"Downloading Python {PYTHON_VERSION} embeddable...")
        urllib.request.urlretrieve(PYTHON_EMBED_URL, cache_zip)
        log("Download complete.")
    elif not cache_zip.exists():
        print(f"ERROR: Cached Python not found at {cache_zip}")
        print("Run without --skip-download first.")
        sys.exit(1)

    log("Extracting Python embeddable...")
    with zipfile.ZipFile(cache_zip, "r") as zf:
        zf.extractall(extract_dir)

    pth_file = extract_dir / f"python311._pth"
    if pth_file.exists():
        content = pth_file.read_text()
        content = content.replace("#import site", "import site")
        pth_file.write_text(content)
        log("Enabled site-packages in ._pth")

    return extract_dir


def install_pip(python_dir):
    """Install pip into the embedded Python."""
    python_exe = python_dir / "python.exe"
    get_pip = CACHE_DIR / "get-pip.py"

    if not get_pip.exists():
        log("Downloading get-pip.py...")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)

    log("Installing pip...")
    subprocess.check_call(
        [str(python_exe), str(get_pip), "--no-warn-script-location"],
        stdout=subprocess.DEVNULL,
    )


def install_dependencies(python_dir):
    """Install project dependencies via pip."""
    python_exe = python_dir / "python.exe"
    req_file = PROJECT_ROOT / "requirements.txt"

    log("Installing project dependencies...")
    subprocess.check_call(
        [str(python_exe), "-m", "pip", "install", "-r", str(req_file),
         "--no-warn-script-location", "-q"],
    )
    log("Dependencies installed.")


def copy_source():
    """Copy project source code to build directory."""
    app_dir = BUILD_DIR / "app"
    if app_dir.exists():
        shutil.rmtree(app_dir)
    app_dir.mkdir(parents=True)

    for d in SOURCE_DIRS:
        src = PROJECT_ROOT / d
        if src.exists():
            shutil.copytree(src, app_dir / d, ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS))
            log(f"Copied {d}/")

    for f in SOURCE_FILES:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy2(src, app_dir / f)
            log(f"Copied {f}")

    frontend_dist = PROJECT_ROOT / "web" / "frontend-v2" / "dist"
    if frontend_dist.exists():
        target = app_dir / "web" / "frontend-v2" / "dist"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(frontend_dist, target, dirs_exist_ok=True)
        log("Copied web/frontend-v2/dist/")
    else:
        log("WARNING: frontend-v2/dist not found — run 'npm run build' first")


def create_launcher():
    """Generate the portable start.bat launcher."""
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        f"title BiliBot V{VERSION}",
        "",
        "set PYTHON_EXE=%~dp0python\\python.exe",
        "set APP_DIR=%~dp0app",
        "",
        'if not exist "%PYTHON_EXE%" (',
        "    echo [ERROR] Python not found: %PYTHON_EXE%",
        "    pause",
        "    exit /b 1",
        ")",
        "",
        'cd /d "%APP_DIR%"',
        "",
        "echo ============================================",
        f"echo   BiliBot V{VERSION} Portable",
        "echo ============================================",
        "echo.",
        "echo   [1] GUI",
        "echo   [2] Web Panel  http://localhost:9527/panel/",
        "echo   [3] GUI + Web",
        "echo   [Q] Quit",
        "echo.",
        "set /p choice=Select: ",
        "",
        'if /i "%choice%"=="1" goto gui',
        'if /i "%choice%"=="2" goto web',
        'if /i "%choice%"=="3" goto both',
        'if /i "%choice%"=="q" goto end',
        "echo Invalid.",
        "pause",
        "goto end",
        "",
        ":gui",
        "echo.",
        "echo [*] Starting GUI...",
        '"%PYTHON_EXE%" gui.py',
        "pause",
        "goto end",
        "",
        ":web",
        "echo.",
        "echo [*] Starting Web Panel...",
        "echo [*] Open: http://localhost:9527/panel/",
        '"%PYTHON_EXE%" -m uvicorn web.app:app --host 0.0.0.0 --port 9527',
        "pause",
        "goto end",
        "",
        ":both",
        "echo.",
        "echo [*] Starting Web Panel in background...",
        'start "" /b cmd /c "cd /d %APP_DIR% ^& %PYTHON_EXE% -m uvicorn web.app:app --host 0.0.0.0 --port 9527"',
        "timeout /t 3 >nul",
        "echo [*] Web Panel: http://localhost:9527/panel/",
        "echo.",
        "echo [*] Starting GUI...",
        '"%PYTHON_EXE%" gui.py',
        "pause",
        "goto end",
        "",
        ":end",
    ]
    bat_content = "\r\n".join(lines) + "\r\n"
    bat_path = BUILD_DIR / "start.bat"
    bat_path.write_bytes(b"\xef\xbb\xbf" + bat_content.encode("utf-8"))
    log("Created start.bat (UTF-8 BOM)")

    readme_lines = [
        f"BiliBot V{VERSION} Portable",
        "=" * 40,
        "",
        "Usage:",
        "  1. Double-click start.bat",
        "  2. Select mode (GUI / Web / Both)",
        "  3. Set Chrome path in Settings on first run",
        "",
        "Notes:",
        "  - Requires Chrome or Edge browser (not included)",
        "  - Web Panel: http://localhost:9527/panel/",
        "  - Config file is auto-created on first run",
    ]
    readme_path = BUILD_DIR / "README.txt"
    readme_path.write_bytes(b"\xef\xbb\xbf" + "\r\n".join(readme_lines).encode("utf-8"))
    log("Created README.txt")


def create_zip():
    """Package everything into a zip."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_name = f"{APP_NAME}_Portable"
    zip_path = OUTPUT_DIR / f"{zip_name}.zip"

    if zip_path.exists():
        zip_path.unlink()

    log(f"Creating {zip_path.name}...")
    shutil.make_archive(
        str(OUTPUT_DIR / zip_name),
        "zip",
        root_dir=BUILD_DIR.parent,
        base_dir=BUILD_DIR.name,
    )

    final_zip = OUTPUT_DIR / f"{zip_name}.zip"
    size_mb = final_zip.stat().st_size / (1024 * 1024)
    log(f"Done! {final_zip} ({size_mb:.1f} MB)")
    return final_zip


def main():
    parser = argparse.ArgumentParser(description=f"Pack {APP_NAME} Portable")
    parser.add_argument("--skip-download", action="store_true", help="Skip Python download (use cache)")
    parser.add_argument("--no-zip", action="store_true", help="Skip final zip creation")
    args = parser.parse_args()

    step("Step 1/5: Download Python Embeddable")
    python_dir = download_python_embed(skip_download=args.skip_download)

    step("Step 2/5: Install pip")
    install_pip(python_dir)

    step("Step 3/5: Install Dependencies")
    install_dependencies(python_dir)

    step("Step 4/5: Copy Source & Frontend")
    copy_source()

    step("Step 5/5: Create Launcher")
    create_launcher()

    if not args.no_zip:
        step("Step 6: Package into ZIP")
        zip_path = create_zip()
        log(f"Pack complete! Output: {zip_path}")
    else:
        log(f"Build dir: {BUILD_DIR}")
        log("(--no-zip: skipped zip creation)")


if __name__ == "__main__":
    main()
