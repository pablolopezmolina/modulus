#!/usr/bin/env python3
"""
MODULUS Setup Script - Phase 0
Automates the setup and validation of the development environment
"""

import sys
import subprocess
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def check_python_version():
    """Verify Python version is 3.11+"""
    print_header("Checking Python Version")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
        return True
    else:
        print_error(f"Python 3.11+ required, found {version.major}.{version.minor}.{version.micro}")
        return False

def check_git():
    """Verify git is available"""
    print_header("Checking Git")
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        print_success(f"Git installed: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print_error("Git not found - please install git")
        return False

def verify_structure():
    """Verify all required directories exist"""
    print_header("Verifying Directory Structure")
    
    required_dirs = [
        'data/reference',
        'data/papers',
        'storage/results',
        'storage/cache',
        'storage/reports',
        'src/api',
        'src/core',
        'src/analysis',
        'src/reporting',
        'tests/unit',
        'tests/integration',
        'scripts'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print_success(f"{dir_path}")
        else:
            print_error(f"{dir_path} - MISSING")
            all_exist = False
    
    return all_exist

def verify_reference_data():
    """Verify reference data files exist and are valid"""
    print_header("Verifying Reference Data")
    
    files_to_check = {
        'data/reference/glycemic_index.csv': 'Glycemic Index Database',
        'data/reference/population_params.json': 'Population Parameters',
        'data/reference/safety_thresholds.json': 'Safety Thresholds'
    }
    
    all_valid = True
    for file_path, description in files_to_check.items():
        path = Path(file_path)
        if path.exists():
            try:
                if file_path.endswith('.json'):
                    with open(path) as f:
                        data = json.load(f)
                    print_success(f"{description} - Valid JSON ({len(data)} keys)")
                elif file_path.endswith('.csv'):
                    with open(path) as f:
                        lines = len([l for l in f if not l.startswith('#')])
                    print_success(f"{description} - {lines} entries")
            except Exception as e:
                print_error(f"{description} - Invalid: {e}")
                all_valid = False
        else:
            print_error(f"{description} - MISSING")
            all_valid = False
    
    return all_valid

def check_dependencies():
    """Check if key dependencies can be imported"""
    print_header("Checking Key Dependencies")
    
    dependencies = [
        ('numpy', 'NumPy'),
        ('scipy', 'SciPy'),
        ('pandas', 'Pandas'),
        ('fastapi', 'FastAPI'),
        ('pydantic', 'Pydantic'),
        ('matplotlib', 'Matplotlib'),
    ]
    
    all_available = True
    for module, name in dependencies:
        try:
            __import__(module)
            print_success(f"{name}")
        except ImportError:
            print_warning(f"{name} - Not installed (run: pip install -r requirements.txt)")
            all_available = False
    
    return all_available

def create_init_files():
    """Create __init__.py files in all Python packages"""
    print_header("Creating __init__.py Files")
    
    packages = [
        'src',
        'src/api',
        'src/api/routes',
        'src/api/schemas',
        'src/api/validation',
        'src/core',
        'src/core/models',
        'src/core/population',
        'src/analysis',
        'src/reporting',
        'src/storage',
        'tests',
        'tests/unit',
        'tests/integration',
    ]
    
    for package in packages:
        init_file = Path(package) / '__init__.py'
        if not init_file.exists():
            init_file.write_text('"""MODULUS package"""\n')
            print_success(f"Created {init_file}")
        else:
            print_success(f"Already exists: {init_file}")

def print_next_steps():
    """Print guidance for next steps"""
    print_header("Phase 0 Setup Complete! ✅")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}\n")
    print("1. Install dependencies (if not already installed):")
    print("   $ pip install -r requirements.txt\n")
    
    print("2. Run tests to verify installation:")
    print("   $ pytest tests/\n")
    
    print("3. Start Phase 1 - Core Simulation Engine:")
    print("   - Implement Dalla Man glucose model (src/core/models/glucose.py)")
    print("   - Implement caffeine PK model (src/core/models/caffeine.py)")
    print("   - Build population generator (src/core/population/generator.py)")
    print("   - Create orchestrator (src/core/orchestrator.py)\n")
    
    print(f"{Colors.BOLD}Documentation:{Colors.END}")
    print("   - See README.md for project overview")
    print("   - See data/reference/ for scientific parameters")
    print("   - See data/papers/ for source publications\n")
    
    print(f"{Colors.GREEN}{Colors.BOLD}Ready to build MODULUS! 🚀{Colors.END}\n")

def main():
    """Run all setup checks"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                   MODULUS SETUP SCRIPT                    ║")
    print("║            Phase 0: Development Environment               ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Git Installation", check_git),
        ("Directory Structure", verify_structure),
        ("Reference Data", verify_reference_data),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    # Optional checks
    print("\n" + "="*60)
    print(f"{Colors.BOLD}OPTIONAL CHECKS{Colors.END}")
    print("="*60 + "\n")
    
    dep_check = check_dependencies()
    
    # Create init files
    create_init_files()
    
    # Summary
    print("\n" + "="*60)
    print(f"{Colors.BOLD}SETUP SUMMARY{Colors.END}")
    print("="*60 + "\n")
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{name:.<40} {status}")
    
    dep_status = 'READY' if dep_check else 'INSTALL NEEDED'
    print(f"{'Dependencies':<40} {dep_status}")
    
    if all_passed:
        print_next_steps()
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠ Some checks failed - please fix errors above{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
