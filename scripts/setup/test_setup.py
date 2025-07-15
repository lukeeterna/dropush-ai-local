#!/usr/bin/env python3
"""
Test for setup.sh
"""

import os
import subprocess
import pytest

def test_setup_script_exists():
    """Test that setup.sh exists"""
    assert os.path.exists('setup.sh')

def test_setup_script_is_executable():
    """Test that setup.sh is executable"""
    assert os.access('setup.sh', os.X_OK)

def test_setup_script_syntax():
    """Test bash script syntax"""
    result = subprocess.run(['bash', '-n', 'setup.sh'], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr}"

def test_setup_script_has_shebang():
    """Test that script has proper shebang"""
    with open('setup.sh', 'r') as f:
        first_line = f.readline().strip()
    assert first_line == '#!/bin/bash'

def test_setup_script_checks_prerequisites():
    """Test that script checks for Docker and SQLite"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'command -v docker' in content
    assert 'command -v sqlite3' in content

def test_setup_script_has_error_handling():
    """Test that script has proper error handling"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'set -e' in content

def test_setup_script_creates_env():
    """Test that script handles .env creation"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert '.env.template' in content
    assert 'docker/.env' in content

def test_setup_script_initializes_database():
    """Test that script initializes database"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'init_db.sh' in content
    assert 'Initializing database' in content

def test_setup_script_starts_docker():
    """Test that script starts Docker services"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'docker-compose up -d' in content

def test_setup_script_installs_ai_models():
    """Test that script installs AI models"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'install_ai_models.sh' in content

def test_setup_script_sets_cron_jobs():
    """Test that script sets up cron jobs"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'crontab' in content
    assert 'backup.sh' in content
    assert 'health_check.sh' in content

def test_setup_script_has_completion_message():
    """Test that script has proper completion message"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    assert 'Setup complete!' in content
    assert 'http://localhost:5678' in content
    assert 'Next steps:' in content

def test_no_mock_data():
    """Test that script has no mock/hardcoded data"""
    with open('setup.sh', 'r') as f:
        content = f.read()
    # Check for common mock data patterns
    assert 'MEGA_TREASURE_SHOP' not in content
    assert 'test_store' not in content
    assert 'dummy' not in content.lower()
    assert 'mock' not in content.lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
