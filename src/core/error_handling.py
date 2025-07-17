"""
Error handling e monitoring con Sentry
Basato su: getsentry/sentry-python
Ref: https://github.com/getsentry/sentry-python
"""
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
import logging
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Version for releases
VERSION = "1.0.0"

# Custom Exceptions
class ListingError(Exception):
    """Base exception for listing-related errors"""
    pass

class ValidationError(ListingError):
    """Raised when validation fails"""
    pass

class PublishError(ListingError):
    """Raised when publishing fails"""
    pass

class OptimizationError(ListingError):
    """Raised when AI optimization fails"""
    pass

class ErrorHandler:
    """Gestione centralizzata errori con Sentry"""
    
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn
        self._initialized = False
        
    def initialize(self, environment: str = "production"):
        """Inizializza Sentry con integrazioni"""
        if not self.dsn:
            logger.warning("Sentry DSN not provided, skipping initialization")
            return
            
        sentry_sdk.init(
            dsn=self.dsn,
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
                AsyncioIntegration()
            ],
            traces_sample_rate=1.0,
            environment=environment,
            release=f"dropush-listing@{VERSION}"
        )
        self._initialized = True
        
    def capture_exception(self, exc: Exception, context: Optional[Dict[str, Any]] = None):
        """Cattura eccezione con contesto custom"""
        if not self._initialized:
            logger.error(f"Exception captured but Sentry not initialized: {exc}")
            return
            
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
            
    def track_business_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Track business metrics in Sentry"""
        if not self._initialized:
            return
            
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("metric_type", "business")
            if tags:
                for k, v in tags.items():
                    scope.set_tag(k, v)
            sentry_sdk.capture_message(f"Business Metric: {metric_name}={value}", level="info")

def with_error_handling(func):
    """Decorator per gestione errori automatica"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_handler.capture_exception(e, {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            })
            raise
    return wrapper

# Global error handler
error_handler = ErrorHandler()
