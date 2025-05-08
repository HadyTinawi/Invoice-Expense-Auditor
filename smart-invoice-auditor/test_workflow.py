#!/usr/bin/env python3
"""
Test the AuditWorkflow functionality directly
"""

import os
import json
import logging
from dotenv import load_dotenv
from src.agent.workflow import AuditWorkflow
from src.ocr.processor import create_processor
from src.models.utils import ocr_data_to_invoice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_workflow_initialization():
    """Test that the workflow can be initialized without errors"""
    logger.info("Testing workflow initialization...")
    
    try:
        # Initialize workflow with minimal config
        workflow = AuditWorkflow(config={"verbose": True})
        logger.info("✅ Workflow initialized successfully!")
        return workflow
    except Exception as e:
        logger.error(f"❌ Workflow initialization failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def test_workflow_execution(workflow):
    """Test that the workflow can be run with sample data"""
    if not workflow:
        logger.error("Cannot test execution - workflow initialization failed")
        return
    
    logger.info("Testing workflow execution...")
    
    # Create sample invoice data
    sample_invoice = {
        "invoice_id": "TEST-123",
        "vendor": "Test Vendor",
        "date": "2025-05-07",
        "due_date": "2025-06-07",
        "total": 1500.00,
        "subtotal": 1400.00,
        "tax": 100.00,
        "line_items": [
            {
                "description": "Test Item 1",
                "quantity": 2,
                "unit_price": 500.00,
                "amount": 1000.00,
                "category": "office_supplies"
            },
            {
                "description": "Test Item 2",
                "quantity": 1,
                "unit_price": 400.00,
                "amount": 400.00,
                "category": "software"
            }
        ]
    }
    
    # Load sample policy data
    try:
        policy_path = os.path.join("data", "policies", "acme_corporation.json")
        with open(policy_path, "r") as f:
            policy_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load policy data: {str(e)}")
        policy_data = {
            "vendor": "Test Policy",
            "rules": [
                {
                    "type": "expense_limit",
                    "category": "office_supplies",
                    "max_amount": 500.00,
                    "description": "Office supplies expenses should not exceed $500 per invoice"
                }
            ]
        }
    
    # Run the workflow
    try:
        logger.info("Running workflow...")
        result = workflow.run_audit(sample_invoice, policy_data)
        logger.info("✅ Workflow executed successfully!")
        logger.info(f"Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        logger.error(f"❌ Workflow execution failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def test_with_sample_file():
    """Test the workflow with a real sample file"""
    logger.info("Testing workflow with sample file...")
    
    # Initialize workflow
    workflow = AuditWorkflow(config={"verbose": True})
    
    # Process a sample file with OCR
    try:
        sample_path = os.path.join("samples", "sample_invoice.png")
        if not os.path.exists(sample_path):
            logger.error(f"Sample file not found: {sample_path}")
            return
        
        processor = create_processor("tesseract")
        ocr_data = processor.process_file(sample_path)
        
        # Create invoice object
        invoice = ocr_data_to_invoice(ocr_data, sample_path)
        logger.info(f"Extracted invoice data: ID={invoice.invoice_id}, Vendor={invoice.vendor.name}, Total=${invoice.total:.2f}")
        
        # Convert to dict for the workflow
        invoice_data = invoice.to_dict()
        
        # Load policy data
        policy_path = os.path.join("data", "policies", "acme_corporation.json")
        with open(policy_path, "r") as f:
            policy_data = json.load(f)
        
        # Run the workflow
        logger.info("Running workflow with OCR data...")
        result = workflow.run_audit(invoice_data, policy_data)
        logger.info("✅ Workflow executed successfully with OCR data!")
        logger.info(f"Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        logger.error(f"❌ Workflow execution with OCR data failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting workflow tests...")
    
    # Test workflow initialization
    workflow = test_workflow_initialization()
    
    # Test workflow execution with sample data
    test_workflow_execution(workflow)
    
    # Test with sample file
    test_with_sample_file()
    
    logger.info("Tests completed.") 