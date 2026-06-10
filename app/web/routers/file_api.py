"""Server-side file picker API — opens native file dialog on the host machine."""

from __future__ import annotations

import asyncio
import ctypes
import sys
from ctypes import c_wchar_p, c_wchar, create_unicode_buffer, byref, sizeof, wintypes
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class FilePickResult(BaseModel):
    path: Optional[str] = None


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("lpstrFilter", c_wchar_p),
        ("lpstrCustomFilter", c_wchar_p),
        ("nMaxCustFilter", wintypes.DWORD),
        ("nFilterIndex", wintypes.DWORD),
        ("lpstrFile", c_wchar_p),
        ("nMaxFile", wintypes.DWORD),
        ("lpstrFileTitle", c_wchar_p),
        ("nMaxFileTitle", wintypes.DWORD),
        ("lpstrInitialDir", c_wchar_p),
        ("lpstrTitle", c_wchar_p),
        ("Flags", wintypes.DWORD),
        ("nFileOffset", wintypes.WORD),
        ("nFileExtension", wintypes.WORD),
        ("lpstrDefExt", c_wchar_p),
        ("lCustData", wintypes.LPARAM),
        ("lpfnHook", wintypes.LPVOID),
        ("lpTemplateName", c_wchar_p),
        ("pvReserved", wintypes.LPVOID),
        ("dwReserved", wintypes.DWORD),
        ("FlagsEx", wintypes.DWORD),
    ]


OFN_FILEMUSTEXIST = 0x00001000
OFN_PATHMUSTEXIST = 0x00000800
OFN_NOCHANGEDIR = 0x00000008
OFN_EXPLORER = 0x00080000


def _pick_file_win32(title: str, filter_spec: str) -> Optional[str]:
    """Open a Windows native file dialog using comdlg32."""
    try:
        comdlg32 = ctypes.windll.comdlg32
        user32 = ctypes.windll.user32

        # 获取前台窗口作为父窗口
        hwnd_owner = user32.GetForegroundWindow()

        filename_buf = create_unicode_buffer(4096)

        ofn = OPENFILENAMEW()
        ofn.lStructSize = sizeof(OPENFILENAMEW)
        ofn.hwndOwner = hwnd_owner  # 设置父窗口
        ofn.lpstrFilter = filter_spec
        ofn.nFilterIndex = 1
        ofn.lpstrFile = ctypes.cast(filename_buf, c_wchar_p)
        ofn.nMaxFile = 4096
        ofn.lpstrTitle = title
        ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_EXPLORER

        # 尝试将对话框置于最前
        result = comdlg32.GetOpenFileNameW(byref(ofn))

        if result:
            return filename_buf.value if filename_buf.value else None
        return None
    except Exception as e:
        print(f"File dialog error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _pick_file_sync(title: str, extensions: list[tuple[str, str]]) -> Optional[str]:
    """Open a file dialog using Windows native API or tkinter fallback."""
    if sys.platform == "win32":
        # 尝试使用 Windows 原生对话框
        filter_parts = []
        for desc, ext in extensions:
            filter_parts.append(f"{desc}\x00{ext}\x00")
        filter_spec = "".join(filter_parts) + "\x00"

        result = _pick_file_win32(title, filter_spec)
        if result:
            return result

    # 备用方案：使用 tkinter
    try:
        import tkinter as tk
        from tkinter import filedialog

        # 创建隐藏的根窗口
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # 置顶

        # 构建文件类型过滤器
        filetypes = [(desc, ext) for desc, ext in extensions]

        # 打开文件对话框
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            parent=root
        )

        root.destroy()

        return file_path if file_path else None

    except Exception as e:
        print(f"Tkinter file dialog error: {e}")
        import traceback
        traceback.print_exc()
        return None


@router.post("/browse/executable", response_model=FilePickResult)
async def browse_executable():
    path = await asyncio.get_event_loop().run_in_executor(
        None, 
        _pick_file_sync, 
        "选择浏览器可执行文件",
        [("可执行文件", "*.exe"), ("所有文件", "*.*")]
    )
    return FilePickResult(path=path)


@router.post("/browse/image", response_model=FilePickResult)
async def browse_image():
    path = await asyncio.get_event_loop().run_in_executor(
        None, 
        _pick_file_sync, 
        "选择图片文件",
        [("图片文件", "*.jpg;*.jpeg;*.png;*.gif;*.webp"), ("所有文件", "*.*")]
    )
    return FilePickResult(path=path)
