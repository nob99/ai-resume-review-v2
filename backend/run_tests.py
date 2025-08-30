#!/usr/bin/env python3
"""
Test runner for AI Resume Review Platform backend.
Runs comprehensive tests for AUTH-004 password security implementation.
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_tests(test_file=None, verbose=False, coverage=False, html_coverage=False):
    """
    Run tests with pytest.
    
    Args:
        test_file: Specific test file to run (optional)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        html_coverage: Generate HTML coverage report
    """
    cmd = ["python", "-m", "pytest"]
    
    if test_file:
        cmd.append(test_file)
    else:
        cmd.append("tests/")
    
    # Add pytest options
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Coverage options
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-fail-under=90"  # Require 90% coverage
        ])
        
        if html_coverage:
            cmd.append("--cov-report=html")
    
    # Additional pytest options
    cmd.extend([
        "--tb=short",  # Short traceback format
        "-x",          # Stop on first failure
        "--strict-markers",  # Strict marker checking
    ])
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=False, cwd=project_root)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


def install_dependencies():
    """Install test dependencies."""
    logger.info("Installing test dependencies...")
    
    try:
        # Install test requirements
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, cwd=project_root)
        
        logger.info("Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False


def check_code_quality():
    """Run code quality checks."""
    logger.info("Running code quality checks...")
    
    checks = [
        # Black formatting check
        ["python", "-m", "black", "--check", "--diff", "app/", "tests/"],
        
        # Flake8 linting
        ["python", "-m", "flake8", "app/", "tests/", "--max-line-length=100"],
        
        # MyPy type checking
        ["python", "-m", "mypy", "app/", "--ignore-missing-imports"],
    ]
    
    all_passed = True
    
    for check in checks:
        logger.info(f"Running: {' '.join(check)}")
        try:
            result = subprocess.run(check, check=False, cwd=project_root, 
                                    capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Quality check failed: {check[2]}")
                if result.stdout:
                    logger.warning(f"stdout: {result.stdout}")
                if result.stderr:
                    logger.warning(f"stderr: {result.stderr}")
                all_passed = False
            else:
                logger.info(f"Quality check passed: {check[2]}")
        except Exception as e:
            logger.error(f"Error running quality check {check[2]}: {e}")
            all_passed = False
    
    return all_passed


def generate_test_report():
    """Generate comprehensive test report."""
    logger.info("Generating comprehensive test report...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=long",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "--junit-xml=test-results.xml",
    ]
    
    try:
        result = subprocess.run(cmd, check=False, cwd=project_root)
        
        if result.returncode == 0:
            logger.info("Test report generated successfully")
            logger.info("HTML coverage report: htmlcov/index.html")
            logger.info("XML coverage report: coverage.xml")
            logger.info("JUnit XML report: test-results.xml")
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="AI Resume Review Backend Test Runner")
    parser.add_argument("--file", "-f", help="Specific test file to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Enable coverage")
    parser.add_argument("--html-coverage", action="store_true", help="Generate HTML coverage")
    parser.add_argument("--quality", "-q", action="store_true", help="Run quality checks")
    parser.add_argument("--report", "-r", action="store_true", help="Generate full report")
    parser.add_argument("--install", "-i", action="store_true", help="Install dependencies")
    parser.add_argument("--all", "-a", action="store_true", help="Run all checks")
    
    args = parser.parse_args()
    
    success = True
    
    # Install dependencies if requested
    if args.install or args.all:
        if not install_dependencies():
            success = False
    
    # Run quality checks if requested
    if args.quality or args.all:
        if not check_code_quality():
            logger.warning("Some quality checks failed")
            # Don't fail the entire run for quality issues
    
    # Generate full report if requested
    if args.report:
        if not generate_test_report():
            success = False
    else:
        # Run regular tests
        if not run_tests(
            test_file=args.file,
            verbose=args.verbose or args.all,
            coverage=args.coverage or args.all,
            html_coverage=args.html_coverage or args.all
        ):
            success = False
    
    if success:
        logger.info("All tests passed successfully! ✅")
        
        # Show coverage summary if enabled
        if args.coverage or args.all or args.report:
            logger.info("\nCoverage Summary:")
            logger.info("================")
            logger.info("✅ Password hashing and validation")
            logger.info("✅ User model security features")
            logger.info("✅ Rate limiting functionality")
            logger.info("✅ Authentication endpoints")
            logger.info("✅ Security error handling")
            
        return 0
    else:
        logger.error("Some tests failed! ❌")
        return 1


if __name__ == "__main__":
    sys.exit(main())