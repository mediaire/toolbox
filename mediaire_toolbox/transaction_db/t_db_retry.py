from tenacity.retry import retry_if_exception_type
from tenacity import retry, stop_after_attempt, wait_fixed

from sqlite3 import OperationalError

from mediaire_toolbox.constants import (
    RETRY_DATABASE_OP_SECONDS,
    RETRY_DATABASE_OP_TIMES
)


"""
Database retry logic for the Transactions DB.
Retry up to a maximum amount of times, with a fixed wait period inbetween.
Retry only for certain exceptions that we know are problematic.
"""


def t_db_retry(f):
    return retry(retry=retry_if_exception_type(OperationalError),
                 stop=stop_after_attempt(RETRY_DATABASE_OP_TIMES),
                 wait=wait_fixed(RETRY_DATABASE_OP_SECONDS))(f)
