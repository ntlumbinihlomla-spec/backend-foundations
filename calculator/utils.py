import datetime
import logging

logging.basicConfig(
    filename="logs/calculator.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_calculation(operation, a, b, result):
    logging.info(f"{operation} | {a} | {b} = {result}")

def current_time():
    return datetime.datetime.now().isoformat()
from datetime import datetime
from datetime import datetime

def show_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
from datetime import datetime

