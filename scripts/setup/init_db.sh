#!/bin/bash
# Database initialization script for Dropush AI Local

DB_PATH="/Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/data/sqlite/dropush.db"
DB_DIR=$(dirname "$DB_PATH")
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "🗄️  Initializing Dropush database..."

# Create database directory if it doesn't exist
if [ ! -d "$DB_DIR" ]; then
    echo "Creating database directory..."
    mkdir -p "$DB_DIR"
fi

# Check if database already exists
if [ -f "$DB_PATH" ]; then
    echo "⚠️  Database already exists at $DB_PATH"
    read -p "Do you want to backup and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup existing database
        BACKUP_FILE="${DB_PATH}.backup_$(date +%Y%m%d_%H%M%S)"
        echo "📦 Creating backup at $BACKUP_FILE"
        cp "$DB_PATH" "$BACKUP_FILE"
        rm "$DB_PATH"
    else
        echo "Keeping existing database."
        exit 0
    fi
fi

# Create new database
echo "📊 Creating new database..."
if [ -f "$SCRIPT_DIR/init_database.sql" ]; then
    sqlite3 "$DB_PATH" < "$SCRIPT_DIR/init_database.sql"
    
    if [ $? -eq 0 ]; then
        echo "✅ Database created successfully!"
        
        # Set permissions
        chmod 644 "$DB_PATH"
        
        # Show database info
        echo ""
        echo "📋 Database Information:"
        echo "  - Location: $DB_PATH"
        echo "  - Size: $(du -h "$DB_PATH" | cut -f1)"
        
        # Count tables
        TABLE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        echo "  - Tables: $TABLE_COUNT"
        
        # Count views
        VIEW_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='view';")
        echo "  - Views: $VIEW_COUNT"
        
        # Count indexes
        INDEX_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
        echo "  - Indexes: $INDEX_COUNT"
        
        echo ""
        echo "🎉 Database initialization complete!"
    else
        echo "❌ Error creating database"
        exit 1
    fi
else
    echo "❌ Error: init_database.sql not found in $SCRIPT_DIR"
    exit 1
fi
