#!/usr/bin/env python3
"""Test runner script for running all tests in the correct order."""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class TestRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        print(f"Running: {' '.join(cmd)}")
        if cwd:
            print(f"  in {cwd}")
        
        result = subprocess.run(cmd, cwd=cwd or self.project_root, env=full_env, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result
    
    def run_backend_unit_tests(self) -> bool:
        """Run backend unit tests."""
        print("\n=== Running Backend Unit Tests ===")
        result = self.run_command([
            "pytest", "tests/",
            "-m", "not integration and not slow and not regression",
            "--cov=app",
            "--cov-report=xml",
            "--cov-report=html",
            "--cov-report=json",
            "--junitxml=test-results.xml",
            "-v"
        ], cwd=self.backend_dir)
        return result.returncode == 0
    
    def run_backend_integration_tests(self) -> bool:
        """Run backend integration tests."""
        print("\n=== Running Backend Integration Tests ===")
        result = self.run_command([
            "pytest", "tests/integration/",
            "--junitxml=integration-results.xml",
            "-v"
        ], cwd=self.backend_dir, env={
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "DATABASE_URL": "sqlite+aiosqlite:///test.db"
        })
        return result.returncode == 0
    
    def run_backend_load_tests(self) -> bool:
        """Run backend load tests."""
        print("\n=== Running Backend Load Tests ===")
        result = self.run_command([
            "pytest", "tests/load/",
            "-m", "not stress",
            "--junitxml=load-results.xml",
            "-v"
        ], cwd=self.backend_dir, env={
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "DATABASE_URL": "sqlite+aiosqlite:///test.db"
        })
        return result.returncode == 0
    
    def run_backend_regression_tests(self) -> bool:
        """Run backend regression tests."""
        print("\n=== Running Backend Regression Tests ===")
        result = self.run_command([
            "pytest", "tests/regression/",
            "--junitxml=regression-results.xml",
            "-v"
        ], cwd=self.backend_dir, env={
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "DATABASE_URL": "sqlite+aiosqlite:///test.db"
        })
        return result.returncode == 0
    
    def run_frontend_unit_tests(self) -> bool:
        """Run frontend unit tests."""
        print("\n=== Running Frontend Unit Tests ===")
        result = self.run_command([
            "npm", "run", "test", "--", "--coverage"
        ], cwd=self.frontend_dir)
        return result.returncode == 0
    
    def run_frontend_e2e_tests(self) -> bool:
        """Run frontend E2E tests."""
        print("\n=== Running Frontend E2E Tests ===")
        
        # Install Playwright if needed
        self.run_command(["npx", "playwright", "install", "--with-deps", "chromium"], cwd=self.frontend_dir)
        
        # Build frontend
        result = self.run_command(["npm", "run", "build"], cwd=self.frontend_dir)
        if result.returncode != 0:
            return False
        
        # Run E2E tests
        result = self.run_command([
            "npx", "playwright", "test", "tests/e2e/",
            "--reporter=junit,playwright-results.xml"
        ], cwd=self.frontend_dir, env={
            "E2E_BASE_URL": "http://localhost:5173",
            "E2E_API_URL": "http://localhost:8000"
        })
        return result.returncode == 0
    
    def run_frontend_integration_tests(self) -> bool:
        """Run frontend integration tests."""
        print("\n=== Running Frontend Integration Tests ===")
        result = self.run_command([
            "npm", "run", "test:integration"
        ], cwd=self.frontend_dir, env={
            "E2E_API_URL": "http://localhost:8000"
        })
        return result.returncode == 0
    
    def run_all(self, skip: List[str] = None) -> bool:
        """Run all tests."""
        skip = skip or []
        
        test_suites = [
            ("backend_unit", self.run_backend_unit_tests),
            ("backend_integration", self.run_backend_integration_tests),
            ("backend_load", self.run_backend_load_tests),
            ("backend_regression", self.run_backend_regression_tests),
            ("frontend_unit", self.run_frontend_unit_tests),
            ("frontend_e2e", self.run_frontend_e2e_tests),
            ("frontend_integration", self.run_frontend_integration_tests),
        ]
        
        results = {}
        all_passed = True
        
        for name, test_func in test_suites:
            if name in skip:
                print(f"\n=== Skipping {name} ===")
                results[name] = "skipped"
                continue
            
            try:
                passed = test_func()
                results[name] = "passed" if passed else "failed"
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"Error running {name}: {e}")
                results[name] = "error"
                all_passed = False
        
        # Print summary
        print("\n=== Test Summary ===")
        for name, status in results.items():
            status_icon = "✓" if status == "passed" else "✗" if status == "failed" else "⊘" if status == "skipped" else "⚠"
            print(f"  {status_icon} {name}: {status}")
        
        return all_passed


def main():
    parser = argparse.ArgumentParser(description="Run all tests")
    parser.add_argument("--skip", nargs="*", default=[], help="Test suites to skip")
    parser.add_argument("--only", nargs="*", default=[], help="Only run specific test suites")
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)
    
    if args.only:
        # Run only specified suites
        skip = [s for s in [
            "backend_unit", "backend_integration", "backend_load", "backend_regression",
            "frontend_unit", "frontend_e2e", "frontend_integration"
        ] if s not in args.only]
    else:
        skip = args.skip
    
    success = runner.run_all(skip=skip)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()