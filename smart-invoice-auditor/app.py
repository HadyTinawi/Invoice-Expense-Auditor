#!/usr/bin/env python3
"""
Simple UI for testing the OCR functionality of the Smart Invoice Auditor.

This application provides a web interface to upload a PDF or image file
and view the extracted information using the OCR processing module.

Usage:
    python app.py

Then open your browser to http://localhost:7860
"""

import os
import tempfile
import logging
import json
import traceback
import gradio as gr
from pathlib import Path
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ocr.processor import create_processor
from src.models.utils import invoice_summary, ocr_data_to_invoice
from src.models.invoice import Invoice, VendorInfo, LineItem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up a file handler to save logs
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(log_dir, "ocr_ui.log"))
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def process_file(file, processor_type="tesseract"):
    """
    Process an uploaded file using OCR and return the extracted information.
    
    Args:
        file: The uploaded file (PDF or image)
        processor_type: The OCR processor to use ('tesseract' or 'textract')
        
    Returns:
        A tuple of (invoice_summary, json_data, raw_text, ocr_data, log_output)
    """
    log_output = []
    ocr_data = {}
    
    try:
        if file is None:
            return "No file uploaded", "{}", "Please upload a file", "{}", "No file was uploaded to process."
        
        # Log file information
        file_path = file.name if hasattr(file, 'name') else str(file)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else "unknown"
        file_type = Path(file_path).suffix
        
        log_output.append(f"Processing file: {os.path.basename(file_path)}")
        log_output.append(f"File type: {file_type}")
        log_output.append(f"File size: {file_size} bytes")
        log_output.append(f"OCR Processor: {processor_type}")
        
        # Create a temporary file to save the upload
        suffix = Path(file_path).suffix
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            # Handle different file object types
            if hasattr(file, 'read') and callable(file.read):
                # If it's a file-like object with a read method
                temp_file.write(file.read())
            elif isinstance(file, str):
                # If it's a string path
                with open(file, 'rb') as src_file:
                    temp_file.write(src_file.read())
            else:
                # If it's a Gradio file object (which could be different formats)
                if hasattr(file, 'name'):
                    # It's likely a Gradio file object with a path
                    with open(file.name, 'rb') as src_file:
                        temp_file.write(src_file.read())
                else:
                    raise ValueError(f"Unsupported file object type: {type(file)}")
            
            temp_path = temp_file.name
        
        # Process the file and capture OCR data
        logger.info(f"Processing file: {file_path} (saved as {temp_path})")
        log_output.append(f"Temporary file created at: {temp_path}")
        
        try:
            # First get the raw OCR data
            processor = create_processor(processor_type)
            ocr_data = processor.process_pdf(temp_path)
            
            # Enhanced confidence reporting
            confidence = ocr_data.get('confidence', 0)
            log_output.append(f"OCR processing complete. Confidence: {confidence:.2f}%")
            
            # Add confidence quality indicator
            if confidence >= 80:
                confidence_quality = "Excellent"
            elif confidence >= 70:
                confidence_quality = "Good"
            elif confidence >= 60:
                confidence_quality = "Fair"
            elif confidence >= 50:
                confidence_quality = "Poor"
            else:
                confidence_quality = "Very Poor"
                
            log_output.append(f"Extraction quality: {confidence_quality}")
            
            # Log the raw OCR data for debugging
            logger.debug(f"Raw OCR data: {json.dumps(ocr_data, default=str)}")
            
            # Then create the invoice using the OCR data
            invoice = ocr_data_to_invoice(ocr_data, temp_path)
            
            # Log successful field extractions
            log_output.append("\nExtracted fields:")
            log_output.append(f"  - Invoice ID: {invoice.invoice_id}")
            log_output.append(f"  - Vendor: {invoice.vendor.name}")
            log_output.append(f"  - Date: {invoice.issue_date}")
            log_output.append(f"  - Total: {invoice.total}")
            if invoice.subtotal:
                log_output.append(f"  - Subtotal: {invoice.subtotal}")
            if invoice.tax:
                log_output.append(f"  - Tax: {invoice.tax}")
            log_output.append(f"  - Line items: {len(invoice.line_items)}")
            
            # Add extraction confidence statistics for individual fields
            log_output.append("\nField extraction confidence:")
            extraction_confidence = {}
            
            # Determine confidence for each extracted field
            extraction_confidence["invoice_id"] = 85 if invoice.invoice_id and invoice.invoice_id != f"OCR-{datetime.now().strftime('%Y%m%d%H%M%S')}"[:10] else 0
            extraction_confidence["vendor"] = 80 if invoice.vendor.name and invoice.vendor.name != "Unknown Vendor" else 0
            extraction_confidence["date"] = 75 if isinstance(invoice.issue_date, str) and invoice.issue_date != datetime.now().date().isoformat() else 0
            extraction_confidence["total"] = 90 if invoice.total and invoice.total > 0 else 0
            extraction_confidence["line_items"] = 70 if len(invoice.line_items) > 0 and invoice.line_items[0].description != "Unspecified Item (OCR could not extract line items)" else 0
            
            # Log field extraction confidence
            for field, confidence in extraction_confidence.items():
                status = "✓" if confidence > 0 else "✗"
                log_output.append(f"  - {field.capitalize()}: {status} {confidence}%")
            
            # Calculate overall extraction quality
            extraction_values = [c for c in extraction_confidence.values() if c > 0]
            if extraction_values:
                avg_extraction_quality = sum(extraction_values) / len(extraction_values)
                log_output.append(f"\nOverall extraction quality: {avg_extraction_quality:.2f}%")
            
            # Generate outputs with proper serialization
            summary = invoice_summary(invoice)
            
            # Convert invoice to dict and then to JSON (avoids serialization issues)
            invoice_dict = invoice.to_dict()  # This should handle proper conversion of custom objects
            json_data = json.dumps(invoice_dict, indent=2)
            
            raw_text = ocr_data.get("raw_text", "No raw text available")
            
            # Safely serialize OCR data
            safe_ocr_data = {k: v for k, v in ocr_data.items() if k != 'raw_text'}
            ocr_json = json.dumps(safe_ocr_data, indent=2, default=str)
            
        except Exception as e:
            # If the OCR process failed, create a minimal invoice with the error
            logger.error(f"OCR processing error: {str(e)}")
            log_output.append(f"ERROR: {str(e)}")
            log_output.append(traceback.format_exc())
            
            # Check if we got any OCR data before the failure
            if not ocr_data:
                ocr_data = {"error": str(e)}
            
            # Create a dict with the error message instead of an Invoice object
            error_data = {
                "error": str(e),
                "invoice_id": "ERROR",
                "vendor": {"name": "OCR Processing Failed"},
                "issue_date": datetime.now().isoformat(),
                "line_items": [],
                "total": "0.00",
                "raw_text": ocr_data.get("raw_text", "")
            }
            
            # Generate outputs
            summary = f"Error: {str(e)}"
            json_data = json.dumps(error_data, indent=2)
            raw_text = ocr_data.get("raw_text", "No raw text available")
            ocr_json = json.dumps({k: v for k, v in ocr_data.items() if k != 'raw_text'}, indent=2, default=str)
        
        # Clean up the temporary file
        os.unlink(temp_path)
        log_output.append("Temporary file deleted")
        log_output.append("Processing complete")
        
        return summary, json_data, raw_text, ocr_json, "\n".join(log_output)
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        log_output.append(f"ERROR: {str(e)}")
        log_output.append(traceback.format_exc())
        return f"Error: {str(e)}", "{}", "Processing failed", "{}", "\n".join(log_output)

