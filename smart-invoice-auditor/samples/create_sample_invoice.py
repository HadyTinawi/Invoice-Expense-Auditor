#!/usr/bin/env python3
"""
Script to create sample invoice PDF and image files for testing OCR.

This script uses wkhtmltopdf to convert the HTML sample invoice to a PDF file,
and then uses pdf2image to convert the PDF to a PNG image.

Requirements:
- wkhtmltopdf must be installed on the system
- pdf2image and PIL packages must be installed

Usage:
    python create_sample_invoice.py
"""

import os
import subprocess
import sys
import logging
from pathlib import Path

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
HTML_PATH = SCRIPT_DIR / "sample_invoice.html"
PDF_PATH = SCRIPT_DIR / "sample_invoice.pdf"
PNG_PATH = SCRIPT_DIR / "sample_invoice.png"


def check_wkhtmltopdf():
    """Check if wkhtmltopdf is installed"""
    try:
        subprocess.run(["which", "wkhtmltopdf"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        logger.error("wkhtmltopdf is not installed. Please install it to generate PDF files.")
        logger.error("macOS: brew install wkhtmltopdf")
        logger.error("Ubuntu/Debian: sudo apt-get install wkhtmltopdf")
        logger.error("Windows: Download from https://wkhtmltopdf.org/downloads.html")
        return False


def html_to_pdf():
    """Convert HTML file to PDF using wkhtmltopdf"""
    if not HTML_PATH.exists():
        logger.error(f"HTML file not found: {HTML_PATH}")
        return False
    
    try:
        logger.info(f"Converting HTML to PDF: {HTML_PATH} -> {PDF_PATH}")
        subprocess.run(
            ["wkhtmltopdf", str(HTML_PATH), str(PDF_PATH)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"PDF created successfully: {PDF_PATH}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting HTML to PDF: {e}")
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
    if not check_wkhtmltopdf():
        return
    
    pdf_success = html_to_pdf()
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