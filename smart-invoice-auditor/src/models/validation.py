"""
Invoice Validation Module

This module provides validation functions for invoices beyond the basic validation
performed by the Invoice class itself. These functions can be used to perform
more complex validations and provide detailed error information.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import re

from .invoice import Invoice, LineItem


class ValidationResult:
    """
    Represents the result of a validation check.
    
    Attributes:
        is_valid: Boolean indicating if validation passed
        errors: List of error messages if validation failed
        warnings: List of warning messages for issues that don't invalidate the invoice
    """
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        
    def add_error(self, message: str):
        """Add an error message and mark the validation as failed."""
        self.errors.append(message)
        self.is_valid = False
        
    def add_warning(self, message: str):
        """Add a warning message without failing the validation."""
        self.warnings.append(message)
        
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        
    def __bool__(self):
        """Allow using the validation result as a boolean value."""
        return self.is_valid


def validate_invoice(invoice: Invoice) -> ValidationResult:
    """
    Perform comprehensive validation of an invoice.
    
    This function combines various validation checks to provide a complete
    validation report.
    
    Args:
        invoice: The invoice to validate
        
    Returns:
        ValidationResult object containing validation status and messages
    """
    result = ValidationResult()
    
    # Validate invoice ID
    result.merge(validate_invoice_id(invoice))
    
    # Validate date information
    result.merge(validate_dates(invoice))
    
    # Validate financial calculations
    result.merge(validate_calculations(invoice))
    
    # Validate line items
    result.merge(validate_line_items(invoice))
    
    # Validate vendor information
    result.merge(validate_vendor_info(invoice))
    
    return result


def validate_invoice_id(invoice: Invoice) -> ValidationResult:
    """
    Validate the invoice ID for proper format and content.
    
    Args:
        invoice: The invoice to validate
        
    Returns:
        ValidationResult with error/warning messages
    """
    result = ValidationResult()
    
    # Check if invoice ID is empty (should be caught by Invoice.__post_init__)
    if not invoice.invoice_id or not invoice.invoice_id.strip():
        result.add_error("Invoice ID is missing or empty")
        return result
    
    # Check for reasonable invoice ID format
    # Most invoice IDs contain at least one digit and some letters or special chars
    if not re.search(r'\d', invoice.invoice_id):
        result.add_warning("Invoice ID does not contain any digits, which is unusual")
    
    # Check for unreasonably long invoice IDs (might indicate OCR error)
    if len(invoice.invoice_id) > 30:
        result.add_warning("Invoice ID is unusually long (> 30 characters)")
    
    return result


def validate_dates(invoice: Invoice) -> ValidationResult:
    """
    Validate invoice dates for consistency and reasonableness.
    
    Args:
        invoice: The invoice to validate
        
    Returns:
        ValidationResult with error/warning messages
    """
    result = ValidationResult()
    
    # Make sure issue_date is a date object
    if not isinstance(invoice.issue_date, (date, datetime)):
        result.add_error("Issue date is not a valid date")
        return result
    
    issue_date = invoice.issue_date
    if isinstance(issue_date, datetime):
        issue_date = issue_date.date()
    
    # Check if issue date is in the future
    today = date.today()
    if issue_date > today:
        result.add_error(f"Invoice issue date ({issue_date}) is in the future")
    
    # Check if issue date is unreasonably old (e.g., more than 3 years old)
    three_years_ago = today - timedelta(days=3*365)
    if issue_date < three_years_ago:
        result.add_warning(f"Invoice issue date ({issue_date}) is over 3 years old")
    
    # Check due date if present
    if invoice.due_date:
        due_date = invoice.due_date
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        
        # Due date should be after or equal to issue date
        if due_date < issue_date:
            result.add_error(f"Due date ({due_date}) is before issue date ({issue_date})")
        
        # Warn if due date is unreasonably far in the future
        one_year_future = today + timedelta(days=365)
        if due_date > one_year_future:
            result.add_warning(f"Due date ({due_date}) is more than a year in the future")
    
    return result


def validate_calculations(invoice: Invoice) -> ValidationResult:
    """
    Validate that invoice calculations are correct.
    
    Checks that line items sum to subtotal, and subtotal + tax = total.
    
    Args:
        invoice: The invoice to validate
        
    Returns:
        ValidationResult with error/warning messages
    """
    result = ValidationResult()
    
    # Calculate sum of line items
    line_item_sum = sum(item.amount for item in invoice.line_items)
    
    # Compare with subtotal
    if invoice.subtotal is not None:
        # Allow for small rounding differences (up to 1 cent per line item + 1 cent)
        tolerance = Decimal('0.01') * (len(invoice.line_items) + 1)
        if abs(line_item_sum - invoice.subtotal) > tolerance:
            result.add_error(
                f"Line items sum ({line_item_sum}) does not match subtotal ({invoice.subtotal}), "
                f"difference: {abs(line_item_sum - invoice.subtotal)}"
            )
    
    # Check if total is consistent with subtotal + tax
    if invoice.subtotal is not None and invoice.tax is not None:
        expected_total = invoice.subtotal + invoice.tax
        if abs(expected_total - invoice.total) > Decimal('0.02'):
            result.add_error(
                f"Subtotal ({invoice.subtotal}) + tax ({invoice.tax}) = {expected_total}, "
                f"which does not match total ({invoice.total}), "
                f"difference: {abs(expected_total - invoice.total)}"
            )
    
    # Check for negative total
    if invoice.total < 0:
        result.add_warning("Invoice total is negative, which is unusual for standard invoices")
    
    return result


def validate_line_items(invoice: Invoice) -> ValidationResult:
    """
    Validate invoice line items for common issues.
    
    Args:
        invoice: The invoice to validate
        
    Returns:
        ValidationResult with error/warning messages
    """
    result = ValidationResult()
    
    # Check if there are any line items
    if not invoice.line_items:
        result.add_error("Invoice contains no line items")
        return result
    
    # Check each line item
    for i, item in enumerate(invoice.line_items, 1):
        # Check for empty descriptions
        if not item.description or not item.description.strip():
            result.add_error(f"Line item {i} has an empty description")
        
        # Check for zero or negative quantities
        if item.quantity <= 0:
            result.add_error(f"Line item {i} ({item.description}) has an invalid quantity: {item.quantity}")
        
        # Check for negative prices
        if item.unit_price < 0:
            result.add_error(f"Line item {i} ({item.description}) has a negative price: {item.unit_price}")
        
        # Check if amount matches quantity * unit_price
        expected_amount = item.quantity * item.unit_price
        if abs(expected_amount - item.amount) > Decimal('0.01'):
            result.add_error(
                f"Line item {i} ({item.description}) amount ({item.amount}) does not match "
                f"quantity ({item.quantity}) * price ({item.unit_price}) = {expected_amount}"
            )
    
    # Check for duplicate descriptions (might indicate a duplicate entry)
    descriptions = [item.description.strip().lower() for item in invoice.line_items]
    for i, desc in enumerate(descriptions):
        if descriptions.count(desc) > 1 and desc:
            result.add_warning(
                f"Possible duplicate line item: '{invoice.line_items[i].description}' "
                f"appears multiple times"
            )
    
    return result


def validate_vendor_info(invoice: Invoice) -> ValidationResult:
    """
    Validate vendor information for completeness.
    
    Args:
        invoice: The invoice to validate
        
    Returns:
        ValidationResult with error/warning messages
    """
    result = ValidationResult()
    
    # Vendor name should not be empty (should be caught by VendorInfo.__post_init__)
    if not invoice.vendor.name or not invoice.vendor.name.strip():
        result.add_error("Vendor name is missing or empty")
    
    # Warn if vendor address is missing
    if not invoice.vendor.address:
        result.add_warning("Vendor address is missing")
    
    # Warn if vendor tax ID is missing
    if not invoice.vendor.tax_id:
        result.add_warning("Vendor tax ID is missing")
    
    return result


def validate_invoice_from_ocr(invoice: Invoice) -> ValidationResult:
    """
    Validate an invoice created from OCR data with special considerations.
    
    This validation is more lenient to account for OCR errors.
    
    Args:
        invoice: The invoice created from OCR data
        
    Returns:
        ValidationResult with error/warning messages
    """
    result = ValidationResult()
    
    # Perform all standard validations
    std_result = validate_invoice(invoice)
    
    # For OCR-generated invoices, convert certain errors to warnings
    for error in std_result.errors:
        # Be more lenient on calculation errors since OCR might misread numbers
        if "does not match" in error and ("sum" in error or "subtotal" in error or "total" in error):
            result.add_warning(f"OCR may have misread values: {error}")
        else:
            result.add_error(error)
    
    # Add all standard warnings
    result.warnings.extend(std_result.warnings)
    
    # Check OCR confidence if available
    if invoice.ocr_confidence is not None:
        if invoice.ocr_confidence < 50:
            result.add_warning(
                f"Low OCR confidence ({invoice.ocr_confidence:.1f}%). "
                f"Manual verification of all fields is recommended."
            )
        elif invoice.ocr_confidence < 75:
            result.add_warning(
                f"Moderate OCR confidence ({invoice.ocr_confidence:.1f}%). "
                f"Some fields may require verification."
            )
    
    return result 