"""
Adapter for OpenAI Agents

This module provides an adapter that makes the OpenAI Agents implementation
compatible with the existing audit workflow interface.
"""

import logging
import json
import traceback
from typing import Dict, Any, Optional

from .agent import InvoiceAuditorAgent

logger = logging.getLogger(__name__)

# Add a module-level logger message to track when this module is imported
logger.info("OpenAI Agents adapter module imported successfully")

class AuditWorkflow:
    """
    Adapter class that provides the same interface as the LangGraph workflow but uses
    OpenAI Agents under the hood.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter with configuration
        
        Args:
            config: Configuration options
        """
        logger.info("Initializing OpenAI Agents adapter with config: %s", json.dumps(config or {}, default=str))
        
        try:
            self.config = config or {}
            self.agent = InvoiceAuditorAgent(config)
            logger.info("OpenAI Agents adapter initialized successfully with model: %s", 
                       self.config.get("model_name", "default"))
        except Exception as e:
            logger.error("Error initializing OpenAI Agents adapter: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise
    
    def run_audit(self, invoice_data: Dict[str, Any], policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the audit using the OpenAI Agents implementation
        
        Args:
            invoice_data: The invoice data to audit
            policy_data: The policy data to check against
            
        Returns:
            Audit results including any issues found
        """
        invoice_id = invoice_data.get("invoice_id", "UNKNOWN")
        vendor = invoice_data.get("vendor", {}).get("name", invoice_data.get("vendor", "UNKNOWN"))
        
        logger.info(f"OpenAI Agents adapter running audit for invoice {invoice_id} from {vendor}")
        
        try:
            result = self.agent.audit_invoice(invoice_data, policy_data)
            logger.info(f"OpenAI Agents adapter completed audit with {len(result.get('issues', []))} issues")
            return result
        except Exception as e:
            logger.error(f"Error in OpenAI Agents adapter audit: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise 