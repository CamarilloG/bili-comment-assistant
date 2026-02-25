import sys
import os
import re
from loguru import logger

if not os.path.exists("logs"):
    os.makedirs("logs")

def sanitize_log(record):
    message = record["message"]
    
    message = re.sub(r'SESSDATA=[^;]+', 'SESSDATA=***', message)
    message = re.sub(r'bili_jct=[^;]+', 'bili_jct=***', message)
    message = re.sub(r'DedeUserID=[^;]+', 'DedeUserID=***', message)
    message = re.sub(r'"password"\s*:\s*"[^"]+"', '"password": "***"', message)
    message = re.sub(r'"token"\s*:\s*"[^"]+"', '"token": "***"', message)
    message = re.sub(r'(sk-)[a-zA-Z0-9]{4}[a-zA-Z0-9]+', r'\g<1>****', message)
    message = re.sub(r'api_key["\s:=]+["\']?[a-zA-Z0-9_-]{8,}["\']?', 'api_key=***', message)
    
    record["message"] = message
    return True

logger.remove()
if sys.stderr:
    logger.add(
        sys.stderr, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        filter=sanitize_log
    )
logger.add(
    "logs/bili_bot_{time:YYYY-MM-DD}.log", 
    rotation="10 MB", 
    retention="10 days", 
    encoding="utf-8",
    filter=sanitize_log
)

def get_logger():
    return logger
