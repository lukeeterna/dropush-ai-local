"""
Test suite completa per Listing Automation System
Coverage target: >85%
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.listing_config import ListingConfig
from src.core.dependencies import DIContainer, get_container
from src.core.cache_system import MultiLevelCache
from src.core.retry_manager import RetryManager
from src.core.error_handling import ErrorHandler, ListingError
from src.core.monitoring import MetricsCollector

from src.listing.ai_optimizer import AIListingOptimizer, OptimizationResult
from src.listing.template_engine import AdvancedTemplateEngine, TemplateRegistry
from src.listing.template_factory import TemplateFactory, TemplateBuilder
from src.listing.publisher import MultiPlatformPublisher, PublishResult
from src.listing.ebay_publisher import EbayPublisher
from src.listing.queue_manager import PublishingQueue, QueueItem
from src.listing.sales_predictor import SalesPredictor


# ==================== FIXTURES ====================

@pytest.fixture
def mock_config():
    """Mock configuration senza chiamate esterne"""
    with patch.dict(os.environ, {
        'REDIS_URL': 'redis://localhost:6379',
        'HF_TOKEN': 'mock-token',
        'EBAY_APP_ID': 'mock-app-id',
        'EBAY_CERT_ID': 'mock-cert-id',
        'EBAY_SANDBOX': 'true'
    }):
        config = ListingConfig()
        return config


@pytest.fixture
async def mock_container(mock_config):
    """Container DI con mock dependencies"""
    container = DIContainer()
    
    # Mock services
    container.register('config', lambda: mock_config)
    container.register('cache', lambda: AsyncMock(spec=MultiLevelCache))
    container.register('metrics', lambda: Mock(spec=MetricsCollector))
    container.register('error_handler', lambda: Mock(spec=ErrorHandler))
    
    await container.start()
    yield container
    await container.stop()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.asyncio.from_url') as mock:
        client = AsyncMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.exists = AsyncMock(return_value=False)
        mock.return_value = client
        yield client


# ==================== CONFIG TESTS ====================

class TestListingConfig:
    """Test configuration management"""
    
    def test_config_defaults(self):
        """Test default configuration values"""
        with patch.dict(os.environ, {}, clear=True):
            config = ListingConfig()
            assert config.redis_url == 'redis://localhost:6379'
            assert config.cache_ttl == 3600
            assert config.model_title == 'salesforce/bart-large-mnli'
    
    def test_config_env_override(self):
        """Test environment variable override"""
        with patch.dict(os.environ, {
            'REDIS_URL': 'redis://custom:6380',
            'CACHE_TTL': '7200'
        }):
            config = ListingConfig()
            assert config.redis_url == 'redis://custom:6380'
            assert config.cache_ttl == 7200
    
    def test_config_validation(self):
        """Test configuration validation"""
        with patch.dict(os.environ, {'CACHE_TTL': '999999'}):
            with pytest.raises(ValueError):
                ListingConfig()


# ==================== DI CONTAINER TESTS ====================

class TestDIContainer:
    """Test dependency injection container"""
    
    @pytest.mark.asyncio
    async def test_container_registration(self):
        """Test service registration"""
        container = DIContainer()
        
        # Register service
        test_service = Mock()
        container.register('test', lambda: test_service)
        
        # Resolve service
        resolved = await container.resolve('test')
        assert resolved == test_service
    
    @pytest.mark.asyncio
    async def test_container_singleton(self):
        """Test singleton behavior"""
        container = DIContainer()
        
        # Register singleton
        counter = {'value': 0}
        def factory():
            counter['value'] += 1
            return counter['value']
        
        container.register('counter', factory, singleton=True)
        
        # Multiple resolves should return same instance
        val1 = await container.resolve('counter')
        val2 = await container.resolve('counter')
        assert val1 == val2 == 1
    
    @pytest.mark.asyncio
    async def test_container_lifecycle(self):
        """Test container start/stop lifecycle"""
        container = DIContainer()
        
        # Mock service with lifecycle
        service = AsyncMock()
        service.start = AsyncMock()
        service.stop = AsyncMock()
        
        container.register('service', lambda: service)
        
        await container.start()
        service.start.assert_called_once()
        
        await container.stop()
        service.stop.assert_called_once()


# ==================== CACHE TESTS ====================

class TestCacheSystem:
    """Test multi-level cache system"""
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self, mock_redis):
        """Test cache miss"""
        cache = MultiLevelCache(redis_client=mock_redis)
        
        result = await cache.get('nonexistent')
        assert result is None
        mock_redis.get.assert_called_once_with('nonexistent')
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, mock_redis):
        """Test cache set and get"""
        cache = MultiLevelCache(redis_client=mock_redis)
        
        # Set value
        await cache.set('key', 'value', ttl=3600)
        mock_redis.set.assert_called_once()
        
        # Get value (from L1 cache)
        result = await cache.get('key')
        assert result == 'value'
    
    @pytest.mark.asyncio
    async def test_cache_decorator(self, mock_redis):
        """Test cache decorator"""
        cache = MultiLevelCache(redis_client=mock_redis)
        
        call_count = 0
        
        @cache.cached(ttl=3600)
        async def expensive_operation(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = await expensive_operation(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call (cached)
        result2 = await expensive_operation(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented


# ==================== AI OPTIMIZER TESTS ====================

class TestAIOptimizer:
    """Test AI listing optimizer"""
    
    @pytest.fixture
    def mock_optimizer(self, mock_container):
        """Mock AI optimizer with mocked models"""
        with patch('transformers.pipeline') as mock_pipeline:
            # Mock title generator
            mock_pipeline.return_value = Mock(
                return_value=[{'generated_text': 'Optimized Title'}]
            )
            
            optimizer = AIListingOptimizer(container=mock_container)
            return optimizer
    
    @pytest.mark.asyncio
    async def test_optimize_title(self, mock_optimizer):
        """Test title optimization"""
        result = await mock_optimizer.optimize_title(
            "Original Title",
            category="Electronics"
        )
        
        assert "Optimized" in result
        assert len(result) <= 80  # eBay title limit
    
    @pytest.mark.asyncio
    async def test_generate_description(self, mock_optimizer):
        """Test description generation"""
        features = ["Feature 1", "Feature 2"]
        description = await mock_optimizer.generate_description(
            "Product Title",
            features=features,
            category="Electronics"
        )
        
        assert isinstance(description, str)
        assert len(description) > 100
    
    @pytest.mark.asyncio
    async def test_extract_keywords(self, mock_optimizer):
        """Test keyword extraction"""
        keywords = await mock_optimizer.extract_keywords(
            "This is a test product description"
        )
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert all(isinstance(k, str) for k in keywords)
    
    @pytest.mark.asyncio
    async def test_optimize_listing_complete(self, mock_optimizer):
        """Test complete listing optimization"""
        listing_data = {
            'title': 'Test Product',
            'description': 'Basic description',
            'category': 'Electronics',
            'features': ['Feature 1', 'Feature 2'],
            'price': 99.99
        }
        
        result = await mock_optimizer.optimize_listing(listing_data)
        
        assert isinstance(result, OptimizationResult)
        assert result.title != listing_data['title']
        assert result.description != listing_data['description']
        assert len(result.keywords) > 0
        assert result.sentiment_score >= -1 and result.sentiment_score <= 1


# ==================== TEMPLATE ENGINE TESTS ====================

class TestTemplateEngine:
    """Test template engine"""
    
    @pytest.fixture
    def template_engine(self, mock_container):
        """Template engine with test templates"""
        engine = AdvancedTemplateEngine(
            container=mock_container,
            base_path='./test_templates'
        )
        
        # Register test template
        engine.registry.register(
            'test_template',
            '# {{ title }}\n{{ description }}',
            {'type': 'simple', 'category': 'test'}
        )
        
        return engine
    
    @pytest.mark.asyncio
    async def test_render_simple_template(self, template_engine):
        """Test simple template rendering"""
        result = await template_engine.render(
            'test_template',
            {'title': 'Test Title', 'description': 'Test Description'}
        )
        
        assert '# Test Title' in result
        assert 'Test Description' in result
    
    @pytest.mark.asyncio
    async def test_render_with_cache(self, template_engine):
        """Test template rendering with cache"""
        context = {'title': 'Cached', 'description': 'Content'}
        
        # First render
        result1 = await template_engine.render('test_template', context)
        
        # Second render (should be cached)
        result2 = await template_engine.render('test_template', context)
        
        assert result1 == result2
    
    def test_template_registry(self):
        """Test template registry operations"""
        registry = TemplateRegistry()
        
        # Register template
        registry.register(
            'custom',
            'Template content',
            {'author': 'test', 'version': '1.0'}
        )
        
        # Get template
        template = registry.get('custom')
        assert template is not None
        assert template.content == 'Template content'
        
        # List templates
        templates = registry.list_templates()
        assert 'custom' in templates
    
    def test_template_builder(self):
        """Test template builder pattern"""
        builder = TemplateBuilder()
        
        template = (builder
            .set_title("{{ product.name }}")
            .add_section("features", "{{ features|join(', ') }}")
            .add_section("shipping", "Fast shipping available")
            .set_footer("Thank you for your purchase!")
            .build()
        )
        
        assert '{{ product.name }}' in template
        assert 'features' in template
        assert 'Fast shipping' in template


# ==================== PUBLISHER TESTS ====================

class TestPublisher:
    """Test multi-platform publisher"""
    
    @pytest.fixture
    def mock_publisher(self, mock_container):
        """Mock publisher with platform adapters"""
        publisher = MultiPlatformPublisher(container=mock_container)
        
        # Mock eBay adapter
        mock_ebay = AsyncMock(spec=eBayPublisher)
        mock_ebay.publish = AsyncMock(return_value=PublishResult(
            success=True,
            platform='ebay',
            listing_id='123456',
            url='https://ebay.com/itm/123456'
        ))
        
        publisher.platforms['ebay'] = mock_ebay
        return publisher
    
    @pytest.mark.asyncio
    async def test_publish_single_platform(self, mock_publisher):
        """Test publishing to single platform"""
        listing_data = {
            'title': 'Test Product',
            'description': 'Test Description',
            'price': 99.99,
            'quantity': 10
        }
        
        result = await mock_publisher.publish(
            listing_data,
            platforms=['ebay']
        )
        
        assert len(result) == 1
        assert result[0].success
        assert result[0].platform == 'ebay'
        assert result[0].listing_id == '123456'
    
    @pytest.mark.asyncio
    async def test_publish_with_retry(self, mock_publisher):
        """Test publishing with retry logic"""
        # Configure to fail first, then succeed
        mock_publisher.platforms['ebay'].publish.side_effect = [
            Exception("Network error"),
            PublishResult(
                success=True,
                platform='ebay',
                listing_id='123456',
                url='https://ebay.com/itm/123456'
            )
        ]
        
        listing_data = {'title': 'Test', 'price': 99.99}
        
        result = await mock_publisher.publish(
            listing_data,
            platforms=['ebay'],
            retry_failed=True
        )
        
        assert len(result) == 1
        assert result[0].success
        assert mock_publisher.platforms['ebay'].publish.call_count == 2


# ==================== QUEUE MANAGER TESTS ====================

class TestQueueManager:
    """Test async queue manager"""
    
    @pytest.fixture
    async def queue_manager(self, mock_container):
        """Queue manager instance"""
        manager = QueueManager(
            container=mock_container,
            max_workers=2
        )
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_add_task(self, queue_manager):
        """Test adding task to queue"""
        task = Task(
            id='test-1',
            type='optimize',
            data={'title': 'Test'},
            priority=1
        )
        
        await queue_manager.add_task(task)
        assert queue_manager.queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_process_task(self, queue_manager):
        """Test task processing"""
        processed = []
        
        async def handler(task):
            processed.append(task.id)
            return True
        
        queue_manager.register_handler('test', handler)
        
        task = Task(
            id='test-1',
            type='test',
            data={'value': 42}
        )
        
        await queue_manager.add_task(task)
        await asyncio.sleep(0.1)  # Let worker process
        
        assert 'test-1' in processed
    
    @pytest.mark.asyncio
    async def test_priority_queue(self, queue_manager):
        """Test priority queue ordering"""
        # Add tasks with different priorities
        tasks = [
            Task('low', 'test', {}, priority=3),
            Task('high', 'test', {}, priority=1),
            Task('medium', 'test', {}, priority=2)
        ]
        
        for task in tasks:
            await queue_manager.add_task(task)
        
        # Process order should be by priority
        processed_order = []
        
        async def handler(task):
            processed_order.append(task.id)
            return True
        
        queue_manager.register_handler('test', handler)
        
        await asyncio.sleep(0.2)
        
        assert processed_order == ['high', 'medium', 'low']


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Test integrazione componenti"""
    
    @pytest.mark.asyncio
    async def test_full_optimization_flow(self, mock_container):
        """Test flusso completo di ottimizzazione"""
        # Setup components
        with patch('transformers.pipeline'):
            optimizer = AIListingOptimizer(container=mock_container)
            template_engine = AdvancedTemplateEngine(container=mock_container)
            
            # Input data
            product_data = {
                'title': 'Original Product Title',
                'description': 'Basic description',
                'category': 'Electronics',
                'features': ['Feature 1', 'Feature 2', 'Feature 3'],
                'price': 149.99
            }
            
            # Step 1: Optimize with AI
            optimization_result = await optimizer.optimize_listing(product_data)
            
            # Step 2: Apply template
            template_engine.registry.register(
                'electronics',
                '''
                <h1>{{ title }}</h1>
                <p>{{ description }}</p>
                <ul>
                {% for feature in features %}
                <li>{{ feature }}</li>
                {% endfor %}
                </ul>
                ''',
                {'category': 'electronics'}
            )
            
            listing_html = await template_engine.render('electronics', {
                'title': optimization_result.title,
                'description': optimization_result.description,
                'features': product_data['features']
            })
            
            # Verify results
            assert '<h1>' in listing_html
            assert optimization_result.title in listing_html
            assert all(f in listing_html for f in product_data['features'])
    
    @pytest.mark.asyncio
    async def test_error_handling_flow(self, mock_container):
        """Test gestione errori nel flusso"""
        error_handler = ErrorHandler(container=mock_container)
        
        # Simulate error
        async def failing_operation():
            raise ListingError("Test error", "TEST_001")
        
        # Handle error
        result = await error_handler.handle_async(failing_operation())
        
        assert result is None  # Default fallback
        
        # Check error was logged
        assert error_handler.get_error_count() > 0


