import sys
import os
from loguru import logger

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add("logs/bili_bot_{time:YYYY-MM-DD}.log", rotation="10 MB", retention="10 days", encoding="utf-8")

def get_logger():
    return logger
