#!/usr/bin/env python3
"""
Smart Invoice Auditor - Web Interface

This application provides a web interface to upload PDF and image files,
extract information using OCR, and analyze invoices using AI agents.

Usage:
    python app.py

Then open your browser to http://localhost:7865
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
from typing import List, Dict, Any, Union, Optional
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ocr.processor import create_processor
from src.models.utils import invoice_summary, ocr_data_to_invoice
from src.models.invoice import Invoice, VendorInfo, LineItem
from src.agent.auditor import AuditorAgent
from src.agent.workflow import AuditWorkflow
from src.policy.manager import PolicyManager

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

# Global variables to track processed invoices and their audit results
processed_invoices = {}
audit_results = {}
policies_cache = {}
policy_manager = PolicyManager()

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
            
            # Store invoice in global dictionary with a unique ID
            invoice_id = str(uuid.uuid4())
            processed_invoices[invoice_id] = {
                "invoice_object": invoice,
                "ocr_data": ocr_data,
                "file_path": file_path,
                "processed_time": datetime.now().isoformat()
            }
            
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
        
        return summary, json_data, raw_text, ocr_json, "\n".join(log_output), invoice_id
    
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
                
        return f"Error: {str(e)}", "{}", "Processing failed", "{}", "\n".join(log_output), ""

def process_multiple_files(files, processor_type="tesseract"):
    """
    Process multiple uploaded files using OCR
    
    Args:
        files: List of uploaded files
        processor_type: OCR processor to use
        
    Returns:
        A summary of processed files and a list of invoice IDs
    """
    if not files:
        return "No files uploaded", []
    
    processed_ids = []
    summaries = []
    
    for file in files:
        summary, _, _, _, log, invoice_id = process_file(file, processor_type)
        if invoice_id:
            processed_ids.append(invoice_id)
            filename = os.path.basename(file.name) if hasattr(file, 'name') else "Unknown file"
            summaries.append(f"✅ {filename}: {summary}")
        else:
            filename = os.path.basename(file.name) if hasattr(file, 'name') else "Unknown file"
            summaries.append(f"❌ {filename}: Processing failed")
    
    return "\n\n".join(summaries), processed_ids

def get_invoice_details(invoice_id):
    """
    Get details for a specific invoice
    
    Args:
        invoice_id: The ID of the processed invoice
        
    Returns:
        Invoice details formatted for display
    """
    if not invoice_id or invoice_id not in processed_invoices:
        return "No invoice selected", "{}", "", "{}"
    
    invoice_data = processed_invoices[invoice_id]
    invoice = invoice_data["invoice_object"]
    
    # Generate summary
    summary = invoice_summary(invoice)
    
    # Get JSON representation
    invoice_dict = invoice.to_dict()
    json_data = json.dumps(invoice_dict, indent=2, default=str)
    
    # Get raw text
    raw_text = invoice_data["ocr_data"].get("raw_text", "No raw text available")
    
    # Get safe OCR data
    safe_ocr_data = {k: v for k, v in invoice_data["ocr_data"].items() if k != 'raw_text'}
    ocr_json = json.dumps(safe_ocr_data, indent=2, default=str)
    
    return summary, json_data, raw_text, ocr_json

def audit_invoice(invoice_id, use_workflow=True):
    """
    Audit an invoice using AI agent or workflow
    
    Args:
        invoice_id: The ID of the processed invoice
        use_workflow: Whether to use the LangGraph workflow (True) or LangChain agent (False)
        
    Returns:
        Audit results
    """
    if not invoice_id or invoice_id not in processed_invoices:
        return "No invoice selected or invoice not found", "{}"
    
    invoice_data = processed_invoices[invoice_id]
    ocr_data = invoice_data["ocr_data"]
    invoice = invoice_data["invoice_object"]
    
    # Try to get policy for the vendor
    vendor_name = invoice.vendor.name if invoice.vendor and invoice.vendor.name else "Unknown"
    
    if vendor_name in policies_cache:
        policy_data = policies_cache[vendor_name]
    else:
        policy_data = policy_manager.get_policy(vendor_name)
        if policy_data:
            policies_cache[vendor_name] = policy_data
        else:
            # Use a default policy if none exists for this vendor
            policy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "policies")
            default_policy_files = [f for f in os.listdir(policy_dir) if f.endswith('.json')]
            
            if default_policy_files:
                default_policy_path = os.path.join(policy_dir, default_policy_files[0])
                policy_data = policy_manager._load_json_policy(default_policy_path)
                policies_cache[vendor_name] = policy_data
            else:
                policy_data = {}
    
    # Configure agent
    agent_config = {
        "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "temperature": 0.0,
        "verbose": os.environ.get("AGENT_VERBOSE", "false").lower() == "true",
        "use_agent_analysis": os.environ.get("USE_AGENT_ANALYSIS", "true").lower() == "true"
    }
    
    try:
        if use_workflow:
            # Use LangGraph workflow
            workflow = AuditWorkflow(config=agent_config)
            result = workflow.run_audit(ocr_data, policy_data)
        else:
            # Use LangChain agent
            auditor = AuditorAgent(config=agent_config)
            result = auditor.audit_invoice(ocr_data, policy_data)
        
        # Store audit result
        audit_results[invoice_id] = result
        
        # Format issues for display
        issues_summary = ""
        if "issues" in result and result["issues"]:
            issues_summary = "Issues found:\n\n"
            for i, issue in enumerate(result["issues"]):
                severity = issue.get("severity", "medium")
                severity_marker = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
                issues_summary += f"{severity_marker} {issue.get('type', 'Issue')}: {issue.get('description', 'No description')}\n"
        else:
            issues_summary = "✅ No issues found! This invoice passed all checks."
        
        if "summary" in result:
            issues_summary += f"\nSummary: {result['summary']}"
        
        return issues_summary, json.dumps(result, indent=2, default=str)
    
    except Exception as e:
        logger.error(f"Error auditing invoice: {str(e)}")
        error_message = f"Error during audit: {str(e)}"
        return error_message, json.dumps({"error": str(e)}, indent=2)

def load_sample(sample_path):
    """Load a sample file and return it as a file object"""
    return sample_path

def get_available_policies():
    """Get a list of available policy files"""
    policy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "policies")
    
    if not os.path.exists(policy_dir):
        os.makedirs(policy_dir, exist_ok=True)
        return []
    
    policy_files = [f for f in os.listdir(policy_dir) if f.endswith(('.json', '.csv'))]
    return [os.path.splitext(f)[0] for f in policy_files]

def refresh_invoice_list():
    """Refresh the list of processed invoices"""
    invoice_options = []
    
    for invoice_id, data in processed_invoices.items():
        invoice = data["invoice_object"]
        vendor_name = invoice.vendor.name if invoice.vendor and invoice.vendor.name else "Unknown"
        invoice_number = invoice.invoice_id or "Unknown"
        total = f"${invoice.total:.2f}" if isinstance(invoice.total, (int, float)) else str(invoice.total)
        
        # Format date for display
        date_str = str(invoice.issue_date) if invoice.issue_date else "Unknown"
        
        label = f"{vendor_name} - {invoice_number} - {date_str} - {total}"
        invoice_options.append((label, invoice_id))
    
    return gr.Dropdown.update(choices=invoice_options)

def main():
    """Create and launch the Gradio interface."""
    # Create a Gradio interface
    with gr.Blocks(title="Smart Invoice Auditor") as demo:
        gr.Markdown("# Smart Invoice Auditor")
        gr.Markdown("AI-powered invoice processing and auditing system")
        
        with gr.Tabs() as tabs:
            # Tab 1: Invoice Processing
            with gr.TabItem("Process Invoices"):
                gr.Markdown("Upload invoice files (PDF, PNG, JPG, etc.) for processing")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        file_input = gr.File(label="Upload Invoices", file_count="multiple")
                        processor_type = gr.Radio(
                            ["tesseract", "textract"], 
                            label="OCR Processor", 
                            value="tesseract",
                            info="Choose the OCR processor to use"
                        )
                        process_btn = gr.Button("Process Invoices", variant="primary")
                    
                    with gr.Column(scale=2):
                        processing_summary = gr.Textbox(label="Processing Summary", lines=10)
                        invoice_list = gr.Dropdown(
                            label="Processed Invoices", 
                            choices=[], 
                            interactive=True,
                            allow_custom_value=False
                        )
                        refresh_btn = gr.Button("Refresh Invoice List")
                
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
                                fn=lambda x=sample_file: [x],
                                inputs=[], 
                                outputs=[file_input]
                            )
            
            # Tab 2: Invoice Details
            with gr.TabItem("Invoice Details"):
                with gr.Row():
                    with gr.Column(scale=1):
                        details_invoice_list = gr.Dropdown(
                            label="Select Invoice", 
                            choices=[], 
                            interactive=True,
                            allow_custom_value=False
                        )
                        refresh_details_btn = gr.Button("Refresh List")
                    
                    with gr.Column(scale=2):
                        invoice_summary = gr.Textbox(label="Invoice Summary", lines=8)
                
                with gr.Tabs():
                    with gr.TabItem("Invoice Data"):
                        invoice_json = gr.JSON(label="Structured Invoice Data")
                    with gr.TabItem("OCR Raw Data"):
                        ocr_json = gr.JSON(label="Raw OCR Data")
                    with gr.TabItem("Extracted Text"):
                        extracted_text = gr.Textbox(label="Raw Text", lines=20)
            
            # Tab 3: AI Auditor
            with gr.TabItem("AI Auditor"):
                gr.Markdown("Analyze invoices for errors, policy violations, and potential fraud")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        audit_invoice_list = gr.Dropdown(
                            label="Select Invoice to Audit", 
                            choices=[], 
                            interactive=True,
                            allow_custom_value=False
                        )
                        use_workflow = gr.Checkbox(
                            label="Use Advanced Workflow",
                            value=True,
                            info="Use the more advanced LangGraph workflow"
                        )
                        audit_btn = gr.Button("Audit Invoice", variant="primary")
                        refresh_audit_btn = gr.Button("Refresh List")
                    
                    with gr.Column(scale=2):
                        audit_summary = gr.Textbox(label="Audit Results", lines=10)
                        audit_details = gr.JSON(label="Detailed Audit Data")
                        
                gr.Markdown("### Available Policies")
                policies_list = gr.Dropdown(
                    label="Available Vendor Policies",
                    choices=get_available_policies(),
                    interactive=True,
                    allow_custom_value=False
                )
            
            # Tab 4: Batch Processing
            with gr.TabItem("Batch Processing"):
                gr.Markdown("Batch process and audit multiple invoices")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        batch_file_input = gr.File(label="Upload Multiple Invoices", file_count="multiple")
                        batch_processor = gr.Radio(
                            ["tesseract", "textract"], 
                            label="OCR Processor", 
                            value="tesseract"
                        )
                        auto_audit = gr.Checkbox(
                            label="Automatically Audit",
                            value=True,
                            info="Automatically run AI audit after processing"
                        )
                        batch_process_btn = gr.Button("Process & Audit Batch", variant="primary")
                    
                    with gr.Column(scale=2):
                        batch_summary = gr.Textbox(label="Batch Processing Results", lines=15)
                        batch_log = gr.Textbox(label="Processing Log", lines=10)
        
        # Set up UI logic and callbacks
        
        # Process invoices
        process_btn.click(
            fn=process_multiple_files,
            inputs=[file_input, processor_type],
            outputs=[processing_summary, invoice_list]
        )
        
        # Refresh invoice lists
        refresh_btn.click(fn=refresh_invoice_list, inputs=[], outputs=[invoice_list])
        refresh_details_btn.click(fn=refresh_invoice_list, inputs=[], outputs=[details_invoice_list])
        refresh_audit_btn.click(fn=refresh_invoice_list, inputs=[], outputs=[audit_invoice_list])
        
        # Display invoice details
        details_invoice_list.change(
            fn=get_invoice_details,
            inputs=[details_invoice_list],
            outputs=[invoice_summary, invoice_json, extracted_text, ocr_json]
        )
        
        # Keep all invoice lists synchronized
        invoice_list.change(lambda x: x, inputs=[invoice_list], outputs=[details_invoice_list, audit_invoice_list])
        details_invoice_list.change(lambda x: x, inputs=[details_invoice_list], outputs=[invoice_list, audit_invoice_list])
        audit_invoice_list.change(lambda x: x, inputs=[audit_invoice_list], outputs=[invoice_list, details_invoice_list])
        
        # Audit invoice
        audit_btn.click(
            fn=audit_invoice,
            inputs=[audit_invoice_list, use_workflow],
            outputs=[audit_summary, audit_details]
        )
        
        # Handle batch processing
        def process_and_audit_batch(files, processor_type, auto_audit):
            """Process a batch of files and optionally audit them"""
            if not files:
                return "No files uploaded", "Batch processing cancelled: no files provided"
            
            # Process all files
            summary, processed_ids = process_multiple_files(files, processor_type)
            
            batch_log = f"Processed {len(processed_ids)} of {len(files)} files successfully.\n"
            
            # Audit if requested
            if auto_audit and processed_ids:
                batch_log += "\nAuditing invoices:\n"
                audit_results_summary = []
                
                for invoice_id in processed_ids:
                    invoice_data = processed_invoices[invoice_id]
                    invoice = invoice_data["invoice_object"]
                    vendor_name = invoice.vendor.name if invoice.vendor and invoice.vendor.name else "Unknown"
                    invoice_number = invoice.invoice_id or "Unknown"
                    
                    batch_log += f"\nAuditing invoice {invoice_number} from {vendor_name}...\n"
                    
                    try:
                        audit_summary, _ = audit_invoice(invoice_id, True)
                        short_summary = audit_summary.split('\n')[0]
                        
                        if "No issues found" in audit_summary:
                            audit_results_summary.append(f"✅ {vendor_name} - {invoice_number}: No issues found")
                        else:
                            audit_results_summary.append(f"⚠️ {vendor_name} - {invoice_number}: Issues detected")
                        
                        batch_log += f"Result: {short_summary}\n"
                    except Exception as e:
                        batch_log += f"Error during audit: {str(e)}\n"
                        audit_results_summary.append(f"❌ {vendor_name} - {invoice_number}: Audit failed")
                
                if audit_results_summary:
                    summary += "\n\n--- Audit Results ---\n" + "\n".join(audit_results_summary)
            
            # Refresh lists
            refresh_invoice_list()
            
            return summary, batch_log
        
        batch_process_btn.click(
            fn=process_and_audit_batch,
            inputs=[batch_file_input, batch_processor, auto_audit],
            outputs=[batch_summary, batch_log]
        )
        
        # Initial policy list load
        policies_list.update(choices=get_available_policies())
    
    # Launch the interface
    demo.launch(server_port=7865, share=False, inbrowser=True)

if __name__ == "__main__":
    main() 