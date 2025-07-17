"""
Monitoring e metriche con Prometheus
Basato su: prometheus/client_python
Ref: https://github.com/prometheus/client_python
"""
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    start_http_server, generate_latest
)
import time
from functools import wraps
from typing import Callable, Any
import asyncio

# Define metrics
listing_created_total = Counter(
    'listing_created_total',
    'Total number of listings created',
    ['marketplace', 'category', 'status']
)

listing_creation_duration = Histogram(
    'listing_creation_duration_seconds',
    'Time spent creating listings',
    ['marketplace', 'step'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

active_listings = Gauge(
    'active_listings',
    'Number of active listings',
    ['marketplace', 'store']
)

api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Cache hit rate',
    ['cache_type', 'hit']
)

ai_model_predictions = Summary(
    'ai_model_predictions',
    'AI model prediction times',
    ['model', 'operation']
)

business_metrics = Gauge(
    'business_metrics',
    'Business KPIs',
    ['metric_name']
)

class MetricsCollector:
    """Collector centralizzato per metriche"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self._server_started = False
        
    def start_server(self):
        """Avvia server metriche Prometheus"""
        if not self._server_started:
            start_http_server(self.port)
            self._server_started = True
            
    @staticmethod
    def track_listing_creation(marketplace: str, category: str):
        """Decorator per tracking creazione listing"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "failed"
                    raise
                finally:
                    # Record metrics
                    listing_created_total.labels(
                        marketplace=marketplace,
                        category=category,
                        status=status
                    ).inc()
                    
                    listing_creation_duration.labels(
                        marketplace=marketplace,
                        step="total"
                    ).observe(time.time() - start_time)
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "failed"
                    raise
                finally:
                    listing_created_total.labels(
                        marketplace=marketplace,
                        category=category,
                        status=status
                    ).inc()
                    
                    listing_creation_duration.labels(
                        marketplace=marketplace,
                        step="total"
                    ).observe(time.time() - start_time)
                    
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
        
    @staticmethod
    def track_api_request(endpoint: str, method: str):
        """Decorator per tracking API requests"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                status = "success"
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    api_requests_total.labels(
                        endpoint=endpoint,
                        method=method,
                        status=status
                    ).inc()
            return wrapper
        return decorator
        
    @staticmethod
    def track_cache(cache_type: str):
        """Track cache hits/misses"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Assuming function returns (value, hit)
                result, hit = await func(*args, **kwargs)
                
                cache_hits_total.labels(
                    cache_type=cache_type,
                    hit="hit" if hit else "miss"
                ).inc()
                
                return result
            return wrapper
        return decorator
        
    @staticmethod
    def track_business_metric(metric_name: str, value: float):
        """Track business KPI"""
        business_metrics.labels(metric_name=metric_name).set(value)
        
    @staticmethod
    def track_ai_operation(model: str, operation: str):
        """Track AI model operations"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with ai_model_predictions.labels(
                    model=model,
                    operation=operation
                ).time():
                    return await func(*args, **kwargs)
            return wrapper
        return decorator

# Global metrics collector
metrics = MetricsCollector()