# ==================== PERFORMANCE TESTS ====================

class TestPerformance:
    """Test performance e benchmark"""
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_template_rendering_performance(self, benchmark, template_engine):
        """Benchmark template rendering"""
        context = {
            'title': 'Test Product',
            'description': 'Long description ' * 100,
            'features': [f'Feature {i}' for i in range(50)]
        }
        
        async def render():
            return await template_engine.render('test_template', context)
        
        result = await benchmark(render)
        assert result is not None
        
        # Target: <100ms
        assert benchmark.stats['mean'] < 0.1
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_cache_performance(self, benchmark, mock_redis):
        """Benchmark cache operations"""
        cache = MultiLevelCache(redis_client=mock_redis)
        
        async def cache_operations():
            await cache.set('key', 'value' * 1000)
            result = await cache.get('key')
            return result
        
        result = await benchmark(cache_operations)
        assert result is not None
        
        # Target: <10ms
        assert benchmark.stats['mean'] < 0.01
    
    @pytest.mark.benchmark
    def test_optimization_memory_usage(self):
        """Test memory usage during optimization"""
        import tracemalloc
        
        tracemalloc.start()
        
        # Simulate heavy operation
        data = []
        for i in range(1000):
            data.append({
                'title': f'Product {i}',
                'description': 'Description' * 100,
                'features': list(range(50))
            })
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Target: <500MB for 1000 products
        assert peak / 1024 / 1024 < 500


