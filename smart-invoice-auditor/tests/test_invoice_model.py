"""
Test module for the invoice data structures.

This module tests the functionality of the invoice data models and utilities.
"""

import unittest
from datetime import date
from decimal import Decimal
import tempfile
import os
import json

# Add parent directory to path for imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.invoice import Invoice, LineItem, VendorInfo
from src.models.validation import validate_invoice, validate_invoice_from_ocr
from src.models.utils import (
    save_invoice_to_json, load_invoice_from_json, 
    ocr_data_to_invoice, invoice_summary
)


class TestInvoiceModel(unittest.TestCase):
    """Test case for the Invoice data model."""
    
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
        self.expected_subtotal = sum(item.amount for item in self.line_items)
        self.expected_tax = Decimal("0.08") * self.expected_subtotal
        self.expected_total = self.expected_subtotal + self.expected_tax
        
        # Create a sample invoice
        self.invoice = Invoice(
            invoice_id="INV-12345",
            vendor=self.vendor,
            issue_date=date(2023, 6, 15),
            line_items=self.line_items,
            subtotal=self.expected_subtotal,
            tax=self.expected_tax,
            total=self.expected_total,
            currency="USD",
            payment_terms="Net 30"
        )
    
    def test_invoice_creation(self):
        """Test basic invoice creation and validation."""
        # Verify the invoice was created correctly
        self.assertEqual(self.invoice.invoice_id, "INV-12345")
        self.assertEqual(self.invoice.vendor.name, "Acme Corporation")
        self.assertEqual(self.invoice.issue_date, date(2023, 6, 15))
        self.assertEqual(len(self.invoice.line_items), 3)
        
        # Check calculated values
        self.assertEqual(self.invoice.subtotal, self.expected_subtotal)
        self.assertEqual(self.invoice.tax, self.expected_tax)
        self.assertEqual(self.invoice.total, self.expected_total)
        
        # Verify hash was generated
        self.assertIsNotNone(self.invoice.invoice_hash)
    
    def test_line_item_calculations(self):
        """Test line item amount calculations."""
        # Test first line item
        item = self.line_items[0]
        self.assertEqual(item.quantity, Decimal("20"))
        self.assertEqual(item.unit_price, Decimal("150.00"))
        self.assertEqual(item.amount, Decimal("3000.00"))
        
        # Test creating a line item with amount specified
        item = LineItem(
            description="Test Item",
            quantity=Decimal("2"),
            unit_price=Decimal("10.00"),
            amount=Decimal("20.00")  # Explicitly set
        )
        self.assertEqual(item.amount, Decimal("20.00"))
    
    def test_invoice_validation(self):
        """Test invoice validation."""
        # Valid invoice should pass validation
        result = validate_invoice(self.invoice)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Create an invalid invoice with calculation error
        invalid_invoice = Invoice(
            invoice_id="INV-99999",
            vendor=self.vendor,
            issue_date=date(2023, 6, 15),
            line_items=self.line_items,
            subtotal=self.expected_subtotal,
            tax=self.expected_tax,
            total=Decimal("9999.99"),  # Wrong total
            currency="USD"
        )
        
        result = validate_invoice(invalid_invoice)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertTrue(any("does not match total" in error for error in result.errors))
    
    def test_json_serialization(self):
        """Test invoice JSON serialization and deserialization."""
        # Get dictionary representation
        invoice_dict = self.invoice.to_dict()
        
        # Check that dictionary contains expected fields
        self.assertEqual(invoice_dict["invoice_id"], "INV-12345")
        self.assertEqual(invoice_dict["vendor"]["name"], "Acme Corporation")
        self.assertEqual(invoice_dict["issue_date"], "2023-06-15")
        
        # Convert back to invoice
        new_invoice = Invoice.from_dict(invoice_dict)
        
        # Verify the new invoice matches the original
        self.assertEqual(new_invoice.invoice_id, self.invoice.invoice_id)
        self.assertEqual(new_invoice.vendor.name, self.invoice.vendor.name)
        self.assertEqual(new_invoice.total, self.invoice.total)
        self.assertEqual(len(new_invoice.line_items), len(self.invoice.line_items))
    
    def test_file_save_load(self):
        """Test saving and loading invoice to/from file."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save the invoice
            file_path = save_invoice_to_json(self.invoice, temp_dir)
            
            # Verify file was created
            self.assertTrue(os.path.exists(file_path))
            
            # Load the invoice
            loaded_invoice = load_invoice_from_json(file_path)
            
            # Verify loaded invoice matches original
            self.assertEqual(loaded_invoice.invoice_id, self.invoice.invoice_id)
            self.assertEqual(loaded_invoice.total, self.invoice.total)
            self.assertEqual(len(loaded_invoice.line_items), len(self.invoice.line_items))
    
    def test_invoice_from_ocr(self):
        """Test creating an invoice from OCR data."""
        # Simulate OCR data
        ocr_data = {
            "invoice_id": "OCR-12345",
            "vendor": "Test Vendor Inc.",
            "date": "2023-07-20",
            "total": "156.75",
            "subtotal": "145.00",
            "tax": "11.75",
            "line_items": [
                {
                    "description": "Consulting Services",
                    "quantity": 2,
                    "price": 50.00,
                    "amount": 100.00
                },
                {
                    "description": "Software License",
                    "quantity": 1,
                    "price": 45.00,
                    "amount": 45.00
                }
            ],
            "confidence": 85.5,
            "source_file": "test.pdf"
        }
        
        # Create invoice from OCR data
        invoice = ocr_data_to_invoice(ocr_data)
        
        # Verify the invoice was created correctly
        self.assertEqual(invoice.invoice_id, "OCR-12345")
        self.assertEqual(invoice.vendor.name, "Test Vendor Inc.")
        self.assertEqual(invoice.total, Decimal("156.75"))
        self.assertEqual(len(invoice.line_items), 2)
        self.assertEqual(invoice.ocr_confidence, 85.5)
        self.assertEqual(invoice.source_file, "test.pdf")
        
        # Test validation specific to OCR-created invoices
        result = validate_invoice_from_ocr(invoice)
        self.assertTrue(result.is_valid)
    
    def test_invoice_summary(self):
        """Test generating a human-readable invoice summary."""
        summary = invoice_summary(self.invoice)
        
        # Check that the summary contains key information
        self.assertIn("INV-12345", summary)
        self.assertIn("Acme Corporation", summary)
        self.assertIn(str(self.expected_total), summary)


if __name__ == "__main__":
    unittest.main() 