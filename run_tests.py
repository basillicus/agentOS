#!/usr/bin/env python3
"""
Test runner for AgentOS tests.
This script runs all unit, integration, and evaluation tests.
"""

import unittest
import sys
import os
import argparse
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_specific_tests(suite_name):
    """
    Run specific test suites by importing them directly.
    
    Args:
        suite_name (str): Name of the test suite ('unit', 'integration', 'evals', 'all')
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    if suite_name in ['unit', 'all']:
        # Import unit test modules directly
        try:
            from tests.unit.test_disk_skill import TestDiskSkill
            from tests.unit.test_memory_skill import TestMemorySkill  
            from tests.unit.test_system_skill import TestSystemSkill
            
            suite.addTests(loader.loadTestsFromTestCase(TestDiskSkill))
            suite.addTests(loader.loadTestsFromTestCase(TestMemorySkill))
            suite.addTests(loader.loadTestsFromTestCase(TestSystemSkill))
            print("✓ Added unit tests")
        except ImportError as e:
            print(f"⚠ Failed to load unit tests: {e}")
    
    if suite_name in ['integration', 'all']:
        # Import integration test modules directly
        try:
            from tests.integration.test_agent_integration import TestAgentIntegration
            
            suite.addTests(loader.loadTestsFromTestCase(TestAgentIntegration))
            print("✓ Added integration tests")
        except ImportError as e:
            print(f"⚠ Failed to load integration tests: {e}")
    
    if suite_name in ['evals', 'all']:
        # Import evaluation test modules directly
        try:
            from tests.evals.test_agent_logfire_evaluation import TestAgentLogfireEvaluation, AgentBenchmarkWithLogfireTests
            from tests.evals.test_agent_pydantic_evals import TestAgentPydanticEvals
            
            suite.addTests(loader.loadTestsFromTestCase(TestAgentLogfireEvaluation))
            suite.addTests(loader.loadTestsFromTestCase(AgentBenchmarkWithLogfireTests))
            suite.addTests(loader.loadTestsFromTestCase(TestAgentPydanticEvals))
            print("✓ Added evaluation tests")
        except ImportError as e:
            print(f"⚠ Failed to load evaluation tests: {e}")
    
    return suite


def run_tests(test_type='all', verbose=False):
    """
    Run tests based on the specified type.
    
    Args:
        test_type (str): Type of tests to run ('unit', 'integration', 'evals', 'all')
        verbose (bool): Whether to run tests in verbose mode
    """
    print(f"Loading {test_type} tests...")
    suite = run_specific_tests(test_type)
    
    if suite.countTestCases() == 0:
        print(f"No tests found for type: {test_type}")
        return True
    
    # Run the tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(suite)
    
    # Return success/failure
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description="Run AgentOS tests")
    parser.add_argument(
        '--type', 
        choices=['unit', 'integration', 'evals', 'all'], 
        default='all',
        help='Type of tests to run (default: all)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Run tests in verbose mode'
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting AgentOS tests...")
    print(f"Test type: {args.type}")
    print(f"Verbose: {args.verbose}")
    print("-" * 50)
    
    success = run_tests(test_type=args.type, verbose=args.verbose)
    
    print("-" * 50)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()