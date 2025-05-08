#!/usr/bin/env python3
"""
Smart Invoice Checker - Simple UI

A simple tool to check invoices for mistakes and policy problems.
Upload PDF or image files and get results quickly.

Usage:
    python simple_app.py
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
import shutil
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
file_handler = logging.FileHandler(os.path.join(log_dir, "invoice_checker.log"))
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Global variables for tracking invoices
processed_invoices = {}
policies_cache = {}
policy_manager = PolicyManager()

def process_and_audit_file(files, processor_type="tesseract", auto_audit=True):
    """
    Process files and check for problems automatically
    
    Args:
        files: List of uploaded files (PDF or images)
        processor_type: OCR tool to use (tesseract or textract)
        auto_audit: Whether to run AI check automatically
        
    Returns:
        Processing summary, list of problems found, and detailed data
    """
    if not files:
        return "Please upload invoice files", "", ""
    
    all_results = []
    all_problems = []
    all_data = {}
    
    # Process each file
    for file in files:
        file_path = file.name if hasattr(file, 'name') else str(file)
        filename = os.path.basename(file_path)
        
        result = f"📄 {filename}:\n"
        temp_path = None
        
        try:
            # Create temporary file
            suffix = Path(file_path).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_path = temp_file.name
                shutil.copy2(file_path, temp_path)
            
            # Process with OCR
            processor = create_processor(processor_type)
            ocr_data = processor.process_file(temp_path)
            
            # Create invoice object
            invoice = ocr_data_to_invoice(ocr_data, temp_path)
            
            # Store with unique ID
            invoice_id = str(uuid.uuid4())
            processed_invoices[invoice_id] = {
                "invoice_object": invoice,
                "ocr_data": ocr_data,
                "file_path": file_path,
                "processed_time": datetime.now().isoformat()
            }
            
            # Basic invoice info
            result += f"• Invoice ID: {invoice.invoice_id}\n"
            result += f"• Company: {invoice.vendor.name}\n"
            result += f"• Date: {invoice.issue_date}\n"
            result += f"• Amount: ${invoice.total:.2f}\n"
            
            # Run AI check if requested
            if auto_audit:
                # Get policy
                vendor_name = invoice.vendor.name if invoice.vendor and invoice.vendor.name else "Unknown"
                if vendor_name in policies_cache:
                    policy_data = policies_cache[vendor_name]
                else:
                    policy_data = policy_manager.get_policy(vendor_name)
                    if not policy_data:
                        # Try to find default policy
                        policy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "policies")
                        default_policy_files = [f for f in os.listdir(policy_dir) if f.endswith('.json')]
                        if default_policy_files:
                            default_policy_path = os.path.join(policy_dir, default_policy_files[0])
                            policy_data = policy_manager._load_json_policy(default_policy_path)
                        else:
                            policy_data = {}
                    policies_cache[vendor_name] = policy_data
                
                # Configure the AI
                agent_config = {
                    "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
                    "temperature": 0.0,
                    "verbose": os.environ.get("AGENT_VERBOSE", "false").lower() == "true",
                    "use_agent_analysis": os.environ.get("USE_AGENT_ANALYSIS", "true").lower() == "true"
                }
                
                try:
                    # Run AI check
                    workflow = AuditWorkflow(config=agent_config)
                    audit_result = workflow.run_audit(ocr_data, policy_data)
                    
                    # Get issues
                    if "issues" in audit_result and audit_result["issues"]:
                        result += f"\n🚨 Found {len(audit_result['issues'])} problems:\n"
                        problems = []
                        for i, issue in enumerate(audit_result["issues"], 1):
                            severity = issue.get("severity", "medium")
                            severity_icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
                            issue_desc = f"{severity_icon} {issue.get('description', 'No description')}"
                            problems.append(issue_desc)
                        
                        result += "\n".join(f"  {p}" for p in problems)
                        all_problems.extend(problems)
                    else:
                        result += "\n✅ No problems found. Invoice looks good!"
                    
                    # Add summary
                    if "summary" in audit_result:
                        result += f"\n\n📝 Summary: {audit_result['summary']}"
                    
                    # Store detailed data
                    all_data[filename] = {
                        "invoice": invoice.to_dict(),
                        "audit_result": audit_result
                    }
                except Exception as e:
                    logger.error(f"Error during AI check: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Fallback to basic checks if AI check fails
                    result += f"\n⚠️ AI check failed: {str(e)}"
                    result += "\n🔍 Performing basic checks instead:"
                    
                    # Basic check: Verify total matches sum of line items
                    basic_issues = []
                    
                    # Check if invoice has line items
                    if not invoice.line_items or len(invoice.line_items) == 0:
                        basic_issues.append("🟡 No line items found in invoice")
                    
                    # Check if total amount is very small or zero
                    if invoice.total <= 0:
                        basic_issues.append("🔴 Invoice total is zero or negative")
                    
                    # Check if missing critical info
                    if not invoice.invoice_id or invoice.invoice_id.startswith("OCR-"):
                        basic_issues.append("🟡 Invoice ID not detected properly")
                    
                    if not invoice.vendor or not invoice.vendor.name:
                        basic_issues.append("🟡 Vendor name not detected")
                    
                    # Policy check if policy_data is available
                    if policy_data:
                        # Check expense limits
                        max_amount = policy_data.get("max_amount", {}).get("total", float('inf'))
                        if invoice.total > max_amount:
                            basic_issues.append(f"🔴 Invoice total (${invoice.total:.2f}) exceeds company limit (${max_amount:.2f})")
                    
                    # Display findings
                    if basic_issues:
                        result += "\n" + "\n".join(f"  {issue}" for issue in basic_issues)
                        all_problems.extend(basic_issues)
                    else:
                        result += "\n  ✅ Basic checks passed. Invoice appears valid."
                    
                    # Create a basic audit result for the data output
                    basic_audit_result = {
                        "invoice_id": invoice.invoice_id,
                        "vendor": invoice.vendor.name if invoice.vendor else "Unknown",
                        "total": invoice.total,
                        "issues_found": len(basic_issues) > 0,
                        "issues": [{"description": issue, "severity": "medium", "source": "basic_check"} for issue in basic_issues],
                        "summary": "Basic invoice validation completed. AI check failed."
                    }
                    
                    all_data[filename] = {
                        "invoice": invoice.to_dict(),
                        "audit_result": basic_audit_result
                    }
            
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            logger.error(traceback.format_exc())
            result += f"\n❌ Error: {str(e)}"
        
        all_results.append(result)
    
    # Combine results
    summary = "\n\n".join(all_results)
    
    # Format problems list
    problems_summary = ""
    if all_problems:
        problems_summary = "All problems found:\n\n" + "\n".join(all_problems)
    else:
        problems_summary = "✅ No problems found in any invoices."
    
    # Format detailed data
    detailed_data = json.dumps(all_data, indent=2, default=str)
    
    return summary, problems_summary, detailed_data

def main():
    """Create and launch the simple Gradio interface."""
    # Create a simple Gradio interface
    with gr.Blocks(title="Invoice Checker") as demo:
        gr.Markdown("# Simple Invoice Checker")
        gr.Markdown("Upload invoices to check for mistakes and policy problems")
        
        with gr.Row():
            with gr.Column():
                # Upload section
                files_input = gr.File(
                    label="Upload Invoice Files (PDF, PNG, JPG, etc.)",
                    file_count="multiple",
                    type="file"
                )
                
                with gr.Row():
                    processor_type = gr.Radio(
                        ["tesseract", "textract"],
                        label="Text Reading Tool",
                        value="tesseract",
                        info="Choose OCR tool (tesseract works on most computers)"
                    )
                    auto_audit = gr.Checkbox(
                        label="Check for Problems",
                        value=True,
                        info="Automatically check invoices for mistakes"
                    )
                
                process_btn = gr.Button("Process Invoices", variant="primary", size="lg")
                
                # Sample files
                examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
                sample_files = []
                
                sample_pdf_path = os.path.join(examples_dir, "sample_invoice.pdf")
                if os.path.exists(sample_pdf_path):
                    sample_files.append(sample_pdf_path)
                
                sample_png_path = os.path.join(examples_dir, "sample_invoice.png")
                if os.path.exists(sample_png_path):
                    sample_files.append(sample_png_path)
                
                if sample_files:
                    gr.Examples(
                        examples=sample_files,
                        inputs=files_input,
                        label="Example Invoices"
                    )
            
            with gr.Column():
                # Results section
                with gr.Tabs():
                    with gr.TabItem("Processing Results"):
                        result_text = gr.Textbox(
                            label="Processing Results",
                            lines=15,
                            placeholder="Upload and process invoices to see results here"
                        )
                    
                    with gr.TabItem("Problems Found"):
                        problems_text = gr.Textbox(
                            label="Problems Found",
                            lines=15,
                            placeholder="Any problems found in the invoices will appear here"
                        )
                    
                    with gr.TabItem("Detailed Data"):
                        data_json = gr.JSON(
                            label="Detailed Data",
                            value={},
                        )
        
        # Process button action
        process_btn.click(
            fn=process_and_audit_file,
            inputs=[files_input, processor_type, auto_audit],
            outputs=[result_text, problems_text, data_json]
        )
    
    # Launch the interface
    demo.launch(server_port=7865, share=False, inbrowser=True)

if __name__ == "__main__":
    main() 