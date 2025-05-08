#!/usr/bin/env python3
"""
Test script to verify the integration of OCR and agent components.
This script tests the OCR functionality with both PDF and PNG files,
and ensures the data can be passed to the auditor agent framework.
"""

import os
import sys
import logging
import json
from pathlib import Path

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ocr.processor import create_processor
from src.models.utils import ocr_data_to_invoice
from src.policy.manager import PolicyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ocr_integration(file_path, processor_type="tesseract"):
    """
    Test that OCR processing works correctly and can extract structured data
    from both PDF and image files.
    """
    logger.info(f"Testing OCR processing for file: {file_path}")
    logger.info(f"File size: {os.path.getsize(file_path)} bytes")
    
    # Create OCR processor
    processor = create_processor(processor_type)
    
    # Process the file (this now works for both PDF and image files)
    try:
        ocr_data = processor.process_file(file_path)
        logger.info(f"OCR processing complete. Confidence: {ocr_data.get('confidence', 0):.2f}%")
        
        # Convert to invoice object
        invoice = ocr_data_to_invoice(ocr_data, file_path)
        logger.info(f"Successfully created invoice object: {invoice.invoice_id}")
        
        # Print invoice details
        logger.info("Invoice details:")
        logger.info(f"  - ID: {invoice.invoice_id}")
        logger.info(f"  - Date: {invoice.issue_date}")
        logger.info(f"  - Vendor: {invoice.vendor.name}")
        logger.info(f"  - Total: {invoice.total}")
        logger.info(f"  - Line items: {len(invoice.line_items)}")
        
        return ocr_data, invoice
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None

def test_agent_integration(ocr_data, policy_path):
    """
    Test that the agent framework can process OCR data without requiring API calls.
    This is a simplified version that doesn't use the LangChain components.
    """
    if not ocr_data:
        logger.error("No OCR data provided to agent integration test")
        return None
    
    logger.info(f"Testing agent integration with OCR data (vendor: {ocr_data.get('vendor', 'Unknown')})")
    
    # Load policy data
    policy_manager = PolicyManager()
    policy_data = {}
    
    if policy_path and os.path.exists(policy_path):
        logger.info(f"Loading policy from: {policy_path}")
        
        if policy_path.endswith('.csv'):
            vendor_name = os.path.splitext(os.path.basename(policy_path))[0]
            policy_data = policy_manager._load_csv_policy(policy_path)
        elif policy_path.endswith('.json'):
            vendor_name = os.path.splitext(os.path.basename(policy_path))[0]
            policy_data = policy_manager._load_json_policy(policy_path)
        else:
            logger.error(f"Unsupported policy file format: {policy_path}")
            return None
    else:
        # Try to find policy based on vendor name
        vendor_name = ocr_data.get("vendor", "UNKNOWN")
        policy_data = policy_manager.get_policy(vendor_name)
        
        if not policy_data:
            logger.warning(f"No policy found for vendor: {vendor_name}")
    
    # Simulated audit results without requiring API calls
    # This tests the data integration, not the actual AI analysis
    audit_results = {
        "invoice_id": ocr_data.get("invoice_id", "UNKNOWN"),
        "vendor": ocr_data.get("vendor", "UNKNOWN"),
        "total": ocr_data.get("total", 0.0),
        "issues": [],  # This would normally be populated by the agent
        "summary": "Invoice appears to be valid based on initial checks.",
        "timestamp": ocr_data.get("timestamp", "")
    }
    
    # Add a simulated issue if the total exceeds a policy limit (for testing)
    total = float(ocr_data.get("total", 0.0))
    if policy_data and "rules" in policy_data:
        for rule in policy_data.get("rules", []):
            if rule.get("type") == "expense_limit" and rule.get("category") == "hardware":
                limit = float(rule.get("max_amount", 5000.0))
                if total > limit:
                    audit_results["issues"].append({
                        "type": "policy_violation",
                        "description": f"Invoice total (${total:.2f}) exceeds the hardware expense limit (${limit:.2f})",
                        "severity": "high"
                    })
    
    logger.info(f"Agent integration test complete. Found {len(audit_results['issues'])} issues.")
    
    return audit_results

def main():
    """Test the integration of OCR and agent components."""
    # Path to the sample files
    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    policy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "policies")
    
    # Find sample files
    pdf_file = os.path.join(samples_dir, "sample_invoice.pdf")
    png_file = os.path.join(samples_dir, "sample_invoice.png")
    policy_file = os.path.join(policy_dir, "acme_corporation.json")
    
    # Ensure sample files exist
    if not os.path.exists(pdf_file):
        logger.warning(f"PDF sample file not found: {pdf_file}")
    
    if not os.path.exists(png_file):
        logger.warning(f"PNG sample file not found: {png_file}")
    
    if not os.path.exists(policy_file):
        logger.warning(f"Policy file not found: {policy_file}")
    
    # Test with PNG file
    if os.path.exists(png_file):
        logger.info("\n=== Testing OCR with PNG file ===")
        png_ocr_data, png_invoice = test_ocr_integration(png_file)
        
        if os.path.exists(policy_file):
            logger.info("\n=== Testing Agent integration with PNG OCR data ===")
            png_audit_results = test_agent_integration(png_ocr_data, policy_file)
            
            if png_audit_results:
                logger.info("\nAudit Results:")
                logger.info(f"Invoice ID: {png_audit_results['invoice_id']}")
                logger.info(f"Vendor: {png_audit_results['vendor']}")
                logger.info(f"Total: ${float(png_audit_results['total']):.2f}")
                
                if png_audit_results['issues']:
                    logger.info(f"\nFound {len(png_audit_results['issues'])} issues:")
                    for issue in png_audit_results['issues']:
                        logger.info(f"- {issue['description']} (Severity: {issue['severity']})")
                else:
                    logger.info("\nNo issues found.")
                
                logger.info(f"\nSummary: {png_audit_results['summary']}")
    
    # Test with PDF file
    if os.path.exists(pdf_file):
        logger.info("\n=== Testing OCR with PDF file ===")
        pdf_ocr_data, pdf_invoice = test_ocr_integration(pdf_file)
        
        if os.path.exists(policy_file):
            logger.info("\n=== Testing Agent integration with PDF OCR data ===")
            pdf_audit_results = test_agent_integration(pdf_ocr_data, policy_file)
            
            if pdf_audit_results:
                logger.info("\nAudit Results:")
                logger.info(f"Invoice ID: {pdf_audit_results['invoice_id']}")
                logger.info(f"Vendor: {pdf_audit_results['vendor']}")
                logger.info(f"Total: ${float(pdf_audit_results['total']):.2f}")
                
                if pdf_audit_results['issues']:
                    logger.info(f"\nFound {len(pdf_audit_results['issues'])} issues:")
                    for issue in pdf_audit_results['issues']:
                        logger.info(f"- {issue['description']} (Severity: {issue['severity']})")
                else:
                    logger.info("\nNo issues found.")
                
                logger.info(f"\nSummary: {pdf_audit_results['summary']}")

if __name__ == "__main__":
    main() 