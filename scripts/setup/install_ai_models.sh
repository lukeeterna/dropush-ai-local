#!/bin/bash
set -e  # Exit on error

echo "🚀 Installing AI models for Dropush..."
echo "================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    exit 1
fi

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker exec dropush-ollama ollama list > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    echo "  Attempt $((attempt+1))/$max_attempts..."
    sleep 2
    attempt=$((attempt+1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Error: Ollama service not ready after 60 seconds"
    exit 1
fi

# Function to install model with retry
install_model() {
    local model=$1
    local purpose=$2
    local max_retries=3
    local retry=0
    
    echo ""
    echo "📥 Installing $model for $purpose..."
    
    while [ $retry -lt $max_retries ]; do
        if docker exec dropush-ollama ollama pull $model; then
            echo "✅ $model installed successfully!"
            return 0
        fi
        retry=$((retry+1))
        echo "⚠️  Retry $retry/$max_retries for $model..."
        sleep 5
    done
    
    echo "❌ Failed to install $model after $max_retries attempts"
    return 1
}

# Install models
install_model "llama3.2:3b" "general AI tasks (product descriptions, analysis)"
install_model "nomic-embed-text" "embeddings (semantic search, similarity)"
install_model "codellama:7b" "code generation (automation scripts, integrations)"

# Verify installations
echo ""
echo "🔍 Verifying installed models..."
installed_models=$(docker exec dropush-ollama ollama list 2>/dev/null || echo "")

echo ""
echo "📋 Installed models:"
echo "$installed_models"

# Check if all required models are installed
required_models=("llama3.2:3b" "nomic-embed-text" "codellama:7b")
missing_models=()

for model in "${required_models[@]}"; do
    if ! echo "$installed_models" | grep -q "$model"; then
        missing_models+=("$model")
    fi
done

if [ ${#missing_models[@]} -eq 0 ]; then
    echo ""
    echo "✅ All AI models installed successfully!"
    echo ""
    echo "🎯 Models available:"
    echo "  - llama3.2:3b (general purpose, product descriptions)"
    echo "  - nomic-embed-text (semantic search, similarity)"
    echo "  - codellama:7b (automation scripts, integrations)"
    echo ""
    echo "Ready to process dropshipping tasks with local AI!"
else
    echo ""
    echo "⚠️  Warning: Some models may not have installed correctly:"
    for model in "${missing_models[@]}"; do
        echo "  - $model"
    done
    echo ""
    echo "You can manually install them later with:"
    echo "  docker exec dropush-ollama ollama pull <model_name>"
fi
