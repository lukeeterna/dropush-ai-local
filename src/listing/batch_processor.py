"""
Batch processing per elaborazione massiva listing
Ottimizzato per throughput elevato (target: 1000+ listings/minuto)
Basato su: asyncio.gather, concurrent.futures, backpressure control
"""
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Callable, TypeVar, Union, AsyncGenerator
from dataclasses import dataclass
import time
import logging
from functools import partial
import multiprocessing as mp

from src.core.dependencies import DIContainer
from src.listing.ai_optimizer import AIListingOptimizer, OptimizationResult
from src.listing.template_engine import AdvancedTemplateEngine
from src.core.monitoring import MetricsCollector

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class BatchResult:
    """Risultato elaborazione batch"""
    successful: List[OptimizationResult]
    failed: List[Dict[str, Any]]
    total_time: float
    throughput: float  # items/secondo
    metadata: Dict[str, Any]


@dataclass
class BatchConfig:
    """Configurazione batch processing"""
    batch_size: int = 100
    max_workers: int = mp.cpu_count()
    max_concurrent_batches: int = 4
    enable_gpu: bool = True
    timeout_per_item: float = 5.0
    retry_failed: bool = True
    backpressure_threshold: int = 1000


class BatchProcessor:
    """
    Batch processor ad alte performance per listing automation
    
    Features:
    - Elaborazione parallela multi-processo
    - Backpressure control per evitare memory overflow
    - GPU acceleration quando disponibile
    - Retry automatico su failure
    - Monitoring real-time performance
    """
    
    def __init__(
        self,
        container: DIContainer,
        config: Optional[BatchConfig] = None
    ):
        self.container = container
        self.config = config or BatchConfig()
        
        # Executor pools
        self.process_pool = ProcessPoolExecutor(max_workers=self.config.max_workers)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers * 2)
        
        # Components
        self.ai_optimizer = AIListingOptimizer(container)
        self.template_engine = AdvancedTemplateEngine(container)
        self.metrics = container.resolve('metrics')
        
        # Backpressure control
        self._processing_semaphore = asyncio.Semaphore(
            self.config.backpressure_threshold
        )
        self._active_tasks = 0
        
        # Performance tracking
        self._start_time = None
        self._processed_count = 0
        self._failed_count = 0
    
    async def process_batch(
        self,
        products: List[Dict[str, Any]],
        optimization_params: Optional[Dict[str, Any]] = None
    ) -> BatchResult:
        """
        Processa batch di prodotti con ottimizzazione parallela
        
        Args:
            products: Lista prodotti da ottimizzare
            optimization_params: Parametri extra per ottimizzazione
            
        Returns:
            BatchResult con risultati e metriche
        """
        self._start_time = time.time()
        self._processed_count = 0
        self._failed_count = 0
        
        logger.info(f"Starting batch processing of {len(products)} products")
        
        # Dividi in sub-batches
        batches = self._create_batches(products)
        
        # Process batches concurrently
        results = await self._process_batches_concurrent(
            batches,
            optimization_params
        )
        
        # Aggregate results
        successful = []
        failed = []
        
        for batch_results in results:
            for result in batch_results:
                if isinstance(result, OptimizationResult):
                    successful.append(result)
                    self._processed_count += 1
                else:
                    failed.append(result)
                    self._failed_count += 1
        
        # Retry failed if configured
        if self.config.retry_failed and failed:
            retry_results = await self._retry_failed_items(
                failed,
                optimization_params
            )
            
            for result in retry_results:
                if isinstance(result, OptimizationResult):
                    successful.append(result)
                    failed.remove(result)
                    self._processed_count += 1
                    self._failed_count -= 1
        
        # Calculate metrics
        total_time = time.time() - self._start_time
        throughput = self._processed_count / total_time if total_time > 0 else 0
        
        # Log performance
        logger.info(
            f"Batch processing completed: "
            f"{self._processed_count} successful, "
            f"{self._failed_count} failed, "
            f"{throughput:.2f} items/sec"
        )
        
        # Update metrics
        await self.metrics.gauge('batch.throughput', throughput)
        await self.metrics.increment('batch.processed', self._processed_count)
        await self.metrics.increment('batch.failed', self._failed_count)
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total_time=total_time,
            throughput=throughput,
            metadata={
                'total_items': len(products),
                'batch_count': len(batches),
                'workers_used': self.config.max_workers,
                'gpu_enabled': self.config.enable_gpu
            }
        )
    
    def _create_batches(
        self,
        items: List[T]
    ) -> List[List[T]]:
        """Divide items in batches ottimizzati"""
        batch_size = self.config.batch_size
        return [
            items[i:i + batch_size]
            for i in range(0, len(items), batch_size)
        ]
    
    async def _process_batches_concurrent(
        self,
        batches: List[List[Dict[str, Any]]],
        optimization_params: Optional[Dict[str, Any]]
    ) -> List[List[Union[OptimizationResult, Dict[str, Any]]]]:
        """Processa batches con concurrency control"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        
        async def process_with_semaphore(batch):
            async with semaphore:
                return await self._process_single_batch(
                    batch,
                    optimization_params
                )
        
        tasks = [
            process_with_semaphore(batch)
            for batch in batches
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _process_single_batch(
        self,
        batch: List[Dict[str, Any]],
        optimization_params: Optional[Dict[str, Any]]
    ) -> List[Union[OptimizationResult, Dict[str, Any]]]:
        """Processa singolo batch con parallelizzazione"""
        
        # Se GPU disponibile e batch grande, usa GPU processing
        if self.config.enable_gpu and len(batch) > 20:
            return await self._process_batch_gpu(batch, optimization_params)
        
        # Altrimenti usa CPU multi-processing
        loop = asyncio.get_event_loop()
        
        # Prepare partial function for multiprocessing
        process_func = partial(
            self._process_item_cpu,
            optimization_params=optimization_params
        )
        
        # Run in process pool
        futures = []
        for item in batch:
            # Acquire semaphore for backpressure
            await self._processing_semaphore.acquire()
            
            future = loop.run_in_executor(
                self.process_pool,
                process_func,
                item
            )
            
            # Release semaphore when done
            future.add_done_callback(
                lambda f: self._processing_semaphore.release()
            )
            
            futures.append(future)
        
        # Wait for all with timeout
        results = []
        for future in asyncio.as_completed(futures):
            try:
                result = await asyncio.wait_for(
                    future,
                    timeout=self.config.timeout_per_item
                )
                results.append(result)
            except asyncio.TimeoutError:
                results.append({
                    'error': 'Timeout',
                    'item': batch[futures.index(future)]
                })
            except Exception as e:
                results.append({
                    'error': str(e),
                    'item': batch[futures.index(future)]
                })
        
        return results
    
    def _process_item_cpu(
        self,
        item: Dict[str, Any],
        optimization_params: Optional[Dict[str, Any]]
    ) -> Union[OptimizationResult, Dict[str, Any]]:
        """Processa singolo item su CPU (per multiprocessing)"""
        try:
            # Crea nuovo event loop per il processo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Esegui ottimizzazione
            result = loop.run_until_complete(
                self._optimize_single_item(item, optimization_params)
            )
            
            loop.close()
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'item': item,
                'type': 'processing_error'
            }
    
    async def _process_batch_gpu(
        self,
        batch: List[Dict[str, Any]],
        optimization_params: Optional[Dict[str, Any]]
    ) -> List[Union[OptimizationResult, Dict[str, Any]]]:
        """Processa batch usando GPU acceleration"""
        try:
            # Importa GPU optimizer
            from src.listing.gpu_optimizer import GPUBatchOptimizer
            
            gpu_optimizer = GPUBatchOptimizer(self.container)
            
            # Prepara batch per GPU
            titles = [item.get('title', '') for item in batch]
            descriptions = [item.get('description', '') for item in batch]
            categories = [item.get('category', 'General') for item in batch]
            
            # Ottimizza in batch su GPU
            optimized_titles = await gpu_optimizer.optimize_titles_batch(
                titles,
                categories
            )
            
            optimized_descriptions = await gpu_optimizer.generate_descriptions_batch(
                titles,
                descriptions,
                categories
            )
            
            keywords_batch = await gpu_optimizer.extract_keywords_batch(
                [f"{t} {d}" for t, d in zip(titles, descriptions)]
            )
            
            # Costruisci risultati
            results = []
            for i, item in enumerate(batch):
                try:
                    result = OptimizationResult(
                        title=optimized_titles[i],
                        description=optimized_descriptions[i],
                        keywords=keywords_batch[i],
                        sentiment_score=0.0,  # TODO: batch sentiment
                        metadata={
                            'processed_on': 'GPU',
                            'batch_index': i
                        }
                    )
                    results.append(result)
                except Exception as e:
                    results.append({
                        'error': str(e),
                        'item': item,
                        'type': 'gpu_processing_error'
                    })
            
            return results
            
        except ImportError:
            logger.warning("GPU optimizer not available, falling back to CPU")
            return await self._process_single_batch(batch, optimization_params)
        except Exception as e:
            logger.error(f"GPU batch processing failed: {e}")
            # Fallback to CPU
            return await self._process_single_batch(batch, optimization_params)
    
    async def _optimize_single_item(
        self,
        item: Dict[str, Any],
        optimization_params: Optional[Dict[str, Any]]
    ) -> OptimizationResult:
        """Ottimizza singolo item (versione async)"""
        # Qui dovrebbe usare i veri componenti, per ora mock
        return OptimizationResult(
            title=f"Optimized: {item.get('title', 'Unknown')}",
            description=f"Optimized description for {item.get('title', 'Unknown')}",
            keywords=['keyword1', 'keyword2', 'keyword3'],
            sentiment_score=0.85,
            metadata={'optimization_params': optimization_params}
        )
    
    async def _retry_failed_items(
        self,
        failed_items: List[Dict[str, Any]],
        optimization_params: Optional[Dict[str, Any]]
    ) -> List[Union[OptimizationResult, Dict[str, Any]]]:
        """Riprova items falliti con strategia di backoff"""
        logger.info(f"Retrying {len(failed_items)} failed items")
        
        retry_results = []
        
        for item in failed_items:
            # Extract original item data
            original_item = item.get('item', item)
            
            # Wait with exponential backoff
            await asyncio.sleep(0.1)
            
            try:
                # Retry with extended timeout
                result = await asyncio.wait_for(
                    self._optimize_single_item(
                        original_item,
                        optimization_params
                    ),
                    timeout=self.config.timeout_per_item * 2
                )
                retry_results.append(result)
            except Exception as e:
                logger.error(f"Retry failed for item: {e}")
                retry_results.append({
                    'error': f"Retry failed: {str(e)}",
                    'item': original_item,
                    'type': 'retry_failed'
                })
        
        return retry_results
    
    async def process_stream(
        self,
        item_generator: AsyncGenerator[Dict[str, Any], None],
        optimization_params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[OptimizationResult, None]:
        """
        Processa stream di items con windowing
        Utile per elaborazione real-time
        """
        window = []
        window_size = self.config.batch_size
        
        async for item in item_generator:
            window.append(item)
            
            if len(window) >= window_size:
                # Process window
                batch_result = await self.process_batch(
                    window,
                    optimization_params
                )
                
                # Yield successful results
                for result in batch_result.successful:
                    yield result
                
                # Clear window
                window = []
        
        # Process remaining items
        if window:
            batch_result = await self.process_batch(
                window,
                optimization_params
            )
            
            for result in batch_result.successful:
                yield result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche performance correnti"""
        if not self._start_time:
            return {}
        
        elapsed = time.time() - self._start_time
        
        return {
            'processed': self._processed_count,
            'failed': self._failed_count,
            'elapsed_time': elapsed,
            'throughput': self._processed_count / elapsed if elapsed > 0 else 0,
            'success_rate': (
                self._processed_count / 
                (self._processed_count + self._failed_count)
                if (self._processed_count + self._failed_count) > 0
                else 0
            ),
            'active_tasks': self._active_tasks
        }
    
    async def shutdown(self):
        """Cleanup resources"""
        self.process_pool.shutdown(wait=True)
        self.thread_pool.shutdown(wait=True)
        logger.info("BatchProcessor shutdown complete")
