#!/usr/bin/env python3
"""
Quick verification script to test backend imports and configuration.
Run this after installation to verify everything is set up correctly.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


def check_imports():
    """Check that all critical imports work."""
    print("🔍 Checking imports...")
    
    try:
        from backend.core.config import settings
        print("✓ Config imports successfully")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from backend.database.base import Base, BaseModel
        print("✓ Database base imports successfully")
    except Exception as e:
        print(f"✗ Database base import failed: {e}")
        return False
    
    try:
        from backend.database.session import get_db, AsyncSessionLocal
        print("✓ Database session imports successfully")
    except Exception as e:
        print(f"✗ Database session import failed: {e}")
        return False
    
    try:
        from backend.core.redis import get_redis
        print("✓ Redis imports successfully")
    except Exception as e:
        print(f"✗ Redis import failed: {e}")
        return False
    
    try:
        from backend.api.routes.health import router
        print("✓ Health routes import successfully")
    except Exception as e:
        print(f"✗ Health routes import failed: {e}")
        return False
    
    try:
        from backend.main import app
        print("✓ FastAPI app imports successfully")
    except Exception as e:
        print(f"✗ FastAPI app import failed: {e}")
        return False
    
    return True


def check_config():
    """Check that configuration loads correctly."""
    print("\n🔧 Checking configuration...")
    
    try:
        from backend.core.config import settings
        print(f"✓ App: {settings.app_name} v{settings.app_version}")
        print(f"✓ Debug: {settings.debug}")
        print(f"✓ Database URL configured: {bool(settings.database_url)}")
        print(f"✓ Redis URL configured: {bool(settings.redis_url)}")
        return True
    except Exception as e:
        print(f"✗ Configuration check failed: {e}")
        return False


def check_routes():
    """Check that routes are properly registered."""
    print("\n🛣️ Checking routes...")
    
    try:
        from backend.main import app
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append(f"{', '.join(route.methods)} {route.path}")
        
        if routes:
            print(f"✓ Found {len(routes)} route(s):")
            for route in routes:
                print(f"  - {route}")
            return True
        else:
            print("✗ No routes found")
            return False
    except Exception as e:
        print(f"✗ Route check failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 50)
    print("NisargHunter AI - Backend Verification")
    print("=" * 50)
    
    checks = [
        ("Imports", check_imports),
        ("Configuration", check_config),
        ("Routes", check_routes),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\n✓ All checks passed! Backend is ready to run.")
        print("\nStart the development server with:")
        print("  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
