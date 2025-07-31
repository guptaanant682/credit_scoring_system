#!/usr/bin/env python3
"""
Project validation script to check if all required files are present
and the project structure is correct for the Credit Approval System.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print status"""
    if os.path.exists(file_path):
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: {file_path} - MISSING")
        return False

def validate_project_structure():
    """Validate the entire project structure"""
    print("=== Credit Approval System - Project Structure Validation ===\n")
    
    base_dir = Path(__file__).parent
    all_files_present = True
    
    # Core Django files
    required_files = [
        ("manage.py", "Django management script"),
        ("requirements.txt", "Python dependencies"),
        ("Dockerfile", "Docker container configuration"),
        ("docker-compose.yml", "Docker Compose configuration"),
        ("docker-entrypoint.sh", "Docker entrypoint script"),
        ("README.md", "Project documentation"),
        (".dockerignore", "Docker ignore file"),
        (".env.example", "Environment variables example"),
    ]
    
    # Django project files
    project_files = [
        ("credit_approval_system/__init__.py", "Django project init"),
        ("credit_approval_system/settings.py", "Django settings"),
        ("credit_approval_system/urls.py", "Django project URLs"),
        ("credit_approval_system/wsgi.py", "WSGI configuration"),
        ("credit_approval_system/asgi.py", "ASGI configuration"),
    ]
    
    # Django app files
    app_files = [
        ("credit_app/__init__.py", "App init"),
        ("credit_app/models.py", "Database models"),
        ("credit_app/views.py", "API views"),
        ("credit_app/urls.py", "App URLs"),
        ("credit_app/serializers.py", "DRF serializers"),
        ("credit_app/services.py", "Business logic services"),
        ("credit_app/admin.py", "Django admin"),
        ("credit_app/apps.py", "App configuration"),
        ("credit_app/tests.py", "Unit tests"),
        ("credit_app/management/__init__.py", "Management commands init"),
        ("credit_app/management/commands/__init__.py", "Commands init"),
        ("credit_app/management/commands/load_initial_data.py", "Data loading command"),
        ("credit_app/migrations/__init__.py", "Migrations init"),
    ]
    
    print("1. Core Project Files:")
    for file_path, description in required_files:
        full_path = base_dir / file_path
        if not check_file_exists(full_path, description):
            all_files_present = False
    
    print("\n2. Django Project Files:")
    for file_path, description in project_files:
        full_path = base_dir / file_path
        if not check_file_exists(full_path, description):
            all_files_present = False
    
    print("\n3. Django App Files:")
    for file_path, description in app_files:
        full_path = base_dir / file_path
        if not check_file_exists(full_path, description):
            all_files_present = False
    
    print("\n4. Data Files (Optional - will be loaded if present):")
    data_files = [
        ("customer_data.xlsx", "Customer data for ingestion"),
        ("loan_data.xlsx", "Loan data for ingestion"),
    ]
    
    for file_path, description in data_files:
        full_path = base_dir / file_path
        check_file_exists(full_path, description)
    
    print("\n" + "="*60)
    
    if all_files_present:
        print("✓ PROJECT STRUCTURE VALIDATION PASSED")
        print("\nTo start the application:")
        print("1. docker-compose up --build")
        print("2. Access API at http://localhost:8000")
        print("3. Access admin at http://localhost:8000/admin (admin/admin123)")
        return True
    else:
        print("✗ PROJECT STRUCTURE VALIDATION FAILED")
        print("Some required files are missing. Please check the output above.")
        return False

if __name__ == "__main__":
    success = validate_project_structure()
    sys.exit(0 if success else 1)