#!/usr/bin/env python3
"""
Example script to demonstrate processing a PDF invoice 
to a structured invoice object and outputting it to JSON.

Usage:
    python process_invoice.py <pdf_path> [output_dir]

Example:
    python process_invoice.py sample_invoice.pdf ./output
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ocr.integration import process_invoice_pdf
from src.models.utils import save_invoice_to_json, invoice_summary


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Process a PDF invoice and save the result to JSON."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_path> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    
    # Check if the PDF file exists
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)
    
    try:
        # Process the PDF
        logger.info(f"Processing PDF: {pdf_path}")
        invoice = process_invoice_pdf(pdf_path, "tesseract")
        
        # Print a summary
        print("\nInvoice Summary:")
        print("-" * 40)
        print(invoice_summary(invoice))
        print("-" * 40)
        
        # Save to JSON
        json_path = save_invoice_to_json(invoice, output_dir)
        logger.info(f"Invoice saved to: {json_path}")
        
        print(f"\nThe invoice has been processed and saved to: {json_path}")
        
    except Exception as e:
        logger.error(f"Error processing invoice: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 