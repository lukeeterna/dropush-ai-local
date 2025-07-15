#!/bin/bash
# Initialize Multi-Store Database
# Enterprise-ready, path-agnostic implementation

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Main function
main() {
    cd "$PROJECT_ROOT"
    
    log_info "Initializing Multi-Store Database..."
    
    # Backup existing database if exists
    if [ -f "data/sqlite/dropush.db" ]; then
        backup_file="data/backups/dropush_$(date +%Y%m%d_%H%M%S).db"
        mkdir -p data/backups
        cp data/sqlite/dropush.db "$backup_file"
        log_info "Backed up existing database to $backup_file"
    fi
    
    # Create database directory
    mkdir -p data/sqlite
    
    # Initialize database with multi-store schema
    if [ -f "scripts/setup/schema_multistore.sql" ]; then
        sqlite3 data/sqlite/dropush.db < scripts/setup/schema_multistore.sql
        log_info "Multi-store schema applied successfully"
    else
        log_error "schema_multistore.sql not found!"
        exit 1
    fi
    
    # Set permissions
    chmod 644 data/sqlite/dropush.db
    
    # Verify tables
    log_info "Verifying database tables..."
    tables=$(sqlite3 data/sqlite/dropush.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    echo -e "${GREEN}Tables created:${NC}"
    echo "$tables" | while read table; do
        echo "  - $table"
    done
    
    log_info "Multi-store database initialized successfully!"
}

# Execute
main "$@"
