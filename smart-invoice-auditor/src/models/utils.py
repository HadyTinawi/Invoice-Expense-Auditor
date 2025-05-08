"""
Invoice Utilities Module

This module provides utility functions for working with invoices, including
conversion from different data formats, extraction helpers, and serialization utilities.
"""

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
import logging

from .invoice import Invoice, LineItem, VendorInfo


logger = logging.getLogger(__name__)


def save_invoice_to_json(invoice: Invoice, output_path: str) -> str:
    """
    Save an invoice to a JSON file.
    
    Args:
        invoice: The invoice to save
        output_path: Directory where the file should be saved
        
    Returns:
        Path to the saved file
        
    Raises:
        IOError: If the file cannot be written
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Generate a filename based on invoice ID and date
    if isinstance(invoice.issue_date, datetime):
        date_str = invoice.issue_date.strftime("%Y%m%d")
    else:
        date_str = invoice.issue_date.isoformat().replace("-", "")
        
    safe_id = "".join(c if c.isalnum() else "_" for c in invoice.invoice_id)
    filename = f"{date_str}_{safe_id}.json"
    full_path = os.path.join(output_path, filename)
    
    # Convert invoice to dictionary using the to_dict method which handles custom objects
    invoice_dict = invoice.to_dict()
    
    # Write to file
    try:
        with open(full_path, 'w') as f:
            json.dump(invoice_dict, f, indent=2, default=str)  # Use default=str as fallback serializer
        return full_path
    except Exception as e:
        logger.error(f"Failed to save invoice to {full_path}: {str(e)}")
        raise IOError(f"Failed to save invoice: {str(e)}")


def load_invoice_from_json(file_path: str) -> Invoice:
    """
    Load an invoice from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded Invoice object
        
    Raises:
        IOError: If the file cannot be read
        ValueError: If the file contains invalid data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return Invoice.from_dict(data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {file_path}: {str(e)}")
        raise ValueError(f"Invalid JSON format in file {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to load invoice from {file_path}: {str(e)}")
        raise IOError(f"Failed to load invoice: {str(e)}")


def ocr_data_to_invoice(ocr_data: Dict[str, Any], source_file: Optional[str] = None) -> Invoice:
    """
    Convert OCR-extracted data to an Invoice object.
    
    This function handles the specific format of data returned by the OCR processing
    module and creates a structured Invoice object.
    
    Args:
        ocr_data: Dictionary containing extracted invoice data from OCR
        source_file: Optional path to the source PDF file
        
    Returns:
        A structured Invoice object
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Add raw extracted data to log for debugging
    logger.debug(f"Raw OCR data: {json.dumps(ocr_data, default=str, indent=2)}")
    
    # Extract required fields with validation and fallbacks
    invoice_id = ocr_data.get('invoice_id')
    if not invoice_id:
        logger.warning("Invoice ID not found in OCR data. Using fallback ID.")
        invoice_id = f"OCR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Extract vendor information
    vendor_name = ocr_data.get('vendor')
    if not vendor_name:
        logger.warning("Vendor name not found in OCR data. Using fallback vendor name.")
        vendor_name = "Unknown Vendor"
    
    vendor = VendorInfo(name=vendor_name)
    
    # Extract date with fallback to current date
    issue_date = ocr_data.get('date')
    if not issue_date:
        logger.warning("Invoice date not found in OCR data. Using current date as fallback.")
        issue_date = datetime.now().date().isoformat()
    else:
        # Try to normalize the date format
        try:
            issue_date = _normalize_date_format(issue_date)
            logger.info(f"Normalized date format: {issue_date}")
        except ValueError as e:
            logger.warning(f"Date normalization failed: {str(e)}. Using current date as fallback.")
            issue_date = datetime.now().date().isoformat()
    
    # Extract line items
    ocr_line_items = ocr_data.get('line_items', [])
    line_items = []
    
    # If no line items were extracted, create a default one
    if not ocr_line_items:
        logger.warning("No line items found in OCR data. Creating default line item.")
        line_items = [
            LineItem(
                description="Unspecified Item (OCR could not extract line items)",
                quantity=Decimal('1'),
                unit_price=Decimal(str(ocr_data.get('total', '0')))
            )
        ]
    else:
        for item_data in ocr_line_items:
            try:
                # Handle different key naming conventions in OCR output
                description = item_data.get('description', item_data.get('item', 'Unknown Item'))
                quantity = item_data.get('quantity', 1)
                unit_price = item_data.get('price', item_data.get('unit_price', 0))
                amount = item_data.get('amount', item_data.get('total', None))
                
                line_item = LineItem(
                    description=description,
                    quantity=Decimal(str(quantity)),
                    unit_price=Decimal(str(unit_price)),
                    amount=Decimal(str(amount)) if amount is not None else None
                )
                line_items.append(line_item)
            except Exception as e:
                logger.warning(f"Error processing line item: {str(e)}")
                # Continue processing other line items
    
    # Extract totals
    try:
        total = Decimal(str(ocr_data.get('total', 0)))
        if total == 0:
            logger.warning("Total amount is zero or not found. This might indicate incomplete OCR extraction.")
    except (ValueError, TypeError):
        logger.warning("Invalid total in OCR data, defaulting to 0")
        total = Decimal('0')
        
    try:
        subtotal = Decimal(str(ocr_data.get('subtotal', 0))) if 'subtotal' in ocr_data else None
    except (ValueError, TypeError):
        logger.warning("Invalid subtotal in OCR data, defaulting to None")
        subtotal = None
        
    try:
        tax = Decimal(str(ocr_data.get('tax', 0))) if 'tax' in ocr_data else None
    except (ValueError, TypeError):
        logger.warning("Invalid tax in OCR data, defaulting to None")
        tax = None
    
    # Add source information
    source_file = source_file or ocr_data.get('source_file')
    ocr_confidence = ocr_data.get('confidence')
    
    # Create the invoice
    try:
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
        logger.info(f"Successfully created invoice object with ID: {invoice_id}, Vendor: {vendor_name}")
        return invoice
    except Exception as e:
        logger.error(f"Failed to create invoice from OCR data: {str(e)}")
        
        # Try one more time with minimal data
        try:
            logger.info("Attempting to create invoice with minimal data...")
            minimal_invoice = Invoice(
                invoice_id=invoice_id or "UNKNOWN_ID",
                vendor=VendorInfo(name=vendor_name or "Unknown Vendor"),
                issue_date=datetime.now().date().isoformat(),
                line_items=[LineItem(
                    description="Unknown Item",
                    quantity=Decimal('1'),
                    unit_price=Decimal('0')
                )],
                total=Decimal('0')
            )
            logger.info("Created invoice with minimal data as fallback")
            return minimal_invoice
        except Exception as e2:
            logger.error(f"Even minimal invoice creation failed: {str(e2)}")
            raise ValueError(f"Cannot create invoice from OCR data: {str(e)}")


def _normalize_date_format(date_str: str) -> str:
    """
    Normalize various date formats into ISO format (YYYY-MM-DD).
    
    Args:
        date_str: A date string in various possible formats
        
    Returns:
        A normalized date string in ISO format
        
    Raises:
        ValueError: If the date string cannot be parsed
    """
    # List of common date formats to try
    formats = [
        # ISO format
        "%Y-%m-%d",
        
        # Common US formats
        "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        
        # Month name formats
        "%b %d, %Y", "%B %d, %Y",
        "%d %b %Y", "%d %B %Y",
        "%d-%b-%Y", "%d-%B-%Y",
        "%b %d %Y", "%B %d %Y",
        
        # Month name only (e.g., "June")
        "%B",
        
        # Short year formats
        "%m/%d/%y", "%d/%m/%y",
        
        # Formats with time
        "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S",
    ]
    
    # First, check if the input might just be a month name
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    clean_date = date_str.strip().lower()
    
    # If it's just a month name, convert to current year and that month
    if clean_date in months:
        month_num = months[clean_date]
        current_year = datetime.now().year
        return f"{current_year}-{month_num:02d}-01"
    
    # Try each format
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            
            # If we only got a month, use the current year and the first day of that month
            if fmt == "%B":
                date_obj = date_obj.replace(year=datetime.now().year, day=1)
                
            return date_obj.date().isoformat()
        except ValueError:
            continue
    
    # If all standard formats failed, try some regex-based approaches
    import re
    
    # Look for patterns like "06/2023" (month/year)
    match = re.match(r"(\d{1,2})[/\-\.](\d{4})", clean_date)
    if match:
        month, year = match.groups()
        return f"{year}-{int(month):02d}-01"
    
    # Look for patterns like "2023/06" (year/month)
    match = re.match(r"(\d{4})[/\-\.](\d{1,2})", clean_date)
    if match:
        year, month = match.groups()
        return f"{year}-{int(month):02d}-01"
        
    # If nothing works, fallback to current date
    logger.warning(f"Could not parse date: '{date_str}'. Using current date.")
    return datetime.now().date().isoformat()


def invoice_summary(invoice: Invoice) -> str:
    """
    Generate a human-readable summary of an invoice.
    
    Args:
        invoice: The invoice to summarize
        
    Returns:
        A formatted string with key invoice information
    """
    if isinstance(invoice.issue_date, datetime):
        date_str = invoice.issue_date.strftime("%Y-%m-%d")
    else:
        date_str = str(invoice.issue_date)
    
    summary = [
        f"Invoice ID: {invoice.invoice_id}",
        f"Vendor: {invoice.vendor.name}",
        f"Date: {date_str}",
        f"Total: {invoice.currency} {invoice.total}",
        f"Line Items: {len(invoice.line_items)}"
    ]
    
    if invoice.subtotal is not None:
        summary.append(f"Subtotal: {invoice.currency} {invoice.subtotal}")
    
    if invoice.tax is not None:
        summary.append(f"Tax: {invoice.currency} {invoice.tax}")
    
    if invoice.ocr_confidence is not None:
        summary.append(f"OCR Confidence: {invoice.ocr_confidence:.1f}%")
    
    return "\n".join(summary)


def invoice_comparison(invoice1: Invoice, invoice2: Invoice) -> Dict[str, Any]:
    """
    Compare two invoices and return differences.
    
    This is useful for duplicate detection and verification.
    
    Args:
        invoice1: First invoice to compare
        invoice2: Second invoice to compare
        
    Returns:
        Dictionary with differences between the invoices
    """
    differences = {
        "is_duplicate": False,
        "same_id": invoice1.invoice_id == invoice2.invoice_id,
        "same_vendor": invoice1.vendor.name == invoice2.vendor.name,
        "same_date": invoice1.issue_date == invoice2.issue_date,
        "same_total": invoice1.total == invoice2.total,
        "same_line_item_count": len(invoice1.line_items) == len(invoice2.line_items),
        "differences": []
    }
    
    # Check if invoices have the same hash
    if invoice1.invoice_hash == invoice2.invoice_hash:
        differences["is_duplicate"] = True
        return differences
    
    # Check key fields for differences
    if invoice1.invoice_id != invoice2.invoice_id:
        differences["differences"].append(f"Invoice ID: {invoice1.invoice_id} vs {invoice2.invoice_id}")
    
    if invoice1.vendor.name != invoice2.vendor.name:
        differences["differences"].append(f"Vendor: {invoice1.vendor.name} vs {invoice2.vendor.name}")
    
    if invoice1.issue_date != invoice2.issue_date:
        differences["differences"].append(f"Date: {invoice1.issue_date} vs {invoice2.issue_date}")
    
    if invoice1.total != invoice2.total:
        differences["differences"].append(f"Total: {invoice1.total} vs {invoice2.total}")
    
    # If all key fields match, consider it a potential duplicate
    if (invoice1.invoice_id == invoice2.invoice_id and 
            invoice1.vendor.name == invoice2.vendor.name and
            invoice1.total == invoice2.total):
        differences["is_duplicate"] = True
    
    return differences 