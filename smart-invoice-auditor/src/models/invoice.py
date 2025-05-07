"""
Invoice Data Structures Module

This module defines the data structures used to represent invoices in the
Smart Invoice & Expense Auditor system. These structures are designed to be
flexible enough to accommodate varying invoice formats while providing a
standardized interface for the audit system.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
import json
import uuid


@dataclass
class VendorInfo:
    """
    Represents vendor information from an invoice.
    
    Attributes:
        name: The name of the vendor
        address: Optional address of the vendor
        tax_id: Optional tax ID or business ID
        contact: Optional contact information (email, phone, etc.)
        website: Optional website URL
        additional_info: Dictionary for any additional vendor-specific information
    """
    name: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    contact: Optional[str] = None
    website: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure name is not empty
        if not self.name or not self.name.strip():
            raise ValueError("Vendor name cannot be empty")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert vendor info to a dictionary for JSON serialization"""
        return {
            "name": self.name,
            "address": self.address,
            "tax_id": self.tax_id,
            "contact": self.contact,
            "website": self.website,
            "additional_info": self.additional_info
        }


@dataclass
class LineItem:
    """
    Represents a single line item from an invoice.
    
    Attributes:
        description: Description of the item or service
        quantity: Quantity purchased
        unit_price: Price per unit
        amount: Total amount for this line item (quantity * unit_price)
        item_id: Optional ID for the line item
        category: Optional expense category
        tax_rate: Optional tax rate applied to this item
        discount: Optional discount applied to this item
        additional_info: Dictionary for any additional item-specific information
    """
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Optional[Decimal] = None
    item_id: Optional[str] = None
    category: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Convert numeric values to Decimal if they're not already
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        
        if not isinstance(self.unit_price, Decimal):
            self.unit_price = Decimal(str(self.unit_price))
        
        # Calculate amount if not provided
        if self.amount is None:
            self.amount = self.quantity * self.unit_price
        elif not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
            
        # Convert tax_rate and discount to Decimal if provided
        if self.tax_rate is not None and not isinstance(self.tax_rate, Decimal):
            self.tax_rate = Decimal(str(self.tax_rate))
            
        if self.discount is not None and not isinstance(self.discount, Decimal):
            self.discount = Decimal(str(self.discount))
            
        # Validate that description is not empty
        if not self.description or not self.description.strip():
            raise ValueError("Line item description cannot be empty")
        
        # Validate numeric values
        if self.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert line item to a dictionary for JSON serialization"""
        return {
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount) if self.amount is not None else None,
            "item_id": self.item_id,
            "category": self.category,
            "tax_rate": str(self.tax_rate) if self.tax_rate is not None else None,
            "discount": str(self.discount) if self.discount is not None else None,
            "additional_info": self.additional_info
        }


@dataclass
class Invoice:
    """
    Represents a complete invoice with all relevant information.
    
    Attributes:
        invoice_id: The unique identifier for the invoice
        vendor: Vendor information
        issue_date: Date the invoice was issued
        due_date: Optional date payment is due
        line_items: List of line items on the invoice
        subtotal: Invoice subtotal before taxes and adjustments
        tax: Total tax amount
        total: Total invoice amount after taxes and adjustments
        currency: Currency code (e.g., 'USD', 'EUR')
        payment_terms: Optional payment terms
        purchase_order: Optional purchase order reference
        ocr_confidence: Optional confidence score from OCR extraction
        source_file: Optional path or reference to the source file
        additional_info: Dictionary for any additional invoice-specific information
        invoice_hash: Hash representation to assist with duplicate detection
    """
    invoice_id: str
    vendor: VendorInfo
    issue_date: Union[date, datetime, str]
    line_items: List[LineItem]
    total: Decimal
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    due_date: Optional[Union[date, datetime, str]] = None
    currency: str = "USD"
    payment_terms: Optional[str] = None
    purchase_order: Optional[str] = None
    ocr_confidence: Optional[float] = None
    source_file: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    invoice_hash: Optional[str] = None

    def __post_init__(self):
        # Ensure invoice_id is not empty
        if not self.invoice_id or not self.invoice_id.strip():
            raise ValueError("Invoice ID cannot be empty")
        
        # Convert total to Decimal if it's not already
        if not isinstance(self.total, Decimal):
            self.total = Decimal(str(self.total))
            
        # Convert subtotal and tax to Decimal if provided
        if self.subtotal is not None and not isinstance(self.subtotal, Decimal):
            self.subtotal = Decimal(str(self.subtotal))
            
        if self.tax is not None and not isinstance(self.tax, Decimal):
            self.tax = Decimal(str(self.tax))
            
        # Calculate subtotal if not provided
        if self.subtotal is None:
            self.subtotal = sum(item.amount for item in self.line_items)
            
        # Convert date strings to date objects
        if isinstance(self.issue_date, str):
            self.issue_date = self._parse_date(self.issue_date)
            
        if isinstance(self.due_date, str) and self.due_date:
            self.due_date = self._parse_date(self.due_date)
            
        # Generate invoice hash if not provided
        if self.invoice_hash is None:
            self.invoice_hash = self._generate_hash()

    def _parse_date(self, date_string: str) -> date:
        """Parse a date string into a date object."""
        formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
            "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%d-%B-%Y"
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_string, fmt).date()
                return parsed_date
            except ValueError:
                continue
                
        # If all formats fail, raise an error
        raise ValueError(f"Could not parse date string: {date_string}")

    def _generate_hash(self) -> str:
        """
        Generate a hash for this invoice to help with duplicate detection.
        
        The hash is based on key invoice attributes but not all details.
        """
        hash_base = {
            "invoice_id": self.invoice_id,
            "vendor_name": self.vendor.name,
            "issue_date": str(self.issue_date),
            "total": str(self.total),
            "line_item_count": len(self.line_items)
        }
        
        # Add line item amounts to further strengthen the hash
        line_item_hashes = [str(item.amount) for item in self.line_items]
        hash_base["line_items"] = sorted(line_item_hashes)
        
        # Generate a deterministic hash
        hash_string = json.dumps(hash_base, sort_keys=True)
        return str(uuid.uuid5(uuid.NAMESPACE_OID, hash_string))

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the invoice to a dictionary representation.
        
        This is useful for JSON serialization and storage.
        """
        def _serialize(obj):
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            elif isinstance(obj, Decimal):
                return str(obj)
            elif hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
                return obj.to_dict()
            elif isinstance(obj, list):
                return [_serialize(item) for item in obj]
            else:
                return obj
        
        result = {}
        for key, value in self.__dict__.items():
            result[key] = _serialize(value)
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invoice':
        """
        Create an Invoice object from a dictionary representation.
        
        This is useful for deserializing from JSON or database storage.
        """
        # Process vendor data
        vendor_data = data.get('vendor', {})
        vendor = VendorInfo(**vendor_data)
        
        # Process line items
        line_items_data = data.get('line_items', [])
        line_items = []
        for item_data in line_items_data:
            # Convert string decimals back to Decimal objects
            for decimal_field in ['quantity', 'unit_price', 'amount', 'tax_rate', 'discount']:
                if decimal_field in item_data and isinstance(item_data[decimal_field], str):
                    item_data[decimal_field] = Decimal(item_data[decimal_field])
            line_items.append(LineItem(**item_data))
        
        # Convert string decimals back to Decimal objects for invoice fields
        for decimal_field in ['total', 'subtotal', 'tax']:
            if decimal_field in data and isinstance(data[decimal_field], str):
                data[decimal_field] = Decimal(data[decimal_field])
                
        # Create the invoice object
        invoice_data = {k: v for k, v in data.items() if k not in ['vendor', 'line_items']}
        invoice = cls(
            vendor=vendor,
            line_items=line_items,
            **invoice_data
        )
        
        return invoice

    def is_valid(self) -> bool:
        """
        Validate that the invoice data is consistent.
        
        Returns:
            bool: True if invoice passes validation, False otherwise
        """
        try:
            # Calculate the sum of line items
            calculated_subtotal = sum(item.amount for item in self.line_items)
            
            # Check if calculated subtotal matches the reported subtotal
            if self.subtotal and abs(calculated_subtotal - self.subtotal) > Decimal('0.01'):
                return False
            
            # Check if subtotal + tax equals total (within 1 cent tolerance)
            if self.subtotal and self.tax:
                calculated_total = self.subtotal + self.tax
                if abs(calculated_total - self.total) > Decimal('0.01'):
                    return False
                    
            # Check if there are any line items
            if not self.line_items:
                return False
                
            # Check if all line items have valid quantities and prices
            for item in self.line_items:
                if item.quantity <= 0 or item.unit_price < 0:
                    return False
            
            # Check that issue_date is not in the future
            today = date.today()
            if isinstance(self.issue_date, datetime):
                issue_date = self.issue_date.date()
            else:
                issue_date = self.issue_date
                
            if issue_date > today:
                return False
                
            return True
        except Exception:
            return False


