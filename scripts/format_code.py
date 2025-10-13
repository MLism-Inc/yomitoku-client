#!/usr/bin/env python3
"""
Code formatting script - Automatically format all code
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
    """Main formatting function"""
    print("🎨 Starting code formatting...")

    # Get project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Formatting results
    results = []

    # 1. Black code formatting
    results.append(
        run_command(
            ["python", "-m", "black", "src/", "tests/", "scripts/"],
            "Black code formatting",
        )
    )

    # 2. isort import sorting
    results.append(
        run_command(
            ["python", "-m", "isort", "src/", "tests/", "scripts/"],
            "isort import sorting",
        )
    )

    # 3. Auto-fix flake8 issues
    results.append(
        run_command(
            [
                "python",
                "-m",
                "autopep8",
                "--in-place",
                "--recursive",
                "src/",
                "tests/",
                "scripts/",
            ],
            "autopep8 auto-fix",
        )
    )

    # Summary results
    print("\n" + "=" * 50)
    print("📊 Formatting Results Summary:")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All formatting completed! ({passed}/{total})")
        return 0
    else:
        print(f"⚠️  {total - passed} formatting failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