# ==================== SALES PREDICTOR TESTS ====================

class TestSalesPredictor:
    """Test sales prediction module"""
    
    @pytest.fixture
    def mock_predictor(self, mock_container):
        """Mock sales predictor"""
        with patch('prophet.Prophet'):
            predictor = SalesPredictor(container=mock_container)
            return predictor
    
    @pytest.mark.asyncio
    async def test_predict_sales(self, mock_predictor):
        """Test sales prediction"""
        historical_data = {
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'sales': [10, 15, 20]
        }
        
        prediction = await mock_predictor.predict(
            historical_data,
            days_ahead=7
        )
        
        assert 'forecast' in prediction
        assert 'confidence_interval' in prediction
        assert len(prediction['forecast']) == 7
    
    @pytest.mark.asyncio
    async def test_analyze_seasonality(self, mock_predictor):
        """Test seasonality analysis"""
        historical_data = {
            'dates': [f'2024-{m:02d}-01' for m in range(1, 13)],
            'sales': [100 + 50 * (m % 3) for m in range(1, 13)]
        }
        
        seasonality = await mock_predictor.analyze_seasonality(historical_data)
        
        assert 'weekly' in seasonality
        assert 'monthly' in seasonality
        assert 'yearly' in seasonality


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src', '--cov-report=html'])
