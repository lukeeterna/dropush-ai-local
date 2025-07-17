"""
eBay Publisher implementation
Integra con eBay API esistente
"""
from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET
from datetime import datetime
from src.listing.publisher import BasePublisher, PublishResult, PublishStatus
from src.core.retry_manager import RetryManager

class EbayPublisher(BasePublisher):
    """Publisher per eBay con API Trading"""
    
    def __init__(self, config: Dict[str, Any], retry_manager: Optional[RetryManager] = None, ebay_client: Any = None):
        super().__init__(config, retry_manager)
        self.marketplace_name = "ebay"
        self.ebay_client = ebay_client
        
    async def validate_listing(self, listing: Dict[str, Any]) -> bool:
        """Valida listing per eBay"""
        required = ['title', 'description', 'price', 'category_id', 'condition']
        
        # Check required fields
        if not all(field in listing for field in required):
            return False
            
        # Validate title length (80 chars max)
        if len(listing['title']) > 80:
            return False
            
        # Validate price
        if listing['price'] <= 0:
            return False
            
        return True
        
    async def _do_publish(self, listing: Dict[str, Any]) -> PublishResult:
        """Pubblica su eBay via API"""
        try:
            # Prepare eBay XML
            xml_data = self._build_ebay_xml(listing)
            
            # Call eBay API
            response = await self.ebay_client.add_item(xml_data)
            
            if response.get('Ack') == 'Success':
                return PublishResult(
                    listing_id=response.get('ItemID'),
                    marketplace=self.marketplace_name,
                    status=PublishStatus.PUBLISHED,
                    url=f"https://www.ebay.it/itm/{response.get('ItemID')}",
                    published_at=datetime.now()
                )
            else:
                return PublishResult(
                    listing_id="",
                    marketplace=self.marketplace_name,
                    status=PublishStatus.FAILED,
                    error=response.get('Errors', {}).get('LongMessage', 'Unknown error')
                )
                
        except Exception as e:
            return PublishResult(
                listing_id="",
                marketplace=self.marketplace_name,
                status=PublishStatus.FAILED,
                error=str(e)
            )
            
    def _build_ebay_xml(self, listing: Dict[str, Any]) -> str:
        """Costruisce XML per eBay AddItem"""
        root = ET.Element("AddItemRequest")
        root.set("xmlns", "urn:ebay:apis:eBLBaseComponents")
        
        # Add required fields
        item = ET.SubElement(root, "Item")
        
        # Title
        title_elem = ET.SubElement(item, "Title")
        title_elem.text = listing['title']
        
        # Description
        desc_elem = ET.SubElement(item, "Description")
        desc_elem.text = f"<![CDATA[{listing['description']}]]>"
        
        # Category
        cat_elem = ET.SubElement(item, "PrimaryCategory")
        cat_id = ET.SubElement(cat_elem, "CategoryID")
        cat_id.text = str(listing['category_id'])
        
        # Price
        price_elem = ET.SubElement(item, "StartPrice")
        price_elem.text = str(listing['price'])
        price_elem.set("currencyID", "EUR")
        
        # Condition
        condition_elem = ET.SubElement(item, "ConditionID")
        condition_elem.text = str(listing.get('condition', '1000'))  # New by default
        
        # Quantity
        quantity_elem = ET.SubElement(item, "Quantity")
        quantity_elem.text = str(listing.get('quantity', 1))
        
        # Listing Duration
        duration_elem = ET.SubElement(item, "ListingDuration")
        duration_elem.text = listing.get('duration', 'GTC')  # Good Till Cancelled
        
        # Payment Methods
        payment_elem = ET.SubElement(item, "PaymentMethods")
        payment_elem.text = "PayPal"
        
        # Return Policy
        return_policy = ET.SubElement(item, "ReturnPolicy")
        returns_accepted = ET.SubElement(return_policy, "ReturnsAcceptedOption")
        returns_accepted.text = "ReturnsAccepted"
        
        # Shipping Details
        shipping = ET.SubElement(item, "ShippingDetails")
        shipping_type = ET.SubElement(shipping, "ShippingType")
        shipping_type.text = "Flat"
        
        # Add more fields as needed...
        
        return ET.tostring(root, encoding='unicode')
        
    async def update(self, listing_id: str, updates: Dict[str, Any]) -> bool:
        """Aggiorna listing esistente"""
        try:
            # Build ReviseItem XML
            xml_data = self._build_revise_xml(listing_id, updates)
            
            # Call eBay API
            response = await self.ebay_client.revise_item(xml_data)
            
            return response.get('Ack') == 'Success'
        except Exception:
            return False
            
    async def delete(self, listing_id: str) -> bool:
        """Elimina listing"""
        try:
            # Call eBay EndItem API
            response = await self.ebay_client.end_item(listing_id)
            
            return response.get('Ack') == 'Success'
        except Exception:
            return False
            
    def _build_revise_xml(self, listing_id: str, updates: Dict[str, Any]) -> str:
        """Costruisce XML per ReviseItem"""
        root = ET.Element("ReviseItemRequest")
        root.set("xmlns", "urn:ebay:apis:eBLBaseComponents")
        
        item = ET.SubElement(root, "Item")
        
        # Item ID
        item_id = ET.SubElement(item, "ItemID")
        item_id.text = listing_id
        
        # Add updated fields
        if 'title' in updates:
            title_elem = ET.SubElement(item, "Title")
            title_elem.text = updates['title']
            
        if 'price' in updates:
            price_elem = ET.SubElement(item, "StartPrice")
            price_elem.text = str(updates['price'])
            price_elem.set("currencyID", "EUR")
            
        # Add more update fields as needed...
        
        return ET.tostring(root, encoding='unicode')
