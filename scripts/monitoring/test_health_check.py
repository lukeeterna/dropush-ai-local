#!/usr/bin/env python3
"""
Test for health_check.sh
"""

import os
import subprocess
import pytest
import json

def test_health_check_script_exists():
    """Test that health_check.sh exists"""
    assert os.path.exists('health_check.sh')

def test_health_check_script_is_executable():
    """Test that health_check.sh is executable"""
    assert os.access('health_check.sh', os.X_OK)

def test_health_check_script_syntax():
    """Test bash script syntax"""
    result = subprocess.run(['bash', '-n', 'health_check.sh'], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr}"

def test_health_check_script_has_shebang():
    """Test that script has proper shebang"""
    with open('health_check.sh', 'r') as f:
        first_line = f.readline().strip()
    assert first_line == '#!/bin/bash'

def test_checks_all_services():
    """Test that script checks all required services"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'dropush-n8n' in content
    assert 'dropush-ollama' in content
    assert 'dropush-nginx' in content
    assert 'docker inspect' in content

def test_checks_disk_usage():
    """Test that script monitors disk usage"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'df -h' in content
    assert 'disk_usage' in content

def test_checks_database_size():
    """Test that script monitors database size"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'dropush.db' in content
    assert 'du -h' in content

def test_checks_memory_usage():
    """Test that script monitors memory usage"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'memory_usage' in content
    assert 'ps aux' in content

def test_creates_json_status():
    """Test that script creates JSON status"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'status_json' in content
    assert '"timestamp"' in content
    assert '"services"' in content
    assert '"status"' in content

def test_sends_webhook():
    """Test that script sends webhook to n8n"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'WEBHOOK_URL=' in content
    assert 'curl -X POST' in content
    assert 'Content-Type: application/json' in content

def test_logs_locally():
    """Test that script logs to local file"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'health_check.log' in content
    assert '>>' in content  # Append to log

def test_handles_service_failures():
    """Test that script handles service failures"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'not_running' in content
    assert 'unhealthy' in content

def test_alerts_on_high_disk_usage():
    """Test that script alerts on high disk usage"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert '-gt 90' in content  # Disk usage > 90%
    assert 'warning' in content

def test_prints_summary():
    """Test that script prints summary for cron"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    assert 'Health check completed' in content
    assert 'echo' in content

def test_no_mock_data():
    """Test that script has no mock/hardcoded data"""
    with open('health_check.sh', 'r') as f:
        content = f.read()
    
    # Check for common mock data patterns
    assert 'MEGA_TREASURE_SHOP' not in content
    assert 'test_webhook' not in content
    assert 'dummy' not in content.lower()
    assert 'mock' not in content.lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
