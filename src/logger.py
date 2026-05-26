import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name="job_search", log_file="logs/job_search.log", level=logging.INFO):
    # Get project root
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_log_path = os.path.join(root, log_file)
    os.makedirs(os.path.dirname(full_log_path), exist_ok=True)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    file_handler = RotatingFileHandler(full_log_path, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()
