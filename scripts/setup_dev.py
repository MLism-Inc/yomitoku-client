#!/usr/bin/env python3
"""
Development environment setup script
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
    """Main setup function"""
    print("🚀 Setting up Yomitoku Client development environment...")

    # Get project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Setup results
    results = []

    # 1. Install package in development mode
    results.append(
        run_command(
            ["pip", "install", "-e", "."], "Install package in development mode"
        )
    )

    # 2. Install development dependencies
    results.append(
        run_command(
            ["pip", "install", "-e", ".[dev]"], "Install development dependencies"
        )
    )

    # 3. Install pre-commit
    results.append(run_command(
        ["pip", "install", "pre-commit"], "Install pre-commit"))

    # 4. Install pre-commit hooks
    results.append(run_command(
        ["pre-commit", "install"], "Install pre-commit hooks"))

    # 5. Run pre-commit on all files
    results.append(
        run_command(["pre-commit", "run", "--all-files"],
                    "Run pre-commit on all files")
    )

    # Summary results
    print("\n" + "=" * 50)
    print("📊 Setup Results Summary:")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 Development environment setup complete! ({passed}/{total})")
        print("\n📝 Next steps:")
        print("1. Run 'make test' to run tests")
        print("2. Run 'make format' to format code")
        print("3. Run 'make check' to run all checks")
        print("4. Start coding! Pre-commit hooks will run automatically on commit")
        return 0
    else:
        print(f"⚠️  {total - passed} setup steps failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
