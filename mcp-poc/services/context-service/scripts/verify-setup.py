#!/usr/bin/env python3
"""
Verification script for Context Service database setup

This script verifies that all the required components for database bootstrap are in place:
- Alembic configuration
- Migration files
- Database models
- Bootstrap script
- Helm templates
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report the result"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (NOT FOUND)")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report the result"""
    if Path(dirpath).is_dir():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} (NOT FOUND)")
        return False

def main():
    """Main verification function"""
    print("🔍 Verifying Context Service Database Bootstrap Setup")
    print("=" * 60)
    
    success_count = 0
    total_checks = 0
    
    # Check core files
    checks = [
        # Alembic setup
        ("Alembic config", "alembic.ini"),
        ("Alembic env.py", "migrations/env.py"),
        ("Alembic script template", "migrations/script.py.mako"),
        ("Alembic versions directory", "migrations/versions"),
        
        # Database models and migrations
        ("Database models", "db_models.py"),
        ("Config module", "config.py"),
        ("Migration file", "migrations/versions/4fd7215c8370_create_core_contexts_table_and_helper_.py"),
        
        # Bootstrap script
        ("Bootstrap script", "scripts/db-bootstrap.py"),
        
        # Helm chart
        ("Helm Chart.yaml", "helm/context-service/Chart.yaml"),
        ("Helm values.yaml", "helm/context-service/values.yaml"),
        ("Helm helpers", "helm/context-service/templates/_helpers.tpl"),
        ("Helm deployment", "helm/context-service/templates/deployment.yaml"),
        ("Helm service", "helm/context-service/templates/service.yaml"),
        ("Helm service account", "helm/context-service/templates/serviceaccount.yaml"),
        ("Helm post-install job", "helm/context-service/templates/post-install-job.yaml"),
        
        # Documentation
        ("Database setup docs", "DATABASE_SETUP.md"),
        ("Updated Makefile", "Makefile"),
    ]
    
    print("\n📁 File and Directory Checks:")
    print("-" * 40)
    
    for description, filepath in checks:
        total_checks += 1
        if check_file_exists(filepath, description):
            success_count += 1
    
    # Check if bootstrap script is executable
    total_checks += 1
    bootstrap_script = Path("scripts/db-bootstrap.py")
    if bootstrap_script.exists() and os.access(bootstrap_script, os.X_OK):
        print("✅ Bootstrap script is executable")
        success_count += 1
    else:
        print("❌ Bootstrap script is not executable")
    
    # Check if requirements include alembic
    total_checks += 1
    try:
        with open("requirements.in", "r") as f:
            requirements = f.read()
            if "alembic" in requirements:
                print("✅ Alembic in requirements.in")
                success_count += 1
            else:
                print("❌ Alembic not found in requirements.in")
    except FileNotFoundError:
        print("❌ requirements.in not found")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Verification Results: {success_count}/{total_checks} checks passed")
    
    if success_count == total_checks:
        print("🎉 All components are in place! Database bootstrap setup is complete.")
        print("\n🚀 Next steps:")
        print("   1. Ensure PostgreSQL is running")
        print("   2. Set up database credentials in environment variables")
        print("   3. Run 'make local-run' to test the bootstrap process")
        print("   4. Deploy with 'helm install context-service ./helm/context-service'")
        return 0
    else:
        print("⚠️  Some components are missing. Please check the failed items above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
