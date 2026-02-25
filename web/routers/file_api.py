"""Server-side file picker API — opens native file dialog on the host machine."""

from __future__ import annotations

import threading
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class FilePickResult(BaseModel):
    path: Optional[str] = None


def _pick_file(title: str, filetypes: list[tuple[str, str]]) -> Optional[str]:
    """Open a tkinter file dialog in a dedicated thread (must run on main-ish thread on Windows)."""
    result = [None]

    def _run():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(title=title, filetypes=filetypes)
            root.destroy()
            if path:
                result[0] = path
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=120)
    return result[0]


@router.post("/browse/executable", response_model=FilePickResult)
async def browse_executable():
    import asyncio
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(
        None, _pick_file, "选择浏览器可执行文件",
        [("Executable", "*.exe"), ("All files", "*.*")]
    )
    return FilePickResult(path=path)


@router.post("/browse/image", response_model=FilePickResult)
async def browse_image():
    import asyncio
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(
        None, _pick_file, "选择图片文件",
        [("Image", "*.jpg *.jpeg *.png *.gif *.webp"), ("All files", "*.*")]
    )
    return FilePickResult(path=path)
