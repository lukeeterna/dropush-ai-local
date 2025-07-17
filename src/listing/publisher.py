"""
Publisher system con Protocol pattern e retry
Basato su: FastAPI patterns e tenacity
"""
from typing import Protocol, Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
from src.core.retry_manager import RetryManager, retry_async

class PublishStatus(Enum):
    """Stati pubblicazione"""
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    SCHEDULED = "scheduled"

@dataclass
class PublishResult:
    """Risultato pubblicazione"""
    listing_id: str
    marketplace: str
    status: PublishStatus
    url: Optional[str] = None
    error: Optional[str] = None
    published_at: Optional[datetime] = None
    
class PublisherProtocol(Protocol):
    """Protocol per tutti i publisher"""
    
    async def validate_listing(self, listing: Dict[str, Any]) -> bool:
        """Valida listing prima di pubblicare"""
        ...
        
    async def publish(self, listing: Dict[str, Any]) -> PublishResult:
        """Pubblica listing su marketplace"""
        ...
        
    async def update(self, listing_id: str, updates: Dict[str, Any]) -> bool:
        """Aggiorna listing esistente"""
        ...
        
    async def delete(self, listing_id: str) -> bool:
        """Elimina listing"""
        ...

class BasePublisher(ABC):
    """Base class per publisher con funzionalità comuni"""
    
    def __init__(self, config: Dict[str, Any], retry_manager: Optional[RetryManager] = None):
        self.config = config
        self.retry_manager = retry_manager or RetryManager()
        self.marketplace_name = ""
        
    @abstractmethod
    async def validate_listing(self, listing: Dict[str, Any]) -> bool:
        """Implementazione specifica per marketplace"""
        pass
        
    @retry_async
    async def publish(self, listing: Dict[str, Any]) -> PublishResult:
        """Pubblica con retry automatico"""
        # Validate first
        if not await self.validate_listing(listing):
            return PublishResult(
                listing_id="",
                marketplace=self.marketplace_name,
                status=PublishStatus.FAILED,
                error="Validation failed"
            )
            
        # Publish
        return await self._do_publish(listing)
        
    @abstractmethod
    async def _do_publish(self, listing: Dict[str, Any]) -> PublishResult:
        """Implementazione specifica pubblicazione"""
        pass


class MultiPlatformPublisher:
    """
    Publisher che gestisce multiple piattaforme
    """
    
    def __init__(self, container=None):
        self.container = container
        self.platforms = {}
        self.retry_manager = RetryManager() if not container else container.resolve('retry_manager')
    
    def register_platform(self, name: str, publisher: PublisherProtocol):
        """Registra un publisher per una piattaforma"""
        self.platforms[name] = publisher
    
    async def publish(
        self,
        listing_data: Dict[str, Any],
        platforms: List[str] = None,
        retry_failed: bool = True
    ) -> List[PublishResult]:
        """
        Pubblica su multiple piattaforme
        
        Args:
            listing_data: Dati del listing
            platforms: Lista piattaforme (None = tutte)
            retry_failed: Se riprovare in caso di fallimento
            
        Returns:
            Lista di PublishResult
        """
        if platforms is None:
            platforms = list(self.platforms.keys())
        
        results = []
        
        for platform in platforms:
            if platform not in self.platforms:
                results.append(PublishResult(
                    listing_id="",
                    marketplace=platform,
                    status=PublishStatus.FAILED,
                    error=f"Platform {platform} not registered"
                ))
                continue
            
            publisher = self.platforms[platform]
            
            try:
                # Validate first
                if await publisher.validate_listing(listing_data):
                    # Publish with retry
                    if retry_failed:
                        result = await self.retry_manager.execute_with_retry(
                            publisher.publish,
                            listing_data
                        )
                    else:
                        result = await publisher.publish(listing_data)
                    
                    results.append(result)
                else:
                    results.append(PublishResult(
                        listing_id="",
                        marketplace=platform,
                        status=PublishStatus.FAILED,
                        error="Validation failed"
                    ))
                    
            except Exception as e:
                results.append(PublishResult(
                    listing_id="",
                    marketplace=platform,
                    status=PublishStatus.FAILED,
                    error=str(e)
                ))
        
        return results
    
    async def update_listing(
        self,
        platform: str,
        listing_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Aggiorna listing su una piattaforma"""
        if platform not in self.platforms:
            raise ValueError(f"Platform {platform} not registered")
        
        return await self.platforms[platform].update(listing_id, updates)
