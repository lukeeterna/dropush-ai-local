#!/usr/bin/env python3
"""
Test for install_ai_models.sh
"""

import os
import subprocess
import pytest

def test_install_ai_models_script_exists():
    """Test that install_ai_models.sh exists"""
    assert os.path.exists('install_ai_models.sh')

def test_install_ai_models_script_is_executable():
    """Test that install_ai_models.sh is executable"""
    assert os.access('install_ai_models.sh', os.X_OK)

def test_install_ai_models_script_syntax():
    """Test bash script syntax"""
    result = subprocess.run(['bash', '-n', 'install_ai_models.sh'], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr}"

def test_install_ai_models_script_has_shebang():
    """Test that script has proper shebang"""
    with open('install_ai_models.sh', 'r') as f:
        first_line = f.readline().strip()
    assert first_line == '#!/bin/bash'

def test_script_installs_required_models():
    """Test that script installs all required models"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    # Check for required models
    assert 'llama3.2:3b' in content
    assert 'nomic-embed-text' in content
    assert 'codellama:7b' in content

def test_script_uses_docker_exec():
    """Test that script uses docker exec correctly"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    assert 'docker exec dropush-ollama' in content
    assert 'ollama pull' in content

def test_script_waits_for_service():
    """Test that script waits for Ollama to be ready"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    assert 'sleep' in content
    assert 'Waiting for Ollama' in content

def test_script_verifies_installation():
    """Test that script verifies model installation"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    assert 'ollama list' in content
    assert 'Verifying installed models' in content

def test_script_has_informative_output():
    """Test that script provides user feedback"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    assert 'Installing AI models' in content
    assert 'successfully' in content
    assert 'Models available:' in content

def test_script_documents_model_purposes():
    """Test that script documents what each model is for"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    assert 'general purpose' in content
    assert 'embeddings' in content
    assert 'code generation' in content

def test_no_mock_data():
    """Test that script has no mock/hardcoded data"""
    with open('install_ai_models.sh', 'r') as f:
        content = f.read()
    
    # Check for common mock data patterns
    assert 'MEGA_TREASURE_SHOP' not in content
    assert 'test_' not in content.lower()
    assert 'dummy' not in content.lower()
    assert 'mock' not in content.lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
