"""
UPLOAD-003 Test Runner

Comprehensive test runner for all UPLOAD-003 text extraction functionality.
Runs unit tests, integration tests, and performance benchmarks.
"""

import pytest
import sys
import os
from pathlib import Path
import time
import argparse


def run_unit_tests(verbose: bool = False) -> bool:
    """Run all unit tests for UPLOAD-003."""
    print("🧪 Running UPLOAD-003 Unit Tests...")
    
    unit_test_dir = Path(__file__).parent / "unit"
    
    args = [
        str(unit_test_dir),
        "-v" if verbose else "-q",
        "--tb=short",
        "--durations=10",
        "--cov=app.services.text_extraction_service",
        "--cov=app.core.text_processor", 
        "--cov=app.core.background_processor",
        "--cov=app.core.extraction_cache",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/unit",
        "-m", "not performance"  # Exclude performance tests
    ]
    
    return pytest.main(args) == 0


def run_integration_tests(verbose: bool = False) -> bool:
    """Run all integration tests for UPLOAD-003."""
    print("🔗 Running UPLOAD-003 Integration Tests...")
    
    integration_test_dir = Path(__file__).parent / "integration"
    
    args = [
        str(integration_test_dir),
        "-v" if verbose else "-q",
        "--tb=short",
        "--durations=10"
    ]
    
    return pytest.main(args) == 0


def run_performance_tests(verbose: bool = False) -> bool:
    """Run performance tests for UPLOAD-003."""
    print("⚡ Running UPLOAD-003 Performance Tests...")
    
    args = [
        str(Path(__file__).parent),
        "-v" if verbose else "-q",
        "--tb=short",
        "--durations=0",
        "-m", "performance"
    ]
    
    return pytest.main(args) == 0


def run_sample_file_tests(verbose: bool = False) -> bool:
    """Run tests with real sample files."""
    print("📁 Running Sample File Tests...")
    
    sample_dir = Path(__file__).parent / "sample_files"
    
    # Check if sample files exist
    required_files = [
        "sample_resume_simple.pdf",
        "sample_resume_complex.pdf", 
        "sample_resume.docx",
        "sample_resume_text.txt"
    ]
    
    missing_files = []
    for filename in required_files:
        if not (sample_dir / filename).exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"⚠️  Missing sample files: {missing_files}")
        print("Run create_sample_files.py to generate test files")
        return False
    
    # Run tests that specifically use sample files
    args = [
        str(Path(__file__).parent),
        "-v" if verbose else "-q",
        "--tb=short",
        "-k", "sample_file or real_file",
        f"--sample-files-dir={sample_dir}"
    ]
    
    return pytest.main(args) == 0


def run_all_tests(verbose: bool = False, include_performance: bool = False) -> None:
    """Run comprehensive test suite."""
    print("🚀 Running Complete UPLOAD-003 Test Suite")
    print("=" * 50)
    
    start_time = time.time()
    results = {}
    
    # Unit tests
    results['unit'] = run_unit_tests(verbose)
    
    # Integration tests  
    results['integration'] = run_integration_tests(verbose)
    
    # Sample file tests
    results['sample_files'] = run_sample_file_tests(verbose)
    
    # Performance tests (optional)
    if include_performance:
        results['performance'] = run_performance_tests(verbose)
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 50)
    print("📊 UPLOAD-003 Test Results Summary")
    print("=" * 50)
    
    total_suites = len(results)
    passed_suites = sum(1 for passed in results.values() if passed)
    
    for suite_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{suite_name.ljust(20)}: {status}")
    
    print(f"\nOverall: {passed_suites}/{total_suites} test suites passed")
    print(f"Duration: {duration:.2f} seconds")
    
    if passed_suites == total_suites:
        print("🎉 All UPLOAD-003 tests passed!")
        return True
    else:
        print("🔴 Some tests failed - check output above")
        return False


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    print("🔍 Checking UPLOAD-003 dependencies...")
    
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-asyncio',
        'PyPDF2',
        'pdfplumber', 
        'python-docx',
        'beautifulsoup4',
        'lxml',
        'redis',
        'reportlab'  # For creating test files
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  Missing packages: {missing_packages}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    else:
        print("✅ All dependencies installed")
        return True


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="UPLOAD-003 Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--sample-files", action="store_true", help="Run sample file tests")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies only")
    parser.add_argument("--all", action="store_true", help="Run all tests including performance")
    
    args = parser.parse_args()
    
    # Check dependencies first
    if args.check_deps:
        success = check_dependencies()
        sys.exit(0 if success else 1)
    
    if not check_dependencies():
        print("❌ Dependencies missing - install required packages first")
        sys.exit(1)
    
    success = False
    
    if args.unit:
        success = run_unit_tests(args.verbose)
    elif args.integration:
        success = run_integration_tests(args.verbose)
    elif args.performance:
        success = run_performance_tests(args.verbose)
    elif args.sample_files:
        success = run_sample_file_tests(args.verbose)
    elif args.all:
        success = run_all_tests(args.verbose, include_performance=True)
    else:
        # Default: run unit and integration tests
        success = run_all_tests(args.verbose, include_performance=False)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()