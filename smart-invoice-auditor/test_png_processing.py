#!/usr/bin/env python3
"""
Test script to verify that PNG image processing works correctly.
This script tests the OCR functionality with a PNG image file.
"""

import os
import sys
import logging
from src.ocr.processor import create_processor
from src.models.utils import ocr_data_to_invoice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test the OCR functionality with a PNG file."""
    # Path to the sample PNG file
    png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples", "sample_invoice.png")
    
    if not os.path.exists(png_path):
        logger.error(f"PNG file not found at: {png_path}")
        return
    
    logger.info(f"Testing PNG processing with file: {png_path}")
    logger.info(f"File size: {os.path.getsize(png_path)} bytes")
    
    # Create an OCR processor (using Tesseract by default)
    processor = create_processor("tesseract")
    
    try:
        # Process the PNG file
        ocr_data = processor.process_file(png_path)
        
        # Log the extracted data
        logger.info(f"OCR processing complete. Confidence: {ocr_data.get('confidence', 0):.2f}%")
        logger.info(f"Invoice ID: {ocr_data.get('invoice_id', 'Not found')}")
        logger.info(f"Date: {ocr_data.get('date', 'Not found')}")
        logger.info(f"Vendor: {ocr_data.get('vendor', 'Not found')}")
        logger.info(f"Total: {ocr_data.get('total', 'Not found')}")
        
        # Try to convert OCR data to an invoice object
        invoice = ocr_data_to_invoice(ocr_data, png_path)
        logger.info(f"Successfully created invoice object: {invoice.invoice_id}")
        
        # Print out the full invoice details
        logger.info("Invoice details:")
        logger.info(f"  - ID: {invoice.invoice_id}")
        logger.info(f"  - Date: {invoice.issue_date}")
        logger.info(f"  - Vendor: {invoice.vendor.name}")
        logger.info(f"  - Total: {invoice.total}")
        logger.info(f"  - Line items: {len(invoice.line_items)}")
        
        return True
    except Exception as e:
        logger.error(f"Error processing PNG file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 