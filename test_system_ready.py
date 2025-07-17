"""
Test finale dopo tutti i fix
"""
import sys
import os

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_all_imports():
    """Test che tutti gli import funzionino"""
    print("🔍 Testing all imports...\n")
    
    modules = [
        ("Core Dependencies", "src.core.dependencies", "DIContainer"),
        ("Cache System", "src.core.cache_system", "MultiLevelCache"),
        ("Listing Config", "src.core.listing_config", "ListingConfig"),
        ("Retry Manager", "src.core.retry_manager", "RetryManager"),
        ("Error Handling", "src.core.error_handling", "ErrorHandler"),
        ("AI Optimizer", "src.listing.ai_optimizer", "AIListingOptimizer"),
        ("Template Engine", "src.listing.template_engine", "AdvancedTemplateEngine"),
        ("Publisher", "src.listing.publisher", "MultiPlatformPublisher"),
        ("Batch Processor", "src.listing.batch_processor", "BatchProcessor"),
    ]
    
    all_ok = True
    for name, module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {name}: {class_name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
            all_ok = False
    
    return all_ok

def run_simple_test():
    """Esegue un test semplice del sistema"""
    print("\n🧪 Running simple functionality test...\n")
    
    try:
        from src.core.dependencies import DIContainer
        
        # Create container
        container = DIContainer()
        print("✅ Created DIContainer")
        
        # Register a service
        container.register('config', lambda: {'redis_url': 'redis://localhost:6379'})
        print("✅ Registered config service")
        
        # Resolve service
        config = container.get_service('config')
        print(f"✅ Resolved config: {config}")
        
        # Test Pydantic config
        from src.core.listing_config import ListingConfig
        listing_config = ListingConfig()
        print(f"✅ ListingConfig created with redis_url: {listing_config.redis_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== DROPUSH LISTING AUTOMATION - FINAL TEST ===\n")
    
    # Test all imports
    imports_ok = test_all_imports()
    
    # Run simple test
    if imports_ok:
        test_ok = run_simple_test()
    else:
        test_ok = False
    
    print("\n" + "="*50 + "\n")
    
    if imports_ok and test_ok:
        print("🎉 SUCCESS! System is ready for testing!")
        print("\n🚀 Next steps:")
        print("\n1. Run unit tests:")
        print("   python -m pytest tests/test_listing_automation.py::TestListingConfig -v")
        print("\n2. Run all tests (skip benchmarks):")
        print("   python -m pytest tests/test_listing_automation.py -v -k 'not benchmark'")
        print("\n3. Run with coverage:")
        print("   python -m pytest tests/test_listing_automation.py --cov=src --cov-report=html --cov-report=term")
        print("\n4. Run integration tests:")
        print("   python -m pytest tests/integration/test_full_flow.py -v")
        print("\n5. Run benchmarks (optional):")
        print("   python -m pytest tests/benchmarks/test_performance.py -v")
    else:
        print("❌ There are still issues to fix")

if __name__ == "__main__":
    main()
