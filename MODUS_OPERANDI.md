📋 Modus Operandi per Sessioni Dropush Enterprise
🔄 Workflow per Ogni Sessione

Start: Verifica lo stato del progetto
bashcat PRODUCTION_ROADMAP.md
cat production_modules_status.json

Prendi in analisi come base i files esistenti nel progetto dropush chiedendo sempre la path e ls per verificare i nomi dei files, poi analizzali con i comandi grep e sed.

Plan: Identifica il prossimo modulo da validare

Verifica quali dipendenze sono già validate
Controlla la roadmap per identificare la priorità


Fix: Risolvi problemi in un modulo alla volta

Fai backup prima di ogni modifica
Testa ogni modifica in isolamento
Verifica sintassi con python -m py_compile


Validate: Usa script di validazione

Esegui script di test dedicato
Verifica funzionamento end-to-end
Documenta risultati


Integrate: Aggiungi il modulo validato a production_ready
bashpython scripts/organize_production_modules.py

Document: Aggiorna la roadmap e lo stato

Aggiorna PRODUCTION_ROADMAP.md
Aggiorna documentazione del modulo



🛠️ Comandi Utili

### Verifica e Test
```bash
# Verifica Sintassi
python -m py_compile src/path/to/module.py && echo "✅ Sintassi OK"

# Test Modulo
python scripts/test_module.py path/to/module.py

# Test con pytest
python -m pytest tests/test_module_name.py -v
```

### Backup e Organizzazione
```bash
# Backup Modulo
cp src/path/to/module.py src/path/to/module.py.backup_$(date +%Y%m%d_%H%M%S)

# Organizza Moduli Produzione
python scripts/organize_production_modules.py
```

### 🚀 Deploy su T7 e GitHub
```bash
# 1. SEMPRE verificare prima quali file esistono
ls -la src/core/
ls -la src/listing/
ls -la tests/

# 2. Crea le directory su T7
mkdir -p /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core
mkdir -p /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing
mkdir -p /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/tests

# 3. Copia i moduli core ESISTENTI (esempio per Listing Automation)
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/listing_config.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/dependencies.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/cache_system.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/retry_manager.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/error_handling.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/monitoring.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/

# 4. Copia i moduli listing ESISTENTI
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/ai_optimizer.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/template_engine.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/template_factory.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/publisher.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/ebay_publisher.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/queue_manager.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/sales_predictor.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/batch_processor.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/gpu_optimizer.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/

# 5. Copia i file __init__.py
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/core/__init__.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/core/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/src/listing/__init__.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/listing/

# 6. Copia i test
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/tests/test_listing_automation.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/tests/

# 7. Copia file di supporto
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/.env.listing.test /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/
cp /Users/gianlucadistasi/Desktop/dropshipping-ai/dropush-enterprise/test_system_ready.py /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/

# 8. Git add, commit e push
cd /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local
git add src/core/*.py src/listing/*.py tests/test_listing_automation.py .env.listing.test test_system_ready.py
git commit -m "Add validated Listing Automation module with AI optimizer, template engine and publishers - all tests passing"
git push origin main
```

### ⚠️ IMPORTANTE: Verifica File Prima di Copiare
```bash
# SEMPRE verificare esistenza file PRIMA di dare comandi cp
find src/ -name "*.py" -type f | grep -E "(core|listing)" | sort

# Verificare cosa è già stato copiato
ls -la /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/src/
```

📊 Stato Avanzamento
Mantenere aggiornato lo stato del progetto:
bash# Aggiorna roadmap
python scripts/update_roadmap.py

# Genera report avanzamento
python scripts/generate_progress_report.py
📝 Regole Fondamentali

Un modulo alla volta: Concentrarsi su un singolo modulo per sessione
Verifica sempre: Testare ogni modifica prima di procedere
Documenta tutto: Aggiornare documentazione e roadmap
Backup prima di modificare: Sempre fare backup prima di modifiche
Commit validati: Solo i moduli validati vanno in produzione
A fine sessione fornisci sempre prompt con primo comando :cat PRODUCTION_ROADMAP.md && cat MODUS_OPERANDI.md
