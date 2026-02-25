"""WebSocket 路由。已移除 AI 中控台 /ws/session；Vue 面板日志使用 /ws/logs（见 log_api）。"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()
