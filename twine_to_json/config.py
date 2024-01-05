import io
from loguru import logger

log_stream = io.StringIO()
PATH_TWINE_FILES_DIR = 'twine'
PATH_JSON_FILES_DIR = 'json'

MAX_BUTTON_LEN = 127

logger.add(log_stream, level='WARNING', format='{level} {message}')
