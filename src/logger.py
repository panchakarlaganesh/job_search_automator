import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name="job_search", log_file="logs/job_search.log", level=logging.INFO):
    """Function to setup as many loggers as you want"""
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()
