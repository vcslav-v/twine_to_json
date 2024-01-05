"""Main module twine_to_json project."""
from loguru import logger
import io
from twine_to_json.schemas import Result
from twine_to_json.main import parse


__version__ = '0.1.0'
__author__ = 'Vaclav_V'
__all__ = ['parse', 'Result']


log_stream = io.StringIO()
PATH_TWINE_FILES_DIR = 'twine'
PATH_JSON_FILES_DIR = 'json'

MAX_BUTTON_LEN = 127

logger.add(log_stream, level='WARNING', format='{level} {message}')
