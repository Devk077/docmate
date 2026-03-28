import logging
from datetime import datetime

import pytz


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, timezone=None):
        super().__init__(fmt, datefmt)
        self.timezone = timezone

    def formatTime(self, record, datefmt=None):
        # Convert the created time to a datetime object
        dt = datetime.fromtimestamp(record.created, tz=pytz.utc)
        # Convert the datetime object to the desired timezone
        if self.timezone:
            dt = dt.astimezone(self.timezone)
        # Format the datetime object as a string
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.isoformat()
        return s


def setup_logger(
    log_file="logfile.log", level=logging.INFO, timezone_str="Asia/Kolkata"
):
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Check if handlers are already configured to avoid duplicates
    # This is important in Streamlit which reruns the script on each interaction
    if logger.handlers:
        return logger

    # Create a file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Set the timezone
    timezone = pytz.timezone(timezone_str)

    # Create a formatter and set it for both handlers
    formatter = CustomFormatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
        timezone=timezone,
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Example usage
if __name__ == "__main__":
    logger = setup_logger()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