def main():
    """Create and launch the Gradio interface."""
    # Create a Gradio interface
    with gr.Blocks(title="Invoice OCR Testing") as demo:
        gr.Markdown("# Smart Invoice Auditor - OCR Test")
        gr.Markdown("Upload a PDF or image file to extract invoice information using OCR.")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="Upload Invoice (PDF or Image)")
                processor_type = gr.Radio(
                    ["tesseract", "textract"], 
                    label="OCR Processor", 
                    value="tesseract",
                    info="Choose the OCR processor to use"
                )
                process_btn = gr.Button("Process Invoice", variant="primary")
            
            with gr.Column(scale=2):
                summary_output = gr.Textbox(label="Invoice Summary", lines=10)
                log_output = gr.Textbox(label="Processing Log", lines=8)
        
        with gr.Tabs():
            with gr.TabItem("Invoice Data"):
                json_output = gr.JSON(label="Structured Invoice Data")
            with gr.TabItem("OCR Raw Data"):
                ocr_output = gr.JSON(label="Raw OCR Data")
            with gr.TabItem("Extracted Text"):
                text_output = gr.Textbox(label="Extracted Raw Text", lines=20)
        
        # Set up the processing action
        process_btn.click(
            fn=process_file,
            inputs=[file_input, processor_type],
            outputs=[summary_output, json_output, text_output, ocr_output, log_output]
        )
        
        # Add example functionality with our sample files
        examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
        examples = []
        
        sample_pdf = os.path.join(examples_dir, "sample_invoice.pdf")
        sample_png = os.path.join(examples_dir, "sample_invoice.png")
        
        if os.path.exists(sample_pdf):
            examples.append(sample_pdf)
        if os.path.exists(sample_png):
            examples.append(sample_png)
            
        if examples:
            gr.Examples(
                examples=examples,
                inputs=file_input
            )
    
    # Launch the interface
    demo.launch(share=False, inbrowser=True)

if __name__ == "__main__":
    main() 