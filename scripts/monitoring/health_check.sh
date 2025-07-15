#!/bin/bash
# Health monitoring script for Dropush AI Local

WEBHOOK_URL="http://localhost:5678/webhook/health-check"
DB_PATH="/Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/data/sqlite/dropush.db"
LOG_FILE="/Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/data/logs/health_check.log"

# Check services
echo "🔍 Checking service health..."
n8n_status=$(docker inspect dropush-n8n --format='{{.State.Status}}' 2>/dev/null || echo "not_running")
ollama_status=$(docker inspect dropush-ollama --format='{{.State.Status}}' 2>/dev/null || echo "not_running")
nginx_status=$(docker inspect dropush-nginx --format='{{.State.Status}}' 2>/dev/null || echo "not_running")

# Check disk space
disk_usage=$(df -h /Volumes/mact7 | awk 'NR==2 {print $5}' | sed 's/%//')

# Check database size
db_size=$(du -h "$DB_PATH" 2>/dev/null | cut -f1 || echo "0")

# Check memory usage
memory_usage=$(ps aux | awk 'BEGIN {sum=0} {sum+=$6} END {print sum/1024}')

# Create status JSON
status_json=$(cat <<JSON
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "services": {
    "n8n": "$n8n_status",
    "ollama": "$ollama_status",
    "nginx": "$nginx_status"
  },
  "disk_usage_percent": $disk_usage,
  "database_size": "$db_size",
  "memory_usage_mb": $memory_usage,
  "status": "healthy"
}
JSON
)

# Determine overall health
if [[ "$n8n_status" != "running" ]] || [[ "$ollama_status" != "running" ]]; then
    status_json=$(echo "$status_json" | sed 's/"status": "healthy"/"status": "unhealthy"/')
fi

if [[ $disk_usage -gt 90 ]]; then
    status_json=$(echo "$status_json" | sed 's/"status": "healthy"/"status": "warning"/')
fi

# Send to n8n webhook (if n8n is running)
if [[ "$n8n_status" == "running" ]]; then
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$status_json" \
      --silent --output /dev/null --show-error
fi

# Log locally
echo "$status_json" >> "$LOG_FILE"

# Print summary for cron logs
echo "Health check completed: n8n=$n8n_status, ollama=$ollama_status, disk=$disk_usage%"

# Send alert if unhealthy
if [[ "$status_json" == *'"status": "unhealthy"'* ]]; then
    echo "⚠️ ALERT: System unhealthy! Check logs for details."
fi
