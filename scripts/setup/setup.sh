#!/bin/bash
set -e

echo "🚀 Dropush AI Local Setup"
echo "========================"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker required but not installed. Aborting." >&2; exit 1; }
command -v sqlite3 >/dev/null 2>&1 || { echo "SQLite3 required but not installed. Aborting." >&2; exit 1; }

# Create .env from template
if [ ! -f "docker/.env" ]; then
    cp docker/.env.template docker/.env
    echo "⚠️  Please edit docker/.env with your API credentials"
    exit 1
fi

# Initialize database
echo "📊 Initializing database..."
cd scripts/setup && ./init_db.sh && cd ../..

# Start services
echo "🐳 Starting Docker services..."
cd docker && docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 30

# Install AI models
echo "🤖 Installing AI models..."
cd ../scripts/setup && ./install_ai_models.sh && cd ../..

# Setup cron jobs
echo "⏰ Setting up cron jobs..."
(crontab -l 2>/dev/null; echo "0 2 * * * /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/scripts/backup/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/15 * * * * /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/scripts/monitoring/health_check.sh") | crontab -

echo "✅ Setup complete!"
echo ""
echo "Access n8n at: http://localhost:5678"
echo "Default credentials: admin / (your password)"
echo ""
echo "Next steps:"
echo "1. Import workflow templates from n8n/workflows/"
echo "2. Configure store credentials in n8n"
echo "3. Test order webhook at http://localhost:5678/webhook/order-webhook"
