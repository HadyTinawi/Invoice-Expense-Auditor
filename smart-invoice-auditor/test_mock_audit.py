#!/usr/bin/env python
"""
Test script for the mock audit implementation.
This script tests the audit_invoice function directly without starting the Gradio UI.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import from app.py
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    # Import necessary components from app.py
    from app import process_file, audit_invoice, Invoice
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def test_mock_audit():
    """Test the mock audit implementation with a sample invoice."""
    logger.info("Testing mock audit implementation...")
    
    # Load a sample invoice or create one if not available
    sample_path = os.path.join(parent_dir, "data", "samples", "sample_invoice.json")
    
    if os.path.exists(sample_path):
        logger.info(f"Loading sample invoice from {sample_path}")
        with open(sample_path, 'r') as f:
            invoice_data = json.load(f)
    else:
        logger.warning(f"Sample invoice not found at {sample_path}. Creating a test invoice.")
        invoice_data = {
            "invoice_id": "TEST12345",
            "vendor": {
                "name": "Test Vendor",
                "address": "123 Test Street, Test City, TS 12345",
                "phone": "555-123-4567",
                "email": "contact@testvendor.com"
            },
            "issue_date": "2023-07-15",
            "due_date": "2023-08-15",
            "total": 110.0,  # Intentionally incorrect to trigger a calculation error
            "subtotal": 90.0,
            "tax": 10.0,
            "currency": "USD",
            "line_items": [
                {
                    "description": "Test Product",
                    "quantity": 1,
                    "unit_price": 90.0,
                    "amount": 90.0,
                    "category": "general"
                }
            ],
            "payment_terms": "Net 30",
            "raw_text": "Sample invoice text for OCR testing"
        }
    
    # Process the invoice
    try:
        # We need to simulate the processing step
        invoice_obj = Invoice.from_dict(invoice_data)
        invoice_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Simulate the processed_invoices dictionary entry
        processed_invoice = {
            "invoice_object": invoice_obj,
            "ocr_data": invoice_data.get("raw_text", ""),
            "file_info": {"file_name": "test_invoice.json", "file_path": sample_path},
            "processed_at": datetime.now().isoformat()
        }
        
        # Insert the processed invoice into app's global state (monkeypatch)
        import app
        app.processed_invoices[invoice_id] = processed_invoice
        
        # Audit the invoice
        logger.info(f"Auditing invoice with ID {invoice_id}")
        audit_summary, audit_json = audit_invoice(invoice_id)
        
        # Output results
        logger.info("Audit Summary:\n" + audit_summary)
        
        # Parse and validate the JSON result
        audit_result = json.loads(audit_json)
        logger.info(f"Issues found: {audit_result.get('issues_found', False)}")
        
        # Check basic structure of the result
        assert 'invoice_id' in audit_result, "Invoice ID missing from audit result"
        assert 'vendor' in audit_result, "Vendor missing from audit result"
        assert 'issues' in audit_result, "Issues missing from audit result"
        assert 'summary' in audit_result, "Summary missing from audit result"
        
        # Test result based on the invoice data
        if invoice_data["total"] != invoice_data["subtotal"] + invoice_data["tax"]:
            assert audit_result["issues_found"], "Calculation error should have been detected"
            calculation_error = False
            for issue in audit_result["issues"]:
                if "Calculation Error" in issue.get("type", ""):
                    calculation_error = True
            assert calculation_error, "Calculation error not found in issues"
        
        logger.info("✅ Mock audit test completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_mock_audit()
    if success:
        logger.info("All tests passed!")
        sys.exit(0)
    else:
        logger.error("Test failed!")
        sys.exit(1) 