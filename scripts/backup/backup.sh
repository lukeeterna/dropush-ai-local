#!/bin/bash
# Automated backup script for Dropush AI Local

BACKUP_DIR="/Volumes/HD_1TB/dropush-backups"
SOURCE_DIR="/Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup SQLite database
echo "📊 Backing up database..."
cp "$SOURCE_DIR/data/sqlite/dropush.db" "$BACKUP_DIR/$DATE/"

# Backup n8n workflows
echo "🔄 Backing up n8n workflows..."
docker exec dropush-n8n n8n export:workflow --all --output=/data/workflows_backup.json
cp "$SOURCE_DIR/data/workflows_backup.json" "$BACKUP_DIR/$DATE/"

# Backup configurations
echo "⚙️ Backing up configurations..."
cp -r "$SOURCE_DIR/config" "$BACKUP_DIR/$DATE/"

# Create tarball
echo "📦 Creating archive..."
cd "$BACKUP_DIR"
tar -czf "dropush_backup_$DATE.tar.gz" "$DATE"
rm -rf "$DATE"

# Cleanup old backups (keep last 30 days)
echo "🧹 Cleaning old backups..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

# Optional: sync to Google Drive
# rclone copy "$BACKUP_DIR/dropush_backup_$DATE.tar.gz" gdrive:dropush-backups/

echo "✅ Backup completed: dropush_backup_$DATE.tar.gz"

# Log backup completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed: dropush_backup_$DATE.tar.gz" >> "$SOURCE_DIR/data/logs/backup.log"
