# Databricks notebook source
# run_tests.py - Test runner notebook for DABs CI/CD pipeline
# This notebook is executed as the final task in the E-Commerce ETL Pipeline job.
# It runs all 116 pytest data quality tests across Bronze, Silver, and Gold layers.

import sys
import builtins

# ============================================
# SETUP
# ============================================

# Install pytest
%pip install pytest -q

# Get the tests directory path
# When deployed via DABs, this file is at: /Workspace/.../tests/run_tests.py
tests_dir = '/Workspace/Users/kaveyarrasank@gmail.com/ecommerce-analytics-platform/tests/'

# Add tests directory to Python path
sys.path.insert(0, tests_dir)
sys.dont_write_bytecode = True

# Clear cached modules
for mod in list(sys.modules.keys()):
    if 'conftest' in mod or 'test_' in mod:
        del sys.modules[mod]

# Inject spark as builtins for all test modules
builtins.spark = spark

# ============================================
# RUN TESTS
# ============================================

import pytest

print(f"{'='*60}")
print(f"🧪 RUNNING DATA QUALITY TESTS")
print(f"{'='*60}")
print(f"   Test directory: {tests_dir}")
print(f"   Spark session: {type(spark).__name__}")
print()

# Run pytest with verbose output
retcode = pytest.main([
    tests_dir,
    "-v",
    "-p", "no:cacheprovider",
    "--tb=short",
    "-q",
    "--rootdir", tests_dir,
])

# Report results
print(f"\n{'='*60}")
if retcode == 0:
    print(f"✅ ALL TESTS PASSED! Pipeline completed successfully.")
else:
    print(f"❌ TESTS FAILED (exit code: {retcode})")
    print(f"   Review failures above and fix data quality issues.")
print(f"{'='*60}")

# Fail the notebook if tests fail (important for DABs job task)
assert retcode == 0, f"Data quality tests failed with exit code {retcode}"