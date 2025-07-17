"""
Queue manager per pubblicazioni asincrone
Basato su: asyncio patterns e priority queue
"""
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import heapq
from enum import Enum
from src.listing.publisher import PublishResult, PublishStatus

class Priority(Enum):
    """Priorità pubblicazione"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0

@dataclass(order=True)
class QueueItem:
    """Item in coda con priorità"""
    priority: int
    scheduled_at: datetime = field(compare=False)
    listing: Dict[str, Any] = field(compare=False)
    marketplace: str = field(compare=False)
    retries: int = field(default=0, compare=False)

class PublishingQueue:
    """
    Coda pubblicazioni con priorità e scheduling
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.queue: List[QueueItem] = []
        self.max_concurrent = max_concurrent
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, PublishResult] = {}
        self._running = False
        self._publishers: Dict[str, Any] = {}
        
    def register_publisher(self, marketplace: str, publisher: Any):
        """Registra publisher per marketplace"""
        self._publishers[marketplace] = publisher
        
    async def add_to_queue(
        self,
        listing: Dict[str, Any],
        marketplace: str,
        priority: Priority = Priority.NORMAL,
        scheduled_at: Optional[datetime] = None
    ) -> str:
        """Aggiungi listing alla coda"""
        item = QueueItem(
            priority=priority.value,
            scheduled_at=scheduled_at or datetime.now(),
            listing=listing,
            marketplace=marketplace
        )
        
        # Generate queue ID
        queue_id = f"{marketplace}_{datetime.now().timestamp()}"
        
        # Add to priority queue
        heapq.heappush(self.queue, item)
        
        # Start processing if not running
        if not self._running:
            asyncio.create_task(self._process_queue())
            
        return queue_id
        
    async def _process_queue(self):
        """Processa coda con concorrenza limitata"""
        self._running = True
        
        while self.queue or self.active_tasks:
            # Check for scheduled items ready to process
            now = datetime.now()
            
            # Start new tasks if under limit
            while self.queue and len(self.active_tasks) < self.max_concurrent:
                # Peek at next item
                if self.queue[0].scheduled_at <= now:
                    item = heapq.heappop(self.queue)
                    task_id = f"{item.marketplace}_{id(item)}"
                    
                    # Create publish task
                    task = asyncio.create_task(
                        self._publish_item(item)
                    )
                    self.active_tasks[task_id] = task
                    
                    # Add callback to clean up
                    task.add_done_callback(
                        lambda t, tid=task_id: self.active_tasks.pop(tid, None)
                    )
                else:
                    # Wait until next scheduled item
                    wait_time = (self.queue[0].scheduled_at - now).total_seconds()
                    await asyncio.sleep(min(wait_time, 1))
                    
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
            
        self._running = False
        
    async def _publish_item(self, item: QueueItem) -> PublishResult:
        """Pubblica singolo item con gestione errori"""
        publisher = self._get_publisher(item.marketplace)
        
        if not publisher:
            return PublishResult(
                listing_id="",
                marketplace=item.marketplace,
                status=PublishStatus.FAILED,
                error=f"No publisher registered for {item.marketplace}"
            )
        
        try:
            result = await publisher.publish(item.listing)
            self.results[id(item)] = result
            return result
            
        except Exception as e:
            # Handle retry
            if item.retries < 3:
                item.retries += 1
                # Schedule retry with exponential backoff
                from datetime import timedelta
                item.scheduled_at = datetime.now() + timedelta(minutes=5 * item.retries)
                heapq.heappush(self.queue, item)
                
            return PublishResult(
                listing_id="",
                marketplace=item.marketplace,
                status=PublishStatus.FAILED,
                error=str(e)
            )
            
    def _get_publisher(self, marketplace: str):
        """Ottieni publisher per marketplace"""
        return self._publishers.get(marketplace)
        
    async def get_status(self) -> Dict[str, Any]:
        """Ottieni stato coda"""
        return {
            "queue_size": len(self.queue),
            "active_tasks": len(self.active_tasks),
            "results_count": len(self.results),
            "is_running": self._running,
            "max_concurrent": self.max_concurrent
        }
        
    async def get_results(self, limit: int = 100) -> List[PublishResult]:
        """Ottieni ultimi risultati"""
        # Return last N results
        results_list = list(self.results.values())
        return results_list[-limit:]
        
    async def clear_queue(self):
        """Svuota coda"""
        self.queue.clear()
        
    async def pause(self):
        """Pausa processamento"""
        self._running = False
        
    async def resume(self):
        """Riprendi processamento"""
        if not self._running and self.queue:
            asyncio.create_task(self._process_queue())
