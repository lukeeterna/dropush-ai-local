#!/usr/bin/env python3
"""
Multi-Store OAuth Wizard
Enterprise-ready implementation for connecting multiple eBay stores.
"""

import os
import sys
import json
import sqlite3
import logging
import secrets
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
from flask import Flask, request, redirect, jsonify

# Setup paths
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiStoreOAuthWizard:
    """Enterprise OAuth wizard for multiple eBay stores."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.db_path = PROJECT_ROOT / "data" / "sqlite" / "dropush.db"
        self.config_path = PROJECT_ROOT / "config" / "ebay_oauth.json"
        
        # Load eBay OAuth config
        self.config = self._load_config()
        
        # Flask app for OAuth callback
        self.app = Flask(__name__)
        self._setup_routes()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load eBay OAuth configuration."""
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            return {}
            
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _setup_routes(self):
        """Setup Flask routes for OAuth callback."""
        
        @self.app.route('/oauth/callback')
        def oauth_callback():
            """Handle OAuth callback from eBay."""
            code = request.args.get('code')
            state = request.args.get('state')
            
            if not code:
                return "Error: No authorization code received", 400
            
            # Exchange code for tokens
            tokens = self._exchange_code_for_tokens(code)
            
            if tokens:
                # Save tokens to database
                store_name = self._get_store_from_state(state)
                self._save_tokens(store_name, tokens)
                
                return f"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: green;">✅ Store Connected Successfully!</h1>
                    <p>Store: <strong>{store_name}</strong></p>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
                """
            else:
                return "Error: Failed to exchange code for tokens", 500
    
    def add_store(self, store_name: str, ebay_username: str):
        """Add a new store and initiate OAuth flow."""
        logger.info(f"Adding store: {store_name} ({ebay_username})")
        
        # Check if store already exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM stores WHERE store_name = ? OR ebay_username = ?", 
                      (store_name, ebay_username))
        if cursor.fetchone():
            logger.error("Store already exists!")
            conn.close()
            return False
        
        # Insert new store
        cursor.execute("""
            INSERT INTO stores (store_name, ebay_username) 
            VALUES (?, ?)
        """, (store_name, ebay_username))
        
        store_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate OAuth URL
        state = f"{store_name}:{secrets.token_urlsafe(16)}"
        oauth_url = self._generate_oauth_url(state)
        
        print(f"\n🔗 Please visit this URL to authorize the store:")
        print(f"\n{oauth_url}\n")
        
        # Try to open in browser
        try:
            webbrowser.open(oauth_url)
            print("✅ Browser opened automatically")
        except:
            print("⚠️  Please open the URL manually in your browser")
        
        return True
    
    def _generate_oauth_url(self, state: str) -> str:
        """Generate eBay OAuth authorization URL."""
        params = {
            'client_id': self.config.get('client_id'),
            'response_type': 'code',
            'redirect_uri': self.config.get('redirect_uri', 'http://localhost:8080/oauth/callback'),
            'scope': self.config.get('scopes', 'https://api.ebay.com/oauth/api_scope'),
            'state': state
        }
        
        base_url = 'https://auth.ebay.com/oauth2/authorize'
        return f"{base_url}?{urlencode(params)}"
    
    def _exchange_code_for_tokens(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access tokens."""
        url = 'https://api.ebay.com/identity/v1/oauth2/token'
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self._get_basic_auth()}'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.config.get('redirect_uri', 'http://localhost:8080/oauth/callback')
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return None
    
    def _get_basic_auth(self) -> str:
        """Get Basic auth string for eBay API."""
        import base64
        credentials = f"{self.config.get('client_id')}:{self.config.get('client_secret')}"
        return base64.b64encode(credentials.encode()).decode()
    
    def _get_store_from_state(self, state: str) -> str:
        """Extract store name from state parameter."""
        return state.split(':')[0] if ':' in state else state
    
    def _save_tokens(self, store_name: str, tokens: Dict[str, Any]):
        """Save OAuth tokens to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get store ID
        cursor.execute("SELECT id FROM stores WHERE store_name = ?", (store_name,))
        store_id = cursor.fetchone()[0]
        
        # Calculate expiration times
        now = datetime.now()
        access_expires = now + timedelta(seconds=tokens.get('expires_in', 7200))
        refresh_expires = now + timedelta(days=365)  # eBay refresh tokens last ~18 months
        
        # Save tokens
        cursor.execute("""
            INSERT OR REPLACE INTO oauth_tokens 
            (store_id, access_token, refresh_token, token_expires_at, refresh_expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (store_id, tokens['access_token'], tokens.get('refresh_token'), 
              access_expires, refresh_expires))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Tokens saved for store: {store_name}")
    
    def list_stores(self) -> List[Dict[str, Any]]:
        """List all configured stores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.id, s.store_name, s.ebay_username, s.status, 
                   s.total_listings, s.total_sales,
                   t.token_expires_at
            FROM stores s
            LEFT JOIN oauth_tokens t ON s.id = t.store_id
            ORDER BY s.created_at DESC
        """)
        
        stores = []
        for row in cursor.fetchall():
            stores.append({
                'id': row[0],
                'store_name': row[1],
                'ebay_username': row[2],
                'status': row[3],
                'total_listings': row[4],
                'total_sales': row[5],
                'token_valid': row[6] and datetime.fromisoformat(row[6]) > datetime.now()
            })
        
        conn.close()
        return stores
    
    def run_server(self, port: int = 8080):
        """Run OAuth callback server."""
        logger.info(f"Starting OAuth callback server on port {port}")
        self.app.run(host='localhost', port=port, debug=False)


def main():
    """Main CLI interface."""
    wizard = MultiStoreOAuthWizard()
    
    print("🏪 Dropush Multi-Store OAuth Wizard")
    print("===================================")
    
    while True:
        print("\nOptions:")
        print("1. Add new store")
        print("2. List stores")
        print("3. Start OAuth server")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            store_name = input("Store name: ").strip()
            ebay_username = input("eBay username: ").strip()
            
            if store_name and ebay_username:
                wizard.add_store(store_name, ebay_username)
            else:
                print("❌ Store name and username are required!")
                
        elif choice == '2':
            stores = wizard.list_stores()
            if stores:
                print("\n📋 Configured Stores:")
                for store in stores:
                    token_status = "✅" if store['token_valid'] else "❌"
                    print(f"  - {store['store_name']} ({store['ebay_username']}) "
                          f"Token: {token_status} | "
                          f"Listings: {store['total_listings']} | "
                          f"Sales: €{store['total_sales']:.2f}")
            else:
                print("\n❌ No stores configured yet")
                
        elif choice == '3':
            print("\n🚀 Starting OAuth server...")
            print("Keep this running while adding stores!")
            wizard.run_server()
            
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    main()
