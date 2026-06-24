# logging_config.py
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Set up logging configuration for the entire application.
    This function should be called once at the start of your app.
    """
    
    # Get environment from environment variable
    env = os.getenv("ENVIRONMENT", "development")
    
    # Determine log levels based on environment
    if env == "production":
        root_level = logging.WARNING
        console_level = logging.WARNING
        file_level = logging.WARNING
    else:
        root_level = logging.DEBUG
        console_level = logging.DEBUG
        file_level = logging.INFO
    
    # Create formatter (the stamp that adds time, name, level to each log)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler 1: Console (terminal) - shows DEBUG and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    
    # Handler 2: File (with rotation) - shows INFO and above
    # Creates app.log, and rotates when it reaches 10 MB
    file_handler = RotatingFileHandler(
        'app.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5           # Keep 5 backup files
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    
    # Get the root logger (CEO) - sets minimum  level for ALL loggers
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log that logging is set up (optional)
    root_logger.info(f"Logging configured for {env} environment")
    
    return root_logger