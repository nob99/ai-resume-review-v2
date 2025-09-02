#!/usr/bin/env python3
"""
Layer 1 Test: Repository/Database Layer
Tests ORM operations and database connectivity in isolation.
"""

import asyncio
import sys
import logging
from pathlib import Path
from uuid import uuid4

# Add backend to path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from app.database.connection import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.models.analysis import AnalysisStatus, ExtractionStatus
from app.core.datetime_utils import utc_now

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_database_connectivity():
    """Test basic database connection."""
    logger.info("=== Testing Database Connectivity ===")
    
    try:
        db = next(get_db())
        logger.info("✅ Database connection successful")
        
        # Test a simple query (SQLAlchemy 2.0 compatible)
        from sqlalchemy import text
        result = db.execute(text("SELECT 1 as test")).fetchone()
        if result and result[0] == 1:
            logger.info("✅ Database query execution successful")
            return True
        else:
            logger.error("❌ Database query returned unexpected result")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()


def test_repository_instantiation():
    """Test repository instantiation and basic methods."""
    logger.info("=== Testing Repository Instantiation ===")
    
    try:
        db = next(get_db())
        repository = AnalysisRepository(db)
        logger.info("✅ AnalysisRepository instantiated successfully")
        
        # Test repository has required methods
        required_methods = [
            'create_analysis_request',
            'get_by_id_and_user', 
            'list_by_user',
            'count_by_user',
            'delete_by_id_and_user'
        ]
        
        for method in required_methods:
            if hasattr(repository, method):
                logger.info(f"✅ Repository has method: {method}")
            else:
                logger.error(f"❌ Repository missing method: {method}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Repository instantiation failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()


def test_create_analysis_request():
    """Test creating an analysis request via repository."""
    logger.info("=== Testing Create Analysis Request ===")
    
    db = None
    created_id = None
    
    try:
        db = next(get_db())
        repository = AnalysisRepository(db)
        
        # Use existing user from database  
        from uuid import UUID
        test_user_id = UUID("8955190d-e058-43ce-8260-fe5481dbb6e9")  # Real user ID from database
        test_filename = "test_repository.pdf"
        test_file_path = "/tmp/test_repository.pdf"
        
        logger.info(f"Creating analysis request for existing user: {test_user_id}")
        
        # Create analysis request
        analysis_request = repository.create_analysis_request(
            user_id=test_user_id,
            original_filename=test_filename,
            file_path=test_file_path,
            file_size_bytes=12345,
            mime_type="application/pdf",
            target_role="Software Engineer",
            target_industry="Technology",
            experience_level="mid"  # Valid experience level from database constraint
        )
        
        created_id = analysis_request.id
        logger.info(f"✅ Analysis request created: {created_id}")
        
        # Verify the created request
        if analysis_request.user_id == test_user_id:
            logger.info("✅ User ID matches")
        else:
            logger.error("❌ User ID mismatch")
            return False
            
        if analysis_request.original_filename == test_filename:
            logger.info("✅ Filename matches")
        else:
            logger.error("❌ Filename mismatch")
            return False
            
        if analysis_request.status == AnalysisStatus.PENDING.value:
            logger.info("✅ Status set correctly")
        else:
            logger.error(f"❌ Status incorrect: {analysis_request.status}")
            return False
            
        logger.info("✅ Analysis request creation successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Create analysis request failed: {str(e)}")
        return False
        
    finally:
        # Cleanup: delete the test record
        if db and created_id:
            try:
                repository.delete_by_id_and_user(created_id, test_user_id)
                logger.info(f"✅ Test record cleaned up: {created_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup test record: {str(e)}")
        
        if db:
            db.close()


def test_repository_operations():
    """Test full CRUD operations via repository."""
    logger.info("=== Testing Repository CRUD Operations ===")
    
    db = None
    created_id = None
    from uuid import UUID
    test_user_id = UUID("8955190d-e058-43ce-8260-fe5481dbb6e9")  # Real user ID from database
    
    try:
        db = next(get_db())
        repository = AnalysisRepository(db)
        
        # CREATE
        logger.info("Testing CREATE operation...")
        analysis_request = repository.create_analysis_request(
            user_id=test_user_id,
            original_filename="crud_test.pdf",
            file_path="/tmp/crud_test.pdf",
            file_size_bytes=54321,
            mime_type="application/pdf"
        )
        created_id = analysis_request.id
        logger.info(f"✅ CREATE successful: {created_id}")
        
        # READ
        logger.info("Testing READ operation...")
        retrieved = repository.get_by_id_and_user(created_id, test_user_id)
        if retrieved and retrieved.id == created_id:
            logger.info("✅ READ successful")
        else:
            logger.error("❌ READ failed")
            return False
        
        # LIST
        logger.info("Testing LIST operation...")
        user_uploads = repository.list_by_user(test_user_id, skip=0, limit=10)
        if len(user_uploads) >= 1:
            logger.info(f"✅ LIST successful: found {len(user_uploads)} records")
        else:
            logger.error("❌ LIST failed")
            return False
        
        # COUNT
        logger.info("Testing COUNT operation...")
        count = repository.count_by_user(test_user_id)
        if count >= 1:
            logger.info(f"✅ COUNT successful: {count} records")
        else:
            logger.error("❌ COUNT failed")
            return False
            
        # DELETE
        logger.info("Testing DELETE operation...")
        delete_success = repository.delete_by_id_and_user(created_id, test_user_id)
        if delete_success:
            logger.info("✅ DELETE successful")
            created_id = None  # Prevent cleanup
        else:
            logger.error("❌ DELETE failed")
            return False
            
        logger.info("✅ All CRUD operations successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Repository operations failed: {str(e)}")
        return False
        
    finally:
        # Cleanup
        if db and created_id:
            try:
                repository.delete_by_id_and_user(created_id, test_user_id)
                logger.info(f"✅ Test record cleaned up: {created_id}")
            except:
                pass
        
        if db:
            db.close()


def main():
    """Run all repository layer tests."""
    logger.info("🧪 Starting Layer 1: Repository/Database Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("Repository Instantiation", test_repository_instantiation),
        ("Create Analysis Request", test_create_analysis_request),
        ("Repository CRUD Operations", test_repository_operations),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 LAYER 1 TEST RESULTS")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if success:
            passed += 1
    
    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 Layer 1 (Repository/Database) is working correctly!")
    else:
        logger.error("💥 Layer 1 has issues that need to be fixed before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)