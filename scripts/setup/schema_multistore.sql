-- Dropush AI Local - Multi-Store Database Schema
-- Enterprise-ready schema for managing multiple eBay stores

-- Stores table
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT UNIQUE NOT NULL,
    ebay_username TEXT UNIQUE NOT NULL,
    site_code TEXT DEFAULT 'EBAY_IT',
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'inactive')),
    daily_listing_limit INTEGER DEFAULT 5,
    current_listings_today INTEGER DEFAULT 0,
    last_listing_reset DATE,
    total_listings INTEGER DEFAULT 0,
    total_sales REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- OAuth tokens table
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);

-- Business policies table
CREATE TABLE IF NOT EXISTS business_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    policy_type TEXT NOT NULL CHECK(policy_type IN ('payment', 'shipping', 'return')),
    policy_name TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    UNIQUE(store_id, policy_type, policy_name)
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('amazon', 'cj', 'eprolo')),
    source_id TEXT NOT NULL,
    source_url TEXT,
    source_price REAL NOT NULL,
    ebay_price REAL NOT NULL,
    margin_percent REAL NOT NULL,
    category_id TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'listed', 'sold', 'inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Listings table
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    ebay_item_id TEXT UNIQUE,
    listing_status TEXT DEFAULT 'active' CHECK(listing_status IN ('active', 'ended', 'sold', 'error')),
    views INTEGER DEFAULT 0,
    watchers INTEGER DEFAULT 0,
    questions INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    ebay_order_id TEXT UNIQUE NOT NULL,
    buyer_username TEXT NOT NULL,
    sale_price REAL NOT NULL,
    shipping_cost REAL NOT NULL,
    ebay_fees REAL NOT NULL,
    source_cost REAL NOT NULL,
    profit REAL NOT NULL,
    order_status TEXT DEFAULT 'pending' CHECK(order_status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    tracking_number TEXT,
    carrier TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

-- Store performance metrics
CREATE TABLE IF NOT EXISTS store_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    metric_date DATE NOT NULL,
    listings_created INTEGER DEFAULT 0,
    orders_received INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0,
    profit REAL DEFAULT 0,
    conversion_rate REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    UNIQUE(store_id, metric_date)
);

-- AI processing queue
CREATE TABLE IF NOT EXISTS ai_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL CHECK(task_type IN ('title_optimization', 'description_generation', 'price_analysis', 'image_enhancement')),
    product_id INTEGER,
    input_data TEXT NOT NULL,
    output_data TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    model_used TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_stores_status ON stores(status);
CREATE INDEX idx_stores_username ON stores(ebay_username);
CREATE INDEX idx_listings_store ON listings(store_id);
CREATE INDEX idx_listings_status ON listings(listing_status);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_ai_queue_status ON ai_queue(status);

-- Create triggers for updated_at
CREATE TRIGGER update_stores_timestamp 
AFTER UPDATE ON stores
BEGIN
    UPDATE stores SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_oauth_tokens_timestamp 
AFTER UPDATE ON oauth_tokens
BEGIN
    UPDATE oauth_tokens SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_products_timestamp 
AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Insert system info
INSERT OR REPLACE INTO system_info (id, version) VALUES (1, '1.0.0');
