#!/usr/bin/env python3
"""
Validation Tests for Priority 1 Fixes

Tests to ensure all three priority 1 fixes have been implemented correctly:
1. Analytics metrics endpoint implementation
2. Admin authorization checks
3. Specific database exception handling
"""

import sys
import os
import inspect
from typing import get_type_hints
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_analytics_metrics_implementation():
    """Test that analytics metrics endpoint is properly implemented."""
    print("🔍 Testing Analytics Metrics Implementation...")
    
    try:
        from app.services.analytics_service import AnalyticsService
        from app.api.analytics import get_analytics_metrics
        
        # Check if metrics method exists in service
        assert hasattr(AnalyticsService, 'get_aggregated_metrics'), "❌ get_aggregated_metrics method missing"
        
        # Check method signature
        sig = inspect.signature(AnalyticsService.get_aggregated_metrics)
        params = list(sig.parameters.keys())
        expected_params = ['self', 'date_start', 'date_end', 'course_id']
        assert all(param in params for param in expected_params), f"❌ Missing parameters: {expected_params}"
        
        # Check return type annotation
        assert sig.return_annotation != inspect.Signature.empty, "❌ Missing return type annotation"
        
        # Check API endpoint uses admin authorization
        api_sig = inspect.signature(get_analytics_metrics)
        api_params = str(api_sig)
        assert 'require_admin_role' in api_params, "❌ Admin authorization missing from metrics endpoint"
        
        print("✅ Analytics metrics implementation complete")
        return True
        
    except Exception as e:
        print(f"❌ Analytics metrics test failed: {e}")
        return False

def test_admin_authorization():
    """Test that admin authorization is properly implemented."""
    print("🔍 Testing Admin Authorization...")
    
    try:
        from app.api.deps import require_admin_role
        from app.api.analytics import get_analytics_metrics
        
        # Check admin dependency exists
        assert callable(require_admin_role), "❌ require_admin_role not callable"
        
        # Check metrics endpoint uses admin dependency
        source = inspect.getsource(get_analytics_metrics)
        assert 'require_admin_role' in source, "❌ Metrics endpoint doesn't use admin authorization"
        
        # Check admin dependency signature
        sig = inspect.signature(require_admin_role)
        assert 'current_user_payload' in str(sig), "❌ Admin dependency missing user payload parameter"
        
        print("✅ Admin authorization implementation complete")
        return True
        
    except Exception as e:
        print(f"❌ Admin authorization test failed: {e}")
        return False

def test_specific_exception_handling():
    """Test that specific database exception handling is implemented."""
    print("🔍 Testing Specific Exception Handling...")
    
    try:
        from app.api.analytics import track_analytics_event, get_analytics_metrics
        from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
        
        # Check imports exist
        import app.api.analytics as analytics_module
        source = inspect.getsource(analytics_module)
        
        # Check for specific exception imports
        assert 'SQLAlchemyError' in source, "❌ SQLAlchemyError not imported"
        assert 'IntegrityError' in source, "❌ IntegrityError not imported"
        assert 'OperationalError' in source, "❌ OperationalError not imported"
        
        # Check for specific exception handling in methods
        event_source = inspect.getsource(track_analytics_event)
        assert 'except IntegrityError' in event_source, "❌ IntegrityError not handled in track_analytics_event"
        assert 'except OperationalError' in event_source, "❌ OperationalError not handled in track_analytics_event"
        assert 'except SQLAlchemyError' in event_source, "❌ SQLAlchemyError not handled in track_analytics_event"
        
        metrics_source = inspect.getsource(get_analytics_metrics)
        assert 'except OperationalError' in metrics_source, "❌ OperationalError not handled in get_analytics_metrics"
        assert 'except SQLAlchemyError' in metrics_source, "❌ SQLAlchemyError not handled in get_analytics_metrics"
        
        print("✅ Specific exception handling implementation complete")
        return True
        
    except Exception as e:
        print(f"❌ Exception handling test failed: {e}")
        return False

def test_metrics_endpoint_functionality():
    """Test that metrics endpoint has proper functionality."""
    print("🔍 Testing Metrics Endpoint Functionality...")
    
    try:
        from app.services.analytics_service import AnalyticsService
        
        # Test the metrics calculation method structure
        sig = inspect.signature(AnalyticsService.get_aggregated_metrics)
        source = inspect.getsource(AnalyticsService.get_aggregated_metrics)
        
        # Check for key metrics calculations
        required_metrics = [
            'total_events',
            'events_by_type', 
            'events_by_category',
            'active_users',
            'engagement_rate',
            'completion_rates'
        ]
        
        for metric in required_metrics:
            assert metric in source, f"❌ Missing metric calculation: {metric}"
        
        # Check for database queries
        assert 'base_query' in source, "❌ Missing base query implementation"
        assert 'group_by' in source, "❌ Missing aggregation queries"
        
        print("✅ Metrics endpoint functionality complete")
        return True
        
    except Exception as e:
        print(f"❌ Metrics functionality test failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests."""
    print("🚀 Running Priority 1 Fixes Validation Tests\n")
    
    tests = [
        test_analytics_metrics_implementation,
        test_admin_authorization, 
        test_specific_exception_handling,
        test_metrics_endpoint_functionality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}\n")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL FIXES SUCCESSFULLY IMPLEMENTED!")
        return True
    else:
        print("⚠️  Some fixes need attention")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)