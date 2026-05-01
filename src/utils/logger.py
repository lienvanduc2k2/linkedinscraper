from loguru import logger
import sys
import os

def setup_logger():
    logger.remove()
    
    # Console output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    
    # File output
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/scraper_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
    )
    
    return logger

log = setup_logger()
