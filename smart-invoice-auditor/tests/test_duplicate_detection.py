"""
Test module for duplicate invoice detection.

This module contains tests for the duplicate detection functionality.
"""

import unittest
from datetime import date
from decimal import Decimal
import os
import sys
import copy

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.invoice import Invoice, LineItem, VendorInfo
from src.models.duplicate_detection import (
    DuplicateDetector, find_duplicates, is_duplicate, find_duplicate_in_list
)


class TestDuplicateDetection(unittest.TestCase):
    """Test case for duplicate invoice detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a sample vendor
        self.vendor = VendorInfo(
            name="Acme Corporation",
            address="123 Main St, Anytown, CA 12345",
            tax_id="12-3456789"
        )
        
        # Create sample line items
        self.line_items = [
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
        
        # Calculate expected totals
        self.subtotal = Decimal("3129.95")  # 20*150 + 1*99.95 + 2*15
        self.tax = Decimal("250.40")  # 8% tax
        self.total = Decimal("3380.35")  # subtotal + tax
        
        # Create a sample invoice
        self.invoice = Invoice(
            invoice_id="INV-12345",
            vendor=self.vendor,
            issue_date=date(2023, 6, 15),
            line_items=self.line_items,
            subtotal=self.subtotal,
            tax=self.tax,
            total=self.total,
            currency="USD",
            payment_terms="Net 30"
        )
        
        # Create an exact duplicate
        self.duplicate_invoice = copy.deepcopy(self.invoice)
        
        # Create a similar invoice with same ID but different total
        self.similar_invoice = copy.deepcopy(self.invoice)
        self.similar_invoice.total = Decimal("3500.00")
        
        # Create a completely different invoice
        self.different_vendor = VendorInfo(
            name="XYZ Supplies",
            address="456 Oak St, Somewhere, NY 10001",
            tax_id="98-7654321"
        )
        
        self.different_line_items = [
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
        
        self.different_invoice = Invoice(
            invoice_id="INV-67890",
            vendor=self.different_vendor,
            issue_date=date(2023, 7, 10),
            line_items=self.different_line_items,
            subtotal=Decimal("109.95"),
            tax=Decimal("8.80"),
            total=Decimal("118.75"),
            currency="USD"
        )
    
    def test_is_duplicate(self):
        """Test the is_duplicate function."""
        # Check exact duplicate
        self.assertTrue(is_duplicate(self.invoice, self.duplicate_invoice))
        
        # Check similar invoice with same ID
        self.assertTrue(is_duplicate(self.invoice, self.similar_invoice))
        
        # Check different invoice
        self.assertFalse(is_duplicate(self.invoice, self.different_invoice))
    
    def test_find_duplicate_in_list(self):
        """Test finding a duplicate in a list."""
        invoice_list = [self.duplicate_invoice, self.different_invoice]
        
        # Find duplicate for original invoice
        duplicate = find_duplicate_in_list(self.invoice, invoice_list)
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.invoice_id, self.invoice.invoice_id)
        
        # No duplicate for different invoice in a list without it
        new_different = Invoice(
            invoice_id="INV-99999",  # Different ID
            vendor=VendorInfo(
                name="New Vendor",
                address="789 Pine St, Newtown, CA 54321",
                tax_id="11-2233445"
            ),
            issue_date=date(2023, 8, 5),
            line_items=[
                LineItem(
                    description="New Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00")
                )
            ],
            subtotal=Decimal("50.00"),
            tax=Decimal("4.00"),
            total=Decimal("54.00"),
            currency="USD"
        )
        duplicate = find_duplicate_in_list(new_different, invoice_list)
        self.assertIsNone(duplicate)
    
    def test_duplicate_detector_single_duplicate(self):
        """Test DuplicateDetector with a single duplicate."""
        invoices = [self.invoice, self.duplicate_invoice, self.different_invoice]
        detector = DuplicateDetector(invoices)
        
        duplicates = detector.find_duplicates()
        self.assertEqual(len(duplicates), 1)  # One group of duplicates
        
        # Check that the duplicate group contains the right invoices
        duplicate_group = None
        for key, group in duplicates.items():
            if "hash:" in key:  # Find the hash-based group
                duplicate_group = group
                break
        
        self.assertIsNotNone(duplicate_group)
        self.assertEqual(len(duplicate_group), 2)
        self.assertEqual(duplicate_group[0].invoice_id, "INV-12345")
        self.assertEqual(duplicate_group[1].invoice_id, "INV-12345")
    
    def test_duplicate_detector_multiple_duplicates(self):
        """Test DuplicateDetector with multiple duplicate groups."""
        # Create another set of duplicate invoices with a different ID
        another_invoice = Invoice(
            invoice_id="INV-ABCDE",
            vendor=self.different_vendor,
            issue_date=date(2023, 8, 1),
            line_items=self.different_line_items,
            subtotal=Decimal("109.95"),
            tax=Decimal("8.80"),
            total=Decimal("118.75"),
            currency="USD"
        )
        another_duplicate = copy.deepcopy(another_invoice)
        
        invoices = [
            self.invoice, 
            self.duplicate_invoice, 
            another_invoice, 
            another_duplicate,
            self.different_invoice  # This is different from the others
        ]
        
        detector = DuplicateDetector(invoices)
        duplicates = detector.find_duplicates()
        
        # Should have 2 groups of duplicates
        self.assertEqual(len(duplicates), 2)
        
        # Check that each group has exactly 2 invoices
        group_sizes = [len(group) for group in duplicates.values()]
        self.assertIn(2, group_sizes)  # At least one group should have 2 invoices
    
    def test_duplicate_detector_add_invoice(self):
        """Test adding invoices to the DuplicateDetector."""
        detector = DuplicateDetector()
        
        # Add invoices one by one
        detector.add_invoice(self.invoice)
        detector.add_invoice(self.duplicate_invoice)
        
        # Should have 1 group of duplicates
        duplicates = detector.find_duplicates()
        self.assertEqual(len(duplicates), 1)
        
        # Add a batch of invoices
        detector.add_invoices([self.different_invoice, self.similar_invoice])
        
        # Now we should have a group with at least 2 invoices
        duplicates = detector.find_duplicates()
        self.assertTrue(any(len(group) >= 2 for group in duplicates.values()))
    
    def test_find_duplicate_for_invoice(self):
        """Test finding a duplicate for a specific invoice."""
        detector = DuplicateDetector([self.invoice, self.different_invoice])
        
        # Check for duplicate of the duplicate_invoice (should match self.invoice)
        duplicate = detector.find_duplicate_for_invoice(self.duplicate_invoice)
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.invoice_id, self.invoice.invoice_id)
        
        # Check for duplicate of a new different invoice
        new_different = Invoice(
            invoice_id="INV-NEW",
            vendor=VendorInfo(
                name="New Vendor",
                address="789 Pine St, Newtown, CA 54321",
                tax_id="11-2233445"
            ),
            issue_date=date(2023, 8, 5),
            line_items=[
                LineItem(
                    description="New Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00")
                )
            ],
            subtotal=Decimal("50.00"),
            tax=Decimal("4.00"),
            total=Decimal("54.00"),
            currency="USD"
        )
        duplicate = detector.find_duplicate_for_invoice(new_different)
        self.assertIsNone(duplicate)
    
    def test_convenience_function(self):
        """Test the convenience function for finding duplicates."""
        invoices = [self.invoice, self.duplicate_invoice, self.different_invoice]
        
        duplicates = find_duplicates(invoices)
        self.assertEqual(len(duplicates), 1)  # One group of duplicates
        
        # Check that the duplicate group contains the right invoices
        for key, group in duplicates.items():
            self.assertEqual(len(group), 2)
            self.assertEqual(group[0].invoice_id, "INV-12345")
            self.assertEqual(group[1].invoice_id, "INV-12345")


if __name__ == "__main__":
    unittest.main() 