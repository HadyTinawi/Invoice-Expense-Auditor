"""
OCR to Invoice Integration Module

This module integrates the OCR processing with the invoice data model,
providing functions to process a PDF and create a structured invoice object.
"""

import os
import logging
from typing import Dict, Any, Optional, Union

from .processor import create_processor, OCRProcessor, OCRError
from ..models.invoice import Invoice
from ..models.utils import ocr_data_to_invoice
from ..models.validation import validate_invoice_from_ocr


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_invoice_pdf(pdf_path: str, processor_type: str = "tesseract",
                        config: Optional[Dict[str, Any]] = None) -> Invoice:
    """
    Process a PDF invoice and return a structured invoice object.
    
    This function combines OCR processing with invoice data structure creation.
    
    Args:
        pdf_path: Path to the PDF file
        processor_type: OCR processor type ('tesseract' or 'textract')
        config: Optional configuration for the OCR processor
        
    Returns:
        Invoice: A structured invoice object
        
    Raises:
        OCRError: If OCR processing fails
        ValueError: If the required invoice fields are missing
    """
    # Create the OCR processor
    processor = create_processor(processor_type, config)
    
    try:
        # Process the PDF
        logger.info(f"Processing PDF: {pdf_path}")
        ocr_result = processor.process_pdf(pdf_path)
        
        # Add source file information if not already present
        if 'source_file' not in ocr_result:
            ocr_result['source_file'] = pdf_path
        
        # Convert OCR result to Invoice object
        logger.info(f"Creating invoice from OCR data")
        invoice = ocr_data_to_invoice(ocr_result)
        
        # Validate the invoice
        validation_result = validate_invoice_from_ocr(invoice)
        if not validation_result.is_valid:
            logger.warning(f"Invoice validation failed with errors: {validation_result.errors}")
        
        if validation_result.warnings:
            logger.info(f"Invoice has warnings: {validation_result.warnings}")
        
        return invoice
    
    except OCRError as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Invoice creation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise OCRError(f"Failed to process invoice: {str(e)}")


def batch_process_invoices(pdf_directory: str, processor_type: str = "tesseract",
                           config: Optional[Dict[str, Any]] = None) -> Dict[str, Union[Invoice, Exception]]:
    """
    Process multiple PDF invoices from a directory.
    
    Args:
        pdf_directory: Directory containing PDF files
        processor_type: OCR processor type ('tesseract' or 'textract')
        config: Optional configuration for the OCR processor
        
    Returns:
        Dictionary mapping file paths to Invoice objects or exceptions
    """
    results = {}
    
    # Find all PDF files in the directory
    pdf_files = [f for f in os.listdir(pdf_directory) 
                 if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(pdf_directory, f))]
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_directory, pdf_file)
        try:
            invoice = process_invoice_pdf(pdf_path, processor_type, config)
            results[pdf_path] = invoice
            logger.info(f"Successfully processed: {pdf_path}")
        except Exception as e:
            results[pdf_path] = e
            logger.error(f"Failed to process {pdf_path}: {str(e)}")
    
    # Summarize results
    success_count = sum(1 for result in results.values() if isinstance(result, Invoice))
    logger.info(f"Successfully processed {success_count} of {len(pdf_files)} invoices")
    
    return results 