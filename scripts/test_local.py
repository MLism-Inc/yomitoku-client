#!/usr/bin/env python3
"""
Local test script - Run all tests and checks before commit
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run command and return result"""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    """Main test function"""
    print("🚀 Starting local tests...")

    # Get project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Test results
    results = []

    # 1. Code formatting check
    results.append(
        run_command(
            ["python", "-m", "black", "--check", "src/", "tests/"],
            "Black code formatting check",
        )
    )

    # 2. Import sorting check
    results.append(
        run_command(
            ["python", "-m", "isort", "--check-only", "src/", "tests/"],
            "isort import sorting check",
        )
    )

    # 3. Code quality check
    results.append(
        run_command(
            ["python", "-m", "flake8", "src/", "tests/"], "flake8 code quality check"
        )
    )

    # 4. Type checking
    results.append(run_command(
        ["python", "-m", "mypy", "src/"], "mypy type checking"))

    # 5. Run tests
    results.append(
        run_command(
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--cov=src",
                "--cov-report=term-missing",
            ],
            "pytest unit tests",
        )
    )

    # 6. Build package test
    results.append(run_command(
        ["python", "-m", "build"], "Build package test"))

    # 7. Package quality check
    results.append(
        run_command(
            ["python", "-m", "twine", "check",
                "dist/*"], "twine package quality check"
        )
    )

    # Summary results
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        return 0
    else:
        print(f"⚠️  {total - passed} tests failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
