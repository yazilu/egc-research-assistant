import os

os.environ.setdefault('TZ', 'Asia/Shanghai')

from .get_logger import get_logger
logger = get_logger()
