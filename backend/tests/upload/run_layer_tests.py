#!/usr/bin/env python3
"""
Upload Layer Tests Runner
Runs all layer tests in sequence to identify upload issues systematically.
"""

import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_test_script(script_path: Path) -> Tuple[bool, str]:
    """
    Run a test script and return success status and output.
    
    Args:
        script_path: Path to the test script
        
    Returns:
        Tuple of (success, output)
    """
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, output
        
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 5 minutes"
    except Exception as e:
        return False, f"Failed to run test: {str(e)}"


def check_docker_logs():
    """Check Docker container logs for upload-related errors."""
    logger.info("=== Checking Docker Container Logs ===")
    
    try:
        # Try to get backend container logs
        result = subprocess.run(
            ["docker", "logs", "--tail", "50", "backend"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Docker logs retrieved successfully")
            
            logs = result.stdout + result.stderr
            
            # Look for error patterns
            error_patterns = [
                "500 Internal Server Error",
                "upload",
                "ERROR",
                "Exception",
                "Traceback",
                "SQLAlchemy",
                "store_uploaded_file"
            ]
            
            relevant_lines = []
            for line in logs.split('\n'):
                for pattern in error_patterns:
                    if pattern.lower() in line.lower():
                        relevant_lines.append(line)
                        break
            
            if relevant_lines:
                logger.info("🔍 Found potentially relevant log entries:")
                for line in relevant_lines[-10:]:  # Show last 10 relevant lines
                    logger.info(f"  {line}")
            else:
                logger.info("ℹ️ No obvious error patterns found in recent logs")
                
            return True, logs
            
        else:
            logger.warning("⚠️ Could not retrieve Docker logs")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ Docker logs command timed out")
        return False, "Timeout"
    except FileNotFoundError:
        logger.warning("⚠️ Docker command not found - may not be running in Docker")
        return False, "Docker not available"
    except Exception as e:
        logger.warning(f"⚠️ Error checking Docker logs: {str(e)}")
        return False, str(e)


def main():
    """Run all layer tests in sequence."""
    logger.info("🚀 Starting Upload Layer Tests")
    logger.info("=" * 80)
    
    # Test scripts in execution order
    test_dir = Path(__file__).parent
    tests = [
        ("Layer 1: Repository/Database", test_dir / "layer_1_repository_test.py"),
        ("Layer 2: File Storage", test_dir / "layer_2_file_storage_test.py"),
        ("Layer 3: Service Layer", test_dir / "layer_3_service_test.py"),
        ("Layer 4: API Layer", test_dir / "layer_4_api_test.py"),
    ]
    
    # Check Docker logs first
    logger.info("\n📋 Phase 1: Infrastructure Check")
    logger.info("-" * 50)
    check_docker_logs()
    
    # Run layer tests
    logger.info("\n🧪 Phase 2: Layer Testing")
    logger.info("-" * 50)
    
    results = {}
    failed_at_layer = None
    
    for layer_name, script_path in tests:
        if not script_path.exists():
            logger.error(f"❌ Test script not found: {script_path}")
            results[layer_name] = False
            continue
            
        logger.info(f"\n🔍 Running: {layer_name}")
        logger.info("-" * 40)
        
        success, output = run_test_script(script_path)
        results[layer_name] = success
        
        if success:
            logger.info(f"✅ {layer_name}: PASSED")
        else:
            logger.error(f"❌ {layer_name}: FAILED")
            failed_at_layer = layer_name
            
            # Show failure output
            logger.error("Failure output:")
            for line in output.split('\n')[-20:]:  # Show last 20 lines
                if line.strip():
                    logger.error(f"  {line}")
            
            # Stop at first failure for focused debugging
            logger.error(f"\n🛑 STOPPING: {layer_name} failed")
            logger.error("Fix this layer before proceeding to higher layers.")
            break
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 FINAL RESULTS")
    logger.info("=" * 80)
    
    passed = 0
    total = len(tests)
    
    for layer_name, script_path in tests:
        if layer_name in results:
            status = "✅ PASS" if results[layer_name] else "❌ FAIL"
            logger.info(f"{layer_name}: {status}")
            if results[layer_name]:
                passed += 1
        else:
            logger.info(f"{layer_name}: ⏭️ SKIPPED")
    
    logger.info("-" * 80)
    logger.info(f"Results: {passed}/{len(results)} layers passed")
    
    if failed_at_layer:
        logger.error(f"\n💥 DIAGNOSIS: Upload system failed at {failed_at_layer}")
        logger.error("Recommendation: Fix the failing layer before testing higher layers.")
        
        # Provide specific guidance
        if "Repository" in failed_at_layer:
            logger.error("🔧 Focus on: Database connectivity, ORM models, SQLAlchemy configuration")
        elif "File Storage" in failed_at_layer:
            logger.error("🔧 Focus on: File validation, storage directories, permissions")
        elif "Service" in failed_at_layer:
            logger.error("🔧 Focus on: Business logic, dependency injection, service coordination")
        elif "API" in failed_at_layer:
            logger.error("🔧 Focus on: FastAPI routing, request handling, authentication")
            
    elif passed == total:
        logger.info("🎉 ALL LAYERS PASSED!")
        logger.info("The upload system architecture is working correctly.")
        logger.info("Issue may be in integration or runtime environment.")
        logger.info("\n📋 Next steps:")
        logger.info("1. Test actual browser upload with full logging")
        logger.info("2. Check network connectivity between frontend and backend")
        logger.info("3. Verify production environment configuration")
    else:
        logger.info("✅ Some layers passed - partial system functionality confirmed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)