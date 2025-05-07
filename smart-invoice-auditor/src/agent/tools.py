"""
Auditor Tools Module

This module provides specialized tools for the invoice auditing agent.
These tools help detect issues in invoices such as duplicates, policy violations,
and calculation errors.
"""

import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import json

from .duplicate_detector import DuplicateDetector


class AuditorTools:
    """Collection of tools for invoice auditing"""
    
    def __init__(self, invoice_history: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize the auditor tools
        
        Args:
            invoice_history: Dictionary of previously processed invoices for duplicate detection
        """
        self.invoice_history = invoice_history or {}
        self.duplicate_detector = DuplicateDetector(invoice_history)
    
    def check_duplicate(self, invoice_id: str, vendor: str, amount: float, date: str) -> Dict[str, Any]:
        """
        Check if an invoice is a duplicate
        
        Args:
            invoice_id: The invoice ID to check
            vendor: The vendor name
            amount: The invoice total amount
            date: The invoice date
            
        Returns:
            Result with detection status and explanation
        """
        # Create a simplified invoice data structure for checking
        invoice_data = {
            "invoice_id": invoice_id,
            "vendor": vendor,
            "total": amount,
            "date": date
        }
        
        # Use the duplicate detector for comprehensive checking
        result = self.duplicate_detector.check_duplicate(invoice_data)
        
        # Add severity information if it's a duplicate
        if result["is_duplicate"]:
            result["severity"] = "high"
            
            # Add additional context based on confidence
            confidence = result.get("confidence", 1.0)
            if confidence >= 0.95:
                result["severity"] = "high"
            elif confidence >= 0.85:
                result["severity"] = "medium"
            else:
                result["severity"] = "low"
        
        return result
    
    def check_policy_compliance(self, expense_category: str, amount: float, 
                               policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an expense complies with policy
        
        Args:
            expense_category: The expense category
            amount: The expense amount
            policy_data: The policy data to check against
            
        Returns:
            Result with compliance status and explanation
        """
        if not policy_data:
            return {
                "complies": True,
                "reason": "No policy data available for compliance check"
            }
        
        # Check category
        if "allowed_categories" in policy_data:
            allowed_categories = [c.lower() for c in policy_data["allowed_categories"]]
            if expense_category.lower() not in allowed_categories:
                return {
                    "complies": False,
                    "reason": f"Category '{expense_category}' is not in the allowed categories: {', '.join(policy_data['allowed_categories'])}",
                    "severity": "medium",
                    "violation_type": "unauthorized_category"
                }
        
        # Check amount limits
        if "max_item_prices" in policy_data and expense_category.lower() in policy_data["max_item_prices"]:
            max_amount = policy_data["max_item_prices"][expense_category.lower()]
            if amount > max_amount:
                return {
                    "complies": False,
                    "reason": f"Amount ${amount:.2f} exceeds maximum ${max_amount:.2f} for category '{expense_category}'",
                    "severity": "medium",
                    "violation_type": "exceeds_category_limit"
                }
        
        # Check total invoice limit
        if "max_amount" in policy_data and amount > float(policy_data["max_amount"]):
            return {
                "complies": False,
                "reason": f"Amount ${amount:.2f} exceeds policy maximum ${float(policy_data['max_amount']):.2f}",
                "severity": "high",
                "violation_type": "exceeds_total_limit"
            }
        
        return {
            "complies": True,
            "reason": f"Expense complies with policy for category '{expense_category}' and amount ${amount:.2f}"
        }
    
    def verify_calculations(self, subtotal: float, tax: float, total: float, 
                           line_items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Verify that invoice calculations are correct
        
        Args:
            subtotal: The invoice subtotal
            tax: The invoice tax amount
            total: The invoice total
            line_items: Optional list of line items
            
        Returns:
            Result with verification status and explanation
        """
        issues = []
        
        # Check if subtotal + tax = total
        expected_total = subtotal + tax
        if abs(expected_total - total) > 0.01:
            issues.append({
                "type": "total_mismatch",
                "description": f"Total (${total:.2f}) doesn't match subtotal (${subtotal:.2f}) + tax (${tax:.2f}) = ${expected_total:.2f}",
                "severity": "medium"
            })
        
        # Check if line items sum to subtotal
        if line_items:
            line_sum = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in line_items)
            if abs(line_sum - subtotal) > 0.01:
                issues.append({
                    "type": "line_items_mismatch",
                    "description": f"Line items sum (${line_sum:.2f}) doesn't match subtotal (${subtotal:.2f})",
                    "severity": "medium"
                })
        
        if issues:
            return {
                "is_correct": False,
                "issues": issues
            }
        
        return {
            "is_correct": True,
            "reason": "All calculations verified: subtotal, tax, total, and line items are consistent"
        }
    
    def check_date_validity(self, invoice_date: str) -> Dict[str, Any]:
        """
        Check if invoice dates are valid
        
        Args:
            invoice_date: The invoice date to check (YYYY-MM-DD format)
            
        Returns:
            Result with validity status and explanation
        """
        try:
            # Try to parse the date
            date_format = "%Y-%m-%d"
            invoice_date_obj = datetime.strptime(invoice_date, date_format)
            
            # Check if date is in the future
            if invoice_date_obj > datetime.now():
                return {
                    "is_valid": False,
                    "reason": f"Invoice date {invoice_date} is in the future",
                    "severity": "high",
                    "issue_type": "future_date"
                }
            
            # Check if date is too old (more than 1 year)
            one_year_ago = datetime.now().replace(year=datetime.now().year - 1)
            if invoice_date_obj < one_year_ago:
                return {
                    "is_valid": False,
                    "reason": f"Invoice date {invoice_date} is more than one year old",
                    "severity": "medium",
                    "issue_type": "old_date"
                }
            
            return {
                "is_valid": True,
                "reason": f"Date {invoice_date} is valid"
            }
        except ValueError:
            return {
                "is_valid": False,
                "reason": f"Could not parse date '{invoice_date}'. Expected format is YYYY-MM-DD",
                "severity": "high",
                "issue_type": "invalid_format"
            }
    
    def generate_invoice_hash(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate a unique hash for an invoice to aid in duplicate detection
        
        Args:
            invoice_data: The invoice data to hash
            
        Returns:
            Hash string for the invoice
        """
        # Use the duplicate detector's hash generation method
        return self.duplicate_detector.generate_invoice_hash(invoice_data)
    
    def extract_vendor_info(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate vendor information from invoice data
        
        Args:
            invoice_data: The invoice data
            
        Returns:
            Extracted vendor information
        """
        vendor_name = invoice_data.get("vendor", "UNKNOWN")
        vendor_address = invoice_data.get("vendor_address", "")
        vendor_tax_id = invoice_data.get("vendor_tax_id", "")
        
        # Check for missing critical vendor information
        issues = []
        if vendor_name == "UNKNOWN":
            issues.append("Vendor name is missing")
        
        if not vendor_address:
            issues.append("Vendor address is missing")
        
        if not vendor_tax_id:
            issues.append("Vendor tax ID is missing")
        
        return {
            "vendor_name": vendor_name,
            "vendor_address": vendor_address,
            "vendor_tax_id": vendor_tax_id,
            "issues": issues,
            "is_complete": len(issues) == 0
        }
    
    def analyze_line_items(self, line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze line items for common issues
        
        Args:
            line_items: List of line items from the invoice
            
        Returns:
            Analysis results
        """
        if not line_items:
            return {
                "issues": ["No line items found"],
                "is_valid": False
            }
        
        issues = []
        categories = {}
        
        # Check each line item
        for i, item in enumerate(line_items):
            # Check for missing description
            if not item.get("description"):
                issues.append(f"Line item {i+1} is missing a description")
            
            # Check for zero or negative price
            price = item.get("price", 0.0)
            if price <= 0:
                issues.append(f"Line item {i+1} has zero or negative price: ${price:.2f}")
            
            # Check for zero or negative quantity
            quantity = item.get("quantity", 0)
            if quantity <= 0:
                issues.append(f"Line item {i+1} has zero or negative quantity: {quantity}")
            
            # Track categories for analysis
            category = item.get("category", "").lower()
            if category:
                if category in categories:
                    categories[category] += 1
                else:
                    categories[category] = 1
        
        return {
            "issues": issues,
            "is_valid": len(issues) == 0,
            "category_distribution": categories,
            "total_items": len(line_items)
        }