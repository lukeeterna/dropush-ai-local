-- Dropush AI Local Database Schema
-- Version: 3.0.0
-- Compatible with: SQLite 3.x
-- Path: /Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local/data/sqlite/dropush.db

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Stores table per eBay e Amazon
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL CHECK(platform IN ('ebay', 'amazon')),
    store_id TEXT UNIQUE NOT NULL,
    store_name TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at DATETIME,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Suppliers table (Amazon, CJ, Eprolo)
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(name IN ('amazon', 'cj', 'eprolo')),
    api_key TEXT,
    api_secret TEXT,
    is_active BOOLEAN DEFAULT 1,
    config JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    supplier_id INTEGER REFERENCES suppliers(id),
    supplier_sku TEXT,
    cost_price DECIMAL(10,2),
    suggested_price DECIMAL(10,2),
    current_stock INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    ai_optimized BOOLEAN DEFAULT 0,
    images JSON,
    attributes JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Listings table
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    store_id INTEGER REFERENCES stores(id),
    platform_listing_id TEXT,
    listing_url TEXT,
    price DECIMAL(10,2),
    quantity INTEGER,
    status TEXT CHECK(status IN ('active', 'inactive', 'out_of_stock', 'pending')),
    listing_data JSON,
    last_sync DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, store_id)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    store_id INTEGER REFERENCES stores(id),
    platform_order_id TEXT,
    customer_name TEXT,
    customer_email TEXT,
    shipping_address JSON,
    total_amount DECIMAL(10,2),
    shipping_cost DECIMAL(10,2),
    tax_amount DECIMAL(10,2),
    profit_margin DECIMAL(10,2),
    status TEXT CHECK(status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
    supplier_order_id TEXT,
    tracking_number TEXT,
    order_date DATETIME,
    ship_date DATETIME,
    delivery_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    unit_cost DECIMAL(10,2),
    item_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Price history table
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    reason TEXT,
    competitor_data JSON,
    changed_by TEXT DEFAULT 'ai_system',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Inventory snapshots
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER,
    supplier_quantity INTEGER,
    snapshot_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, snapshot_date)
);

-- Analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    store_id INTEGER REFERENCES stores(id),
    revenue DECIMAL(10,2) DEFAULT 0,
    profit DECIMAL(10,2) DEFAULT 0,
    orders_count INTEGER DEFAULT 0,
    items_sold INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5,2),
    avg_order_value DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, store_id)
);

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT CHECK(level IN ('debug', 'info', 'warning', 'error', 'critical')),
    module TEXT,
    message TEXT,
    details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Workflow runs per n8n
CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT NOT NULL,
    status TEXT CHECK(status IN ('running', 'success', 'failed')),
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    error_message TEXT,
    execution_data JSON
);

-- Create indexes for performance
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_supplier ON products(supplier_id);
CREATE INDEX idx_listings_platform ON listings(platform_listing_id);
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_analytics_date ON analytics(date);
CREATE INDEX idx_logs_level ON system_logs(level);
CREATE INDEX idx_logs_created ON system_logs(created_at);

-- Create triggers for updated_at
CREATE TRIGGER update_stores_timestamp 
AFTER UPDATE ON stores
BEGIN
    UPDATE stores SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_products_timestamp 
AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Insert default suppliers
INSERT OR IGNORE INTO suppliers (name, is_active) VALUES 
    ('amazon', 1),
    ('cj', 1),
    ('eprolo', 1);

-- Initial system log
INSERT INTO system_logs (level, module, message, details) VALUES 
    ('info', 'database', 'Database initialized successfully', 
     json_object('version', '3.0.0', 
                 'user', 'lukeeterna',
                 'path', '/Volumes/mact7/DROPUSH_PROJECT/dropush-ai-local'));
