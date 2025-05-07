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
import shutil  # Added for better file handling

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
    temp_path = None
    
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
        
        # Create a temporary file with the same extension
        suffix = Path(file_path).suffix
        
        # Improved file handling for Gradio uploads
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            
            # Handle Gradio file objects more explicitly
            if isinstance(file, gr.File) or hasattr(file, 'name'):
                # Copy the file directly instead of reading/writing
                try:
                    shutil.copy2(file.name, temp_path)
                    log_output.append(f"File copied to temporary location: {temp_path}")
                except Exception as copy_error:
                    log_output.append(f"Error copying file: {str(copy_error)}")
                    # Fallback to read/write method
                    with open(file.name, 'rb') as src_file:
                        file_content = src_file.read()
                        temp_file.write(file_content)
                        log_output.append(f"File content read and written to temporary file: {len(file_content)} bytes")
            else:
                # Handle file-like object with read method
                if hasattr(file, 'read') and callable(file.read):
                    file_content = file.read()
                    temp_file.write(file_content)
                    log_output.append(f"File content read and written to temporary file: {len(file_content)} bytes")
                # Handle string path
                elif isinstance(file, str):
                    with open(file, 'rb') as src_file:
                        file_content = src_file.read()
                        temp_file.write(file_content)
                        log_output.append(f"File content read from path and written to temporary file: {len(file_content)} bytes")
                else:
                    raise ValueError(f"Unsupported file object type: {type(file)}")
        
        # Verify the temporary file exists and is not empty
        if not os.path.exists(temp_path):
            raise FileNotFoundError(f"Temporary file was not created: {temp_path}")
        
        if os.path.getsize(temp_path) == 0:
            raise ValueError(f"Temporary file is empty: {temp_path}")
        
        # Process the file and capture OCR data
        logger.info(f"Processing file: {file_path} (saved as {temp_path})")
        log_output.append(f"Temporary file created at: {temp_path} with size: {os.path.getsize(temp_path)} bytes")
        
        try:
            # First get the raw OCR data
            processor = create_processor(processor_type)
            ocr_data = processor.process_file(temp_path)
            log_output.append(f"OCR processing complete. Confidence: {ocr_data.get('confidence', 0):.2f}%")
            
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
            
            # Generate outputs with proper serialization
            summary = invoice_summary(invoice)
            
            # Convert invoice to dict and then to JSON (avoids serialization issues)
            invoice_dict = invoice.to_dict()  # This should handle proper conversion of custom objects
            json_data = json.dumps(invoice_dict, indent=2, default=str)
            
            raw_text = ocr_data.get("raw_text", "No raw text available")
            
            # Safely serialize OCR data by removing raw_text (which can be large) and 
            # using default=str to handle any non-serializable objects
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
            json_data = json.dumps(error_data, indent=2, default=str)  # Add default=str for serialization
            raw_text = ocr_data.get("raw_text", "No raw text available")
            ocr_json = json.dumps({k: v for k, v in ocr_data.items() if k != 'raw_text'}, indent=2, default=str)
        
        # Clean up the temporary file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            log_output.append("Temporary file deleted")
        log_output.append("Processing complete")
        
        return summary, json_data, raw_text, ocr_json, "\n".join(log_output)
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        log_output.append(f"ERROR: {str(e)}")
        log_output.append(traceback.format_exc())
        
        # Clean up temporary file if it exists
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                log_output.append("Temporary file deleted")
            except Exception as cleanup_error:
                log_output.append(f"Error cleaning up temporary file: {str(cleanup_error)}")
                
        return f"Error: {str(e)}", "{}", "Processing failed", "{}", "\n".join(log_output)

# Function to load and process a sample file
def load_sample(sample_path):
    """Load a sample file and return it as a file object"""
    return sample_path

def main():
    """Create and launch the Gradio interface."""
    # Create a Gradio interface
    with gr.Blocks(title="Invoice OCR Testing") as demo:
        gr.Markdown("# Smart Invoice Auditor - OCR Test")
        gr.Markdown("Upload a PDF or image file (PNG, JPG, TIFF, etc.) to extract invoice information using OCR.")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="Upload Invoice (PDF or Image - PNG, JPG, etc.)")
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
        
        # Add example functionality for sample files
        examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
        
        # Check for sample files
        sample_files = []
        sample_labels = []
        
        sample_pdf_path = os.path.join(examples_dir, "sample_invoice.pdf")
        if os.path.exists(sample_pdf_path):
            sample_files.append(sample_pdf_path)
            sample_labels.append("Sample Invoice (PDF)")
        
        sample_png_path = os.path.join(examples_dir, "sample_invoice.png")
        if os.path.exists(sample_png_path):
            sample_files.append(sample_png_path)
            sample_labels.append("Sample Invoice (PNG)")
        
        # Add examples section if any sample files exist
        if sample_files:
            gr.Markdown("### Sample Invoices")
            with gr.Row():
                for i, (sample_file, label) in enumerate(zip(sample_files, sample_labels)):
                    sample_btn = gr.Button(label)
                    # Set up the click event to load the sample file
                    sample_btn.click(
                        fn=lambda x=sample_file: x,
                        inputs=[], 
                        outputs=[file_input]
                    )
    
    # Launch the interface
    demo.launch(server_port=7865, share=False, inbrowser=True)

if __name__ == "__main__":
    main() 