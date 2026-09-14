import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger with a standard format.
    
    Format: %(asctime)s - %(name)s - %(levelname)s - %(message)s
    Output: Console (StreamHandler)
    """
    logger = logging.getLogger(name)
    
    # Only configure if handlers haven't been added yet to avoid duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        # Prevent propagation to root logger to avoid double logging if root is configured
        logger.propagate = False
        
    return logger