def create_invoice_from_ocr_data(ocr_data: Dict[str, Any]) -> Invoice:
    """
    Create an Invoice object from OCR-extracted data.
    
    This function bridges the gap between the OCR output format and our Invoice model.
    
    Args:
        ocr_data: Dictionary containing extracted invoice data from OCR
        
    Returns:
        Invoice: A structured invoice object
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Extract required fields
    invoice_id = ocr_data.get('invoice_id')
    if not invoice_id:
        raise ValueError("Invoice ID is required but was not found in OCR data")
    
    # Extract vendor information
    vendor_name = ocr_data.get('vendor')
    if not vendor_name:
        raise ValueError("Vendor name is required but was not found in OCR data")
    
    vendor = VendorInfo(name=vendor_name)
    
    # Extract date
    issue_date = ocr_data.get('date')
    if not issue_date:
        raise ValueError("Invoice date is required but was not found in OCR data")
    
    # Extract line items
    line_items_data = ocr_data.get('line_items', [])
    line_items = []
    
    for item_data in line_items_data:
        try:
            line_item = LineItem(
                description=item_data.get('description', 'Unknown Item'),
                quantity=Decimal(str(item_data.get('quantity', 1))),
                unit_price=Decimal(str(item_data.get('price', 0))),
                amount=Decimal(str(item_data.get('amount', 0))) if 'amount' in item_data else None
            )
            line_items.append(line_item)
        except Exception as e:
            # Log error but continue processing other line items
            print(f"Error processing line item: {e}")
    
    # Extract totals
    total = Decimal(str(ocr_data.get('total', 0)))
    subtotal = Decimal(str(ocr_data.get('subtotal', 0))) if 'subtotal' in ocr_data else None
    tax = Decimal(str(ocr_data.get('tax', 0))) if 'tax' in ocr_data else None
    
    # Add source information
    source_file = ocr_data.get('source_file')
    ocr_confidence = ocr_data.get('confidence')
    
    # Create the invoice
    invoice = Invoice(
        invoice_id=invoice_id,
        vendor=vendor,
        issue_date=issue_date,
        line_items=line_items,
        total=total,
        subtotal=subtotal,
        tax=tax,
        ocr_confidence=ocr_confidence,
        source_file=source_file
    )
    
    return invoice 