#!/usr/bin/env python3
"""
Example script to demonstrate duplicate invoice detection functionality.

This script shows how to use the duplicate detection module to find duplicate
invoices in a collection. It creates sample invoices and shows different ways
to detect duplicates.

Usage:
    python detect_duplicates.py

Example output:
    === Exact Duplicate Test ===
    Invoice INV-12345 from Acme Corporation is a duplicate of Invoice INV-12345 from Acme Corporation.

    === Similar Invoice Test ===
    Invoice INV-12345 from Acme Corporation is a duplicate of Invoice INV-12345 from Acme Corporation (despite having a different total).

    === Batch Detection Test ===
    Found 2 groups of duplicate invoices:
    Group #1 (3 invoices):
    - Invoice ID: INV-12345, Vendor: Acme Corporation, Date: 2023-06-15, Total: USD 3380.35
    - Invoice ID: INV-12345, Vendor: Acme Corporation, Date: 2023-06-15, Total: USD 3380.35
    - Invoice ID: INV-12345, Vendor: Acme Corporation, Date: 2023-06-15, Total: USD 3500.00

    Group #2 (2 invoices):
    - Invoice ID: INV-67890, Vendor: XYZ Supplies, Date: 2023-07-10, Total: USD 118.75
    - Invoice ID: INV-67890, Vendor: XYZ Supplies, Date: 2023-07-10, Total: USD 118.75
"""

import sys
import os
import copy
from datetime import date
from decimal import Decimal

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.invoice import Invoice, LineItem, VendorInfo
from src.models.duplicate_detection import (
    DuplicateDetector, is_duplicate, find_duplicate_in_list, find_duplicates
)
from src.models.utils import invoice_summary


def create_sample_invoices():
    """Create sample invoices for demonstration."""
    # Create a sample vendor
    vendor1 = VendorInfo(
        name="Acme Corporation",
        address="123 Main St, Anytown, CA 12345",
        tax_id="12-3456789"
    )
    
    # Create sample line items
    line_items1 = [
        LineItem(
            description="Web Development Services",
            quantity=Decimal("20"),
            unit_price=Decimal("150.00")
        ),
        LineItem(
            description="Server Hosting (Monthly)",
            quantity=Decimal("1"),
            unit_price=Decimal("99.95")
        ),
        LineItem(
            description="Domain Registration",
            quantity=Decimal("2"),
            unit_price=Decimal("15.00")
        )
    ]
    
    # Calculate totals
    subtotal1 = Decimal("3129.95")  # 20*150 + 1*99.95 + 2*15
    tax1 = Decimal("250.40")  # 8% tax
    total1 = Decimal("3380.35")  # subtotal + tax
    
    # Create a sample invoice
    invoice1 = Invoice(
        invoice_id="INV-12345",
        vendor=vendor1,
        issue_date=date(2023, 6, 15),
        line_items=line_items1,
        subtotal=subtotal1,
        tax=tax1,
        total=total1,
        currency="USD",
        payment_terms="Net 30"
    )
    
    # Create an exact duplicate
    invoice2 = copy.deepcopy(invoice1)
    
    # Create a similar invoice with same ID but different total
    invoice3 = copy.deepcopy(invoice1)
    invoice3.total = Decimal("3500.00")
    
    # Create a completely different invoice
    vendor2 = VendorInfo(
        name="XYZ Supplies",
        address="456 Oak St, Somewhere, NY 10001",
        tax_id="98-7654321"
    )
    
    line_items2 = [
        LineItem(
            description="Office Supplies",
            quantity=Decimal("5"),
            unit_price=Decimal("12.99")
        ),
        LineItem(
            description="Paper Reams",
            quantity=Decimal("10"),
            unit_price=Decimal("4.50")
        )
    ]
    
    invoice4 = Invoice(
        invoice_id="INV-67890",
        vendor=vendor2,
        issue_date=date(2023, 7, 10),
        line_items=line_items2,
        subtotal=Decimal("109.95"),
        tax=Decimal("8.80"),
        total=Decimal("118.75"),
        currency="USD"
    )
    
    # Create a duplicate of the different invoice
    invoice5 = copy.deepcopy(invoice4)
    
    return [invoice1, invoice2, invoice3, invoice4, invoice5]


def demo_exact_duplicate_check():
    """Demonstrate checking for an exact duplicate."""
    invoices = create_sample_invoices()
    
    # Get the first two invoices (exact duplicates)
    invoice1 = invoices[0]
    invoice2 = invoices[1]
    
    print("=== Exact Duplicate Test ===")
    if is_duplicate(invoice1, invoice2):
        print(f"Invoice {invoice1.invoice_id} from {invoice1.vendor.name} is a duplicate of "
              f"Invoice {invoice2.invoice_id} from {invoice2.vendor.name}.")
    else:
        print("The invoices are not duplicates.")
    print()


def demo_similar_invoice_check():
    """Demonstrate checking for a similar invoice."""
    invoices = create_sample_invoices()
    
    # Get the first and third invoices (similar but with different totals)
    invoice1 = invoices[0]
    invoice3 = invoices[2]
    
    print("=== Similar Invoice Test ===")
    if is_duplicate(invoice1, invoice3):
        print(f"Invoice {invoice1.invoice_id} from {invoice1.vendor.name} is a duplicate of "
              f"Invoice {invoice3.invoice_id} from {invoice3.vendor.name} "
              f"(despite having a different total).")
    else:
        print("The invoices are not duplicates.")
    print()


def demo_batch_detection():
    """Demonstrate batch detection of duplicates."""
    invoices = create_sample_invoices()
    
    print("=== Batch Detection Test ===")
    detector = DuplicateDetector(invoices)
    duplicates = detector.find_duplicates()
    
    if not duplicates:
        print("No duplicate invoices found.")
    else:
        print(f"Found {len(duplicates)} groups of duplicate invoices:")
        for i, (key, group) in enumerate(duplicates.items(), 1):
            print(f"Group #{i} ({len(group)} invoices):")
            for invoice in group:
                # Print a simplified summary
                print(f"- Invoice ID: {invoice.invoice_id}, "
                      f"Vendor: {invoice.vendor.name}, "
                      f"Date: {invoice.issue_date}, "
                      f"Total: {invoice.currency} {invoice.total}")
            print()


def demo_finding_duplicate_for_new_invoice():
    """Demonstrate finding a duplicate for a new invoice."""
    invoices = create_sample_invoices()
    
    # Create a collection of invoices to check against
    invoice_collection = invoices[1:4]  # Exclude the first and last invoices
    
    # Create a new invoice that's a duplicate of the first one
    new_invoice = copy.deepcopy(invoices[0])
    
    print("=== New Invoice Check ===")
    duplicate = find_duplicate_in_list(new_invoice, invoice_collection)
    
    if duplicate:
        print(f"Found a duplicate for the new invoice: {duplicate.invoice_id}")
    else:
        print("No duplicates found for the new invoice.")
    print()


def main():
    """Run the demonstration examples."""
    demo_exact_duplicate_check()
    demo_similar_invoice_check()
    demo_batch_detection()
    demo_finding_duplicate_for_new_invoice()


if __name__ == "__main__":
    main() 