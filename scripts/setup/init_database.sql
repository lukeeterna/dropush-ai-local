-- Dropush AI Local Database Schema
-- SQLite database for dropshipping automation

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Stores table (eBay and Amazon)
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Listings table (products on eBay/Amazon)
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    store_id INTEGER REFERENCES stores(id),
    platform_listing_id TEXT,
    listing_url TEXT,
    price DECIMAL(10,2),
    quantity INTEGER,
    status TEXT CHECK(status IN ('active', 'inactive', 'out_of_stock')),
    last_sync DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    store_id INTEGER REFERENCES stores(id),
    platform_order_id TEXT,
    customer_email TEXT,
    total_amount DECIMAL(10,2),
    profit_margin DECIMAL(10,2),
    status TEXT CHECK(status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
    supplier_order_id TEXT,
    tracking_number TEXT,
    order_date DATETIME,
    ship_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    unit_cost DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Price history table
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    reason TEXT,
    changed_by TEXT DEFAULT 'ai_system',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    store_id INTEGER REFERENCES stores(id),
    revenue DECIMAL(10,2),
    profit DECIMAL(10,2),
    orders_count INTEGER,
    conversion_rate DECIMAL(5,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, store_id)
);

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT CHECK(level IN ('info', 'warning', 'error')),
    module TEXT,
    message TEXT,
    details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_listings_platform ON listings(platform_listing_id);
CREATE INDEX idx_analytics_date ON analytics(date);

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

-- Create views for reporting
CREATE VIEW IF NOT EXISTS v_active_listings AS
SELECT 
    l.id,
    p.sku,
    p.title,
    s.store_name,
    s.platform,
    l.price,
    l.quantity,
    l.status,
    l.last_sync
FROM listings l
JOIN products p ON l.product_id = p.id
JOIN stores s ON l.store_id = s.id
WHERE l.status = 'active' AND p.is_active = 1;

CREATE VIEW IF NOT EXISTS v_order_summary AS
SELECT 
    o.id,
    o.order_number,
    s.store_name,
    s.platform,
    o.total_amount,
    o.profit_margin,
    o.status,
    o.order_date,
    COUNT(oi.id) as item_count
FROM orders o
JOIN stores s ON o.store_id = s.id
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id;

CREATE VIEW IF NOT EXISTS v_product_performance AS
SELECT 
    p.id,
    p.sku,
    p.title,
    sup.name as supplier,
    COUNT(DISTINCT oi.order_id) as total_orders,
    SUM(oi.quantity) as total_sold,
    AVG(oi.unit_price - oi.unit_cost) as avg_profit
FROM products p
JOIN suppliers sup ON p.supplier_id = sup.id
LEFT JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id;

-- Sample data for testing (commented out for production)
-- INSERT INTO stores (platform, store_id, store_name) VALUES 
--     ('ebay', 'test_ebay_001', 'Test eBay Store'),
--     ('amazon', 'test_amz_001', 'Test Amazon Store');
