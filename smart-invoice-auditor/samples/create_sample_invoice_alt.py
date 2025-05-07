#!/usr/bin/env python3
"""
Script to create sample invoice PDF and image files for testing OCR.

This script uses reportlab to create a PDF invoice and then pdf2image
to convert the PDF to a PNG image for testing OCR.

Requirements:
- reportlab, pdf2image, and pillow packages must be installed

Usage:
    python create_sample_invoice_alt.py
"""

import os
import sys
import logging
from pathlib import Path
from decimal import Decimal
from datetime import date

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
except ImportError:
    print("reportlab package is required. Install it with: pip install reportlab")
    sys.exit(1)

try:
    from pdf2image import convert_from_path
except ImportError:
    print("pdf2image package is required. Install it with: pip install pdf2image")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the directory where this script is located
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = SCRIPT_DIR / "sample_invoice.pdf"
PNG_PATH = SCRIPT_DIR / "sample_invoice.png"


def create_invoice_pdf():
    """Create a sample invoice PDF using reportlab"""
    try:
        logger.info(f"Creating sample invoice PDF: {PDF_PATH}")
        
        # Create a PDF document
        doc = SimpleDocTemplate(
            str(PDF_PATH),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Create story (content) for the PDF
        story = []
        styles = getSampleStyleSheet()
        
        # Add company header
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading1'],
            alignment=1,  # Center alignment
            spaceAfter=12
        )
        story.append(Paragraph("Acme Corporation", header_style))
        story.append(Paragraph("123 Main Street, Anytown, CA 12345", styles['Normal']))
        story.append(Paragraph("Tel: (555) 123-4567 | Email: billing@acmecorp.com", styles['Normal']))
        story.append(Paragraph("Tax ID: 12-3456789", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add invoice title
        story.append(Paragraph("INVOICE", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Add customer and invoice details in a table
        customer_data = [
            ["Bill To:", "Invoice #: INV-12345"],
            ["XYZ Enterprises Ltd.", f"Date: June 15, 2023"],
            ["456 Oak Avenue", "Due Date: July 15, 2023"],
            ["Somewhere, NY 10001", "Terms: Net 30"],
            ["Attn: Accounts Payable", ""]
        ]
        
        customer_table = Table(customer_data, colWidths=[doc.width/2.0]*2)
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(customer_table)
        story.append(Spacer(1, 20))
        
        # Add line items
        line_items = [
            ["Description", "Quantity", "Unit Price", "Amount"],
            ["Web Development Services", "20", "$150.00", "$3,000.00"],
            ["Server Hosting (Monthly)", "1", "$99.95", "$99.95"],
            ["Domain Registration", "2", "$15.00", "$30.00"],
            ["", "", "", ""],
            ["", "", "Subtotal:", "$3,129.95"],
            ["", "", "Tax (8%):", "$250.40"],
            ["", "", "TOTAL:", "$3,380.35"]
        ]
        
        line_item_table = Table(line_items, colWidths=[doc.width*0.4, doc.width*0.2, doc.width*0.2, doc.width*0.2])
        line_item_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
            ('GRID', (0, 0), (3, 3), 0.5, colors.black),
            ('ALIGN', (2, 5), (2, 7), 'RIGHT'),
            ('FONTNAME', (2, 7), (3, 7), 'Helvetica-Bold'),
            ('LINEABOVE', (2, 7), (3, 7), 1, colors.black),
        ]))
        story.append(line_item_table)
        story.append(Spacer(1, 30))
        
        # Add footer
        story.append(Paragraph("Payment Methods: Bank Transfer, Credit Card, or Check", styles['Normal']))
        story.append(Paragraph("Please include the invoice number with your payment", styles['Normal']))
        story.append(Paragraph("Thank you for your business!", styles['Normal']))
        
        # Build the PDF
        doc.build(story)
        logger.info(f"PDF created successfully: {PDF_PATH}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        return False


def pdf_to_png():
    """Convert PDF to PNG image using pdf2image"""
    if not PDF_PATH.exists():
        logger.error(f"PDF file not found: {PDF_PATH}")
        return False
    
    try:
        logger.info(f"Converting PDF to PNG: {PDF_PATH} -> {PNG_PATH}")
        pages = convert_from_path(PDF_PATH, 300)  # DPI=300 for good quality
        if pages:
            pages[0].save(PNG_PATH, 'PNG')
            logger.info(f"PNG created successfully: {PNG_PATH}")
            return True
        else:
            logger.error("No pages were converted from the PDF")
            return False
    except Exception as e:
        logger.error(f"Error converting PDF to PNG: {e}")
        return False


def main():
    """Main function to create the sample invoice files"""
    # Install required packages if not installed
    try:
        import pkg_resources
        missing_packages = []
        for package in ['reportlab', 'pdf2image', 'pillow']:
            try:
                pkg_resources.get_distribution(package)
            except pkg_resources.DistributionNotFound:
                missing_packages.append(package)
        
        if missing_packages:
            logger.warning(f"Missing packages: {', '.join(missing_packages)}")
            logger.warning("Please install them with: pip install " + " ".join(missing_packages))
            return
    except ImportError:
        pass
    
    pdf_success = create_invoice_pdf()
    if not pdf_success:
        return
    
    png_success = pdf_to_png()
    if not png_success:
        return
    
    logger.info("Sample invoice files created successfully")
    logger.info(f"PDF: {PDF_PATH}")
    logger.info(f"PNG: {PNG_PATH}")
    logger.info("You can now use these files to test the OCR functionality.")


if __name__ == "__main__":
    main() 