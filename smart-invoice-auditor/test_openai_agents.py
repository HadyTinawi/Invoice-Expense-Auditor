#!/usr/bin/env python3
"""
Test script for OpenAI Agents implementation

This script tests the OpenAI Agents implementation by loading sample data
and running an audit with the agent.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project directory to the path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the OpenAI Agents implementation
from src.agent.openai_agents.adapter import AuditWorkflow

def load_sample_data():
    """Load sample invoice and policy data for testing"""
    try:
        # Load sample invoice data
        sample_invoice_path = os.path.join(project_dir, "data", "samples", "sample_invoice.json")
        with open(sample_invoice_path, 'r') as f:
            invoice_data = json.load(f)
        
        # Load sample policy data
        sample_policy_path = os.path.join(project_dir, "data", "policies", "default_policy.json")
        with open(sample_policy_path, 'r') as f:
            policy_data = json.load(f)
        
        return invoice_data, policy_data
    except FileNotFoundError as e:
        logger.error(f"Sample data not found: {e}")
        # Create minimal sample data
        invoice_data = {
            "invoice_id": "INV12345",
            "vendor": {"name": "Test Vendor"},
            "issue_date": datetime.now().isoformat(),
            "due_date": None,
            "total": 100.0,
            "subtotal": 90.0,
            "tax": 10.0,
            "line_items": [
                {"description": "Test Item", "quantity": 1, "unit_price": 90.0, "amount": 90.0}
            ]
        }
        
        policy_data = {
            "vendor": "Default",
            "expense_limits": {"general": 1000},
            "allowed_categories": ["general"],
            "excluded_items": []
        }
        
        return invoice_data, policy_data

def run_agent_test():
    """Run a test of the OpenAI Agents implementation"""
    logger.info("Testing OpenAI Agents implementation...")
    
    # Check if OpenAI API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set. Please set it in .env file.")
        return False
    
    # Load sample data
    invoice_data, policy_data = load_sample_data()
    
    # Configure the agent
    agent_config = {
        "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "temperature": 0.0,
        "verbose": True
    }
    
    try:
        # Initialize the workflow
        logger.info("Initializing OpenAI Agents workflow...")
        workflow = AuditWorkflow(config=agent_config)
        
        # Run the audit
        logger.info("Running invoice audit...")
        result = workflow.run_audit(invoice_data, policy_data)
        
        # Check for a valid result
        if not isinstance(result, dict):
            logger.error(f"Expected dict result, got {type(result)}")
            return False
        
        # Check for required keys in the result
        required_keys = ["invoice_id", "issues", "completed_at"]
        missing_keys = [key for key in required_keys if key not in result]
        
        if missing_keys:
            logger.error(f"Missing required keys in result: {missing_keys}")
            return False
        
        # Display audit results
        logger.info(f"Audit completed successfully!")
        logger.info(f"Invoice ID: {result.get('invoice_id')}")
        logger.info(f"Issues found: {len(result.get('issues', []))}")
        
        # Display issues
        for i, issue in enumerate(result.get("issues", []), 1):
            logger.info(f"Issue {i}: {issue.get('type')} - {issue.get('severity', 'medium')} priority")
            logger.info(f"Description: {issue.get('description')}")
            logger.info("-" * 40)
        
        logger.info(f"Summary: {result.get('summary', 'No summary available')}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing OpenAI Agents: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_agent_test()
    if success:
        logger.info("✅ OpenAI Agents test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ OpenAI Agents test failed!")
        sys.exit(1) 