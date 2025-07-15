# Dropush AI Local - Enterprise Makefile
# Professional build and management commands

.PHONY: help setup start stop restart status logs clean backup test multistore-init multistore-wizard

# Default command
help:
	@echo "Dropush AI Local - Enterprise Commands"
	@echo "====================================="
	@echo ""
	@echo "Setup & Deployment:"
	@echo "  make setup              - Complete system setup"
	@echo "  make start              - Start all services"
	@echo "  make stop               - Stop all services"
	@echo "  make restart            - Restart all services"
	@echo ""
	@echo "Multi-Store:"
	@echo "  make multistore-init    - Initialize multi-store database"
	@echo "  make multistore-wizard  - Run store connection wizard"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status             - Check system status"
	@echo "  make logs               - View all logs"
	@echo "  make health             - Run health check"
	@echo ""
	@echo "Maintenance:"
	@echo "  make backup             - Backup data"
	@echo "  make clean              - Clean temporary files"
	@echo "  make test               - Run all tests"
	@echo ""

# Complete setup
setup:
	@bash scripts/setup/setup.sh

# Start services
start:
	@cd docker && docker-compose up -d
	@echo "✅ Services started"
	@echo "n8n: http://localhost:5678"

# Stop services
stop:
	@cd docker && docker-compose down
	@echo "✅ Services stopped"

# Restart services
restart: stop start

# Check status
status:
	@echo "🔍 System Status"
	@echo "==============="
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@bash scripts/monitoring/health_check.sh

# View logs
logs:
	@docker-compose -f docker/docker-compose.yml logs -f --tail=100

# Health check
health:
	@bash scripts/monitoring/health_check.sh

# Backup
backup:
	@bash scripts/backup/backup.sh

# Initialize multi-store database
multistore-init:
	@echo "🏪 Initializing Multi-Store Database..."
	@chmod +x scripts/setup/init_multistore_db.sh
	@bash scripts/setup/init_multistore_db.sh

# Run multi-store wizard
multistore-wizard:
	@echo "🧙 Starting Multi-Store Connection Wizard..."
	@python3 scripts/multistore/oauth_wizard.py

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

# Run tests
test:
	@echo "🧪 Running tests..."
	@cd scripts/setup && python test_setup.py -v
	@cd scripts/backup && python test_backup.py -v
	@cd scripts/monitoring && python test_health_check.py -v
