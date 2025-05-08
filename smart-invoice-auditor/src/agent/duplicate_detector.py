"""
Duplicate Invoice Detector Module

This module handles detection of duplicate invoices to prevent double payment.
"""

import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


class DuplicateDetector:
    """Class to detect duplicate invoices"""
    
    def __init__(self, invoice_history: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize the duplicate detector
        
        Args:
            invoice_history: Dictionary of previously processed invoices
        """
        self.invoice_history = invoice_history or {}
    
    def generate_invoice_hash(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate a unique hash for an invoice
        
        Args:
            invoice_data: The invoice data to hash
            
        Returns:
            Hash string for the invoice
        """
        # Extract key fields
        invoice_id = str(invoice_data.get("invoice_id", "")).strip().lower()
        vendor = str(invoice_data.get("vendor", "")).strip().lower()
        total = float(invoice_data.get("total", 0.0))
        date = str(invoice_data.get("date", "")).strip()
        
        # Create a string to hash
        hash_string = f"{invoice_id}|{vendor}|{total:.2f}|{date}"
        
        # Generate the hash
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def check_duplicate(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an invoice is a duplicate
        
        Args:
            invoice_data: The invoice data to check
            
        Returns:
            Result with detection status and explanation
        """
        # Extract key fields
        invoice_id = str(invoice_data.get("invoice_id", "")).strip()
        vendor = str(invoice_data.get("vendor", "")).strip()
        total = float(invoice_data.get("total", 0.0))
        date = str(invoice_data.get("date", "")).strip()
        
        # Check for exact invoice ID match with same vendor
        for id_key, stored_invoice in self.invoice_history.items():
            stored_id = str(stored_invoice.get("invoice_id", "")).strip()
            stored_vendor = str(stored_invoice.get("vendor", "")).strip()
            
            if invoice_id == stored_id and vendor == stored_vendor:
                return {
                    "is_duplicate": True,
                    "reason": f"Invoice ID '{invoice_id}' from vendor '{vendor}' already exists in the system",
                    "duplicate_of": id_key,
                    "confidence": 1.0
                }
        
        # Check for invoice with similar details
        for id_key, stored_invoice in self.invoice_history.items():
            stored_id = str(stored_invoice.get("invoice_id", "")).strip()
            stored_vendor = str(stored_invoice.get("vendor", "")).strip()
            stored_total = float(stored_invoice.get("total", 0.0))
            stored_date = str(stored_invoice.get("date", "")).strip()
            
            # Skip if the vendor is different
            if vendor.lower() != stored_vendor.lower():
                continue
            
            # Check for high similarity in ID, amount, and date
            # (Could have had a typo in the invoice ID)
            
            # Similar amount (within 1%)
            amount_similar = abs(total - stored_total) / max(total, stored_total) < 0.01
            
            # Similar date (same day)
            date_similar = date == stored_date
            
            if amount_similar and date_similar:
                return {
                    "is_duplicate": True,
                    "reason": f"Invoice appears to be a duplicate: same amount (${total:.2f}) and date ({date}) as invoice '{stored_id}'",
                    "duplicate_of": id_key,
                    "confidence": 0.9
                }
        
        # No duplicates found
        return {
            "is_duplicate": False,
            "reason": f"No duplicates found for invoice '{invoice_id}' from vendor '{vendor}'",
            "confidence": 1.0
        }
    
    def add_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """
        Add an invoice to the history for future duplicate checks
        
        Args:
            invoice_data: The invoice data to add
            
        Returns:
            ID key for the added invoice
        """
        # Generate a unique key
        id_key = self.generate_invoice_hash(invoice_data)
        
        # Store the invoice
        self.invoice_history[id_key] = invoice_data
        
        return id_key