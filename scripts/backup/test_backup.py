#!/usr/bin/env python3
"""
Test for backup.sh
"""

import os
import subprocess
import pytest

def test_backup_script_exists():
    """Test that backup.sh exists"""
    assert os.path.exists('backup.sh')

def test_backup_script_is_executable():
    """Test that backup.sh is executable"""
    assert os.access('backup.sh', os.X_OK)

def test_backup_script_syntax():
    """Test bash script syntax"""
    result = subprocess.run(['bash', '-n', 'backup.sh'], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr}"

def test_backup_script_has_shebang():
    """Test that script has proper shebang"""
    with open('backup.sh', 'r') as f:
        first_line = f.readline().strip()
    assert first_line == '#!/bin/bash'

def test_backup_paths_defined():
    """Test that backup paths are properly defined"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'BACKUP_DIR=' in content
    assert 'SOURCE_DIR=' in content
    assert '/Volumes/' in content  # External drives

def test_backup_includes_database():
    """Test that database backup is included"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'dropush.db' in content
    assert 'Backing up database' in content

def test_backup_includes_workflows():
    """Test that n8n workflows are backed up"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'n8n export:workflow' in content
    assert 'workflows_backup.json' in content

def test_backup_creates_archive():
    """Test that backup creates compressed archive"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'tar -czf' in content
    assert '.tar.gz' in content

def test_backup_cleans_old_files():
    """Test that old backups are cleaned"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'find' in content
    assert '-mtime +30' in content
    assert '-delete' in content

def test_backup_logs_completion():
    """Test that backup logs its completion"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'backup.log' in content
    assert 'Backup completed' in content

def test_backup_has_date_stamp():
    """Test that backup uses timestamps"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    assert 'date +%Y%m%d_%H%M%S' in content
    assert '$DATE' in content

def test_no_mock_data():
    """Test that script has no mock/hardcoded data"""
    with open('backup.sh', 'r') as f:
        content = f.read()
    
    # Check for common mock data patterns
    assert 'MEGA_TREASURE_SHOP' not in content
    assert 'test_backup' not in content
    assert 'dummy' not in content.lower()
    assert 'mock' not in content.lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
