"""
MiniLuma Web界面模块
提供基于浏览器的用户界面，允许通过Web访问MiniLuma的功能
"""
from ui.web.server import app, run_web_server

__all__ = ["app", "run_web_server"]
