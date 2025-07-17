"""
Dependency Injection Container Async
Basato su: tiangolo/fastapi e aiomisc patterns
Ref: https://github.com/tiangolo/fastapi
"""
from typing import Any, Dict, Type, TypeVar, Protocol, Optional, Callable, Union
from abc import ABC, abstractmethod
import asyncio
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceProtocol(Protocol):
    """Base protocol per tutti i servizi"""
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class DIContainer:
    """
    Dependency Injection Container async-first con lifecycle management
    Pattern da aiomisc e FastAPI
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._is_started = False
    
    def register(
        self,
        name: str,
        factory: Callable,
        singleton: bool = True
    ) -> None:
        """
        Registra un servizio nel container
        
        Args:
            name: Nome del servizio
            factory: Factory function per creare il servizio
            singleton: Se True, crea una sola istanza
        """
        self._factories[name] = factory
        if singleton:
            self._singletons[name] = None
    
    async def resolve(self, name: str) -> Any:
        """
        Risolve e restituisce un servizio
        
        Args:
            name: Nome del servizio
            
        Returns:
            Istanza del servizio
        """
        # Se è un singleton già creato, restituiscilo
        if name in self._singletons and self._singletons[name] is not None:
            return self._singletons[name]
        
        # Se non c'è factory, errore
        if name not in self._factories:
            raise ValueError(f"Service '{name}' not registered")
        
        # Crea istanza
        factory = self._factories[name]
        instance = factory()
        
        # Se è un singleton, salvalo
        if name in self._singletons:
            self._singletons[name] = instance
        
        return instance
    
    async def start(self) -> None:
        """Avvia tutti i servizi registrati"""
        if self._is_started:
            return
        
        logger.info("Starting DI container services...")
        
        # Risolvi tutti i singleton
        for name in self._singletons:
            if self._singletons[name] is None:
                self._singletons[name] = await self.resolve(name)
        
        # Avvia servizi che implementano start()
        for name, service in self._singletons.items():
            if service and hasattr(service, 'start'):
                logger.info(f"Starting service: {name}")
                await service.start()
        
        self._is_started = True
        logger.info("All services started")
    
    async def stop(self) -> None:
        """Ferma tutti i servizi"""
        if not self._is_started:
            return
        
        logger.info("Stopping DI container services...")
        
        # Ferma in ordine inverso
        for name, service in reversed(list(self._singletons.items())):
            if service and hasattr(service, 'stop'):
                logger.info(f"Stopping service: {name}")
                try:
                    await service.stop()
                except Exception as e:
                    logger.error(f"Error stopping service {name}: {e}")
        
        self._is_started = False
        logger.info("All services stopped")
    
    def get_service(self, name: str) -> Any:
        """Get service sincrono (per compatibilità)"""
        if name in self._singletons and self._singletons[name] is not None:
            return self._singletons[name]
        
        if name not in self._factories:
            raise ValueError(f"Service '{name}' not registered")
        
        return self._factories[name]()


# Alias per compatibilità
ServiceContainer = DIContainer

# Global container
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get global container instance"""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


# Decoratore per dependency injection
def inject(container: DIContainer):
    """
    Decoratore per iniettare dipendenze
    
    Usage:
        @inject(container)
        async def my_handler(cache=Depends('cache'), db=Depends('db')):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Risolvi dipendenze
            for key, value in kwargs.items():
                if hasattr(value, '__name__') and value.__name__ == 'Depends':
                    service_name = value.args[0]
                    kwargs[key] = await container.resolve(service_name)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class Depends:
    """Marker per dipendenze da iniettare"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.__name__ = 'Depends'
        self.args = (service_name,)
