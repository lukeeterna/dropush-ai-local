"""
Retry management con Tenacity
Basato su: jd/tenacity v8.2.0+
Ref: https://github.com/jd/tenacity
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_log,
    after_log,
    before_sleep_log
)
import logging
from typing import Type, Tuple, Optional
from requests.exceptions import HTTPError, ConnectionError, Timeout

logger = logging.getLogger(__name__)

# Custom exceptions
class APIException(Exception):
    """Base exception for API errors"""
    pass

class OperationalError(Exception):
    """Database operational error"""
    pass

class InterfaceError(Exception):
    """Database interface error"""
    pass

class DatabaseError(Exception):
    """General database error"""
    pass

class RetryManager:
    """Manager centralizzato per retry policies"""
    
    @staticmethod
    def standard_retry(
        max_attempts: int = 5,
        wait_min: int = 1,
        wait_max: int = 60,
        exceptions: Tuple[Type[Exception], ...] = (ConnectionError, Timeout)
    ):
        """Standard retry con exponential backoff"""
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            before=before_log(logger, logging.DEBUG),
            after=after_log(logger, logging.DEBUG),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
    
    @staticmethod
    def api_retry():
        """Retry specifico per API calls"""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_fixed(2),
            retry=retry_if_exception_type((
                ConnectionError,
                Timeout,
                HTTPError,
                APIException
            )),
            reraise=True
        )
    
    @staticmethod
    def database_retry():
        """Retry per operazioni database"""
        return retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
            retry=retry_if_exception_type((
                OperationalError,
                InterfaceError,
                DatabaseError
            ))
        )

# Decorators pronti all'uso
retry_async = RetryManager.standard_retry()
retry_api = RetryManager.api_retry()
retry_db = RetryManager.database_retry()
