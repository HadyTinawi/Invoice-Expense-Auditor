"""
OpenAI Agents-based Invoice Auditor

This module implements the invoice auditing using the OpenAI Agents SDK.
"""

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from agents import Agent, Runner
from agents.tool import function_tool

# Local imports
from ..tools import AuditorTools
from src.policy import PolicyManager

logger = logging.getLogger(__name__)

# Add a module-level logger message to track when this module is imported
logger.info("OpenAI Agents-based Invoice Auditor module imported successfully")

class InvoiceAuditorAgent:
    """Invoice auditor implemented using OpenAI Agents SDK"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the invoice auditor
        
        Args:
            config: Configuration options for the auditor
        """
        logger.info("Initializing OpenAI Agents-based Invoice Auditor with config: %s", 
                   json.dumps(config or {}, default=str))
        
        try:
            self.config = config or {}
            self.model_name = self.config.get("model_name", "gpt-4o")
            self.verbose = self.config.get("verbose", False)
            self.debug_api = self.config.get("debug_api", False)
            self.api_key = self.config.get("api_key", os.environ.get("OPENAI_API_KEY"))
            
            # Initialize tools
            self.tools_instance = AuditorTools()
            self.policy_manager = PolicyManager()
            
            # Create the agent
            logger.info("Creating OpenAI Agent with model: %s", self.model_name)
            self.agent = self._create_agent()
            
            logger.info("OpenAI Agents-based Invoice Auditor initialized successfully")
            
            # Check if we're using OpenRouter API
            if self.api_key and self.api_key.startswith("sk-proj-"):
                logger.info("Using OpenRouter API for OpenAI Agents")
        except Exception as e:
            logger.error("Error initializing OpenAI Agents-based Invoice Auditor: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise
    
    def _create_agent(self) -> Agent:
        """Create the OpenAI Agent for invoice auditing"""
        logger.info("Creating function tools for OpenAI Agent")
        
        try:
            # Define the tools here
            
            # Set up OpenAI environment variables
            logger.info("Setting OPENAI_API_KEY environment variable")
            os.environ["OPENAI_API_KEY"] = self.api_key
            
            # Check if it's OpenRouter API and set appropriate API base
            if self.api_key and self.api_key.startswith("sk-proj-"):
                logger.info("Setting OPENAI_BASE_URL to OpenRouter API")
                os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
            
            # Create functions WITHOUT using Pydantic models
            
            @function_tool
            def check_duplicate(invoice_id: str, vendor: str, amount: float, date: str) -> Dict[str, Any]:
                """
                Check if an invoice is a duplicate based on ID, vendor, amount, and date.
                
                Args:
                    invoice_id: The invoice ID to check
                    vendor: The vendor name
                    amount: The invoice total amount
                    date: The invoice date in YYYY-MM-DD format
                    
                Returns:
                    A dictionary with duplicate check results.
                """
                return self.tools_instance.check_duplicate(invoice_id, vendor, amount, date)
            
            @function_tool
            def check_policy_compliance(expense_category: str, amount: float, policy_data: Dict[str, Any]) -> Dict[str, Any]:
                """
                Check if an expense complies with policy.
                
                Args:
                    expense_category: The expense category
                    amount: The expense amount
                    policy_data: Dictionary with policy rules
                    
                Returns:
                    A dictionary with compliance check results.
                """
                return self.tools_instance.check_policy_compliance(expense_category, amount, policy_data)
            
            @function_tool
            def verify_calculations(subtotal: float, tax: float, total: float, line_items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
                """
                Verify that invoice calculations are correct.
                
                Args:
                    subtotal: The invoice subtotal
                    tax: The invoice tax amount
                    total: The invoice total
                    line_items: Optional list of line items
                    
                Returns:
                    A dictionary with calculation verification results.
                """
                return self.tools_instance.verify_calculations(subtotal, tax, total, line_items)
            
            @function_tool
            def check_date_validity(invoice_date: str) -> Dict[str, Any]:
                """
                Check if an invoice date is valid.
                
                Args:
                    invoice_date: The invoice date in YYYY-MM-DD format
                    
                Returns:
                    A dictionary with date validity check results.
                """
                return self.tools_instance.check_date_validity(invoice_date)
            
            @function_tool
            def extract_vendor_info(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
                """
                Extract and analyze vendor information from the invoice.
                
                Args:
                    invoice_data: The invoice data as a dictionary
                    
                Returns:
                    A dictionary with vendor information analysis.
                """
                return self.tools_instance.extract_vendor_info(invoice_data)
            
            @function_tool
            def analyze_line_items(line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
                """
                Analyze line items for anomalies or patterns.
                
                Args:
                    line_items: List of line item dictionaries
                    
                Returns:
                    A dictionary with line item analysis results.
                """
                return self.tools_instance.analyze_line_items(line_items)
            
            # Create the agent with instructions and tools
            logger.info("Creating OpenAI Agent with %d tools", 6)
            agent = Agent(
                name="Invoice Auditor",
                instructions="""You are an Invoice Auditing Assistant designed to analyze invoice data and detect issues.
                Your job is to carefully examine invoices for:
                1. Duplicate invoices (same invoice ID, vendor, or very similar amounts and dates)
                2. Policy violations (charges that exceed allowed limits or unauthorized expense categories)
                3. Calculation errors (incorrect subtotals, tax calculations, or totals)
                4. Date inconsistencies (future dates, unreasonably old dates)
                5. Vendor information irregularities
                6. Line item anomalies
                
                For each issue found, provide:
                - A clear description of the problem
                - The severity (low, medium, high)
                - A recommendation for resolution
                
                Always analyze all aspects of the invoice thoroughly and report all issues found.
                """,
                tools=[
                    check_duplicate,
                    check_policy_compliance,
                    verify_calculations,
                    check_date_validity,
                    extract_vendor_info,
                    analyze_line_items
                ],
                model=self.model_name
            )
            
            logger.info("OpenAI Agent created successfully")
            return agent
        except Exception as e:
            logger.error("Error creating OpenAI Agent: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise
    
    def audit_invoice(self, invoice_data: Dict[str, Any], policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audit an invoice using the OpenAI Agent
        
        Args:
            invoice_data: The invoice data to audit
            policy_data: The policy data to check against
            
        Returns:
            Audit results including any issues found
        """
        invoice_id = invoice_data.get("invoice_id", "UNKNOWN")
        vendor = invoice_data.get("vendor", {}).get("name", invoice_data.get("vendor", "UNKNOWN"))
        
        logger.info(f"Starting audit for invoice {invoice_id} from {vendor} with OpenAI Agents")
        
        try:
            # Prepare the invoice and policy data as JSON strings
            invoice_json = json.dumps(invoice_data, indent=2, default=str)
            policy_json = json.dumps(policy_data, indent=2, default=str)
            
            # Create the prompt for the agent
            prompt = f"""
            Please audit the following invoice against the provided policy:
            
            INVOICE DATA:
            {invoice_json}
            
            POLICY DATA:
            {policy_json}
            
            Analyze the invoice thoroughly for duplicates, policy violations, calculation errors, 
            date issues, vendor irregularities, and line item anomalies.
            
            Return a comprehensive analysis with all issues found.
            """
            
            # Run the agent
            logger.info(f"Invoking OpenAI Agent Runner for invoice {invoice_id}")
            
            try:
                # Log environment variables without sensitive data
                env_vars = {k: v[:4] + "..." + v[-4:] if k == "OPENAI_API_KEY" and len(v) > 8 else v 
                           for k, v in os.environ.items() if k.startswith("OPENAI_")}
                logger.info(f"OpenAI environment variables: {json.dumps(env_vars)}")
                
                # Run the agent
                result = Runner.run_sync(self.agent, prompt)
                logger.info(f"OpenAI Agent Runner completed for invoice {invoice_id}")
                logger.info(f"Final output length: {len(result.final_output)}")
            except Exception as e:
                logger.error(f"Error running OpenAI Agent: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            # Extract issues from the agent's response
            logger.info(f"Extracting issues from OpenAI Agent response")
            issues = self._extract_issues_from_response(result.final_output, invoice_data)
            logger.info(f"Extracted {len(issues)} issues from response")
            
            # Generate summary
            summary = self._generate_summary(invoice_data, issues)
            
            # Create the audit result
            audit_result = {
                "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
                "vendor": invoice_data.get("vendor", {}).get("name", invoice_data.get("vendor", "UNKNOWN")),
                "total": invoice_data.get("total", 0.0),
                "issues_found": len(issues) > 0,
                "issues": issues,
                "summary": summary,
                "completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Completed audit for invoice {invoice_id} with {len(issues)} issues found")
            return audit_result
            
        except Exception as e:
            logger.error(f"Error during invoice audit: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return error result
            return {
                "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
                "vendor": invoice_data.get("vendor", {}).get("name", invoice_data.get("vendor", "UNKNOWN")),
                "total": invoice_data.get("total", 0.0),
                "issues_found": True,
                "issues": [{
                    "type": "Audit Error",
                    "description": f"Error during audit: {str(e)}",
                    "severity": "high",
                    "source": "audit_error"
                }],
                "summary": f"Audit failed with error: {str(e)}",
                "completed_at": datetime.now().isoformat()
            }
    
    def _extract_issues_from_response(self, response: str, invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract issues from the agent response
        
        Args:
            response: The agent response text
            invoice_data: The original invoice data
            
        Returns:
            List of issues extracted from the response
        """
        issues = []
        
        # Simple parsing logic - look for patterns that indicate issues
        # This could be enhanced with more sophisticated parsing
        lines = response.split("\n")
        current_issue = None
        
        for line in lines:
            line = line.strip()
            
            # Look for issue markers
            if "Issue:" in line or "Problem:" in line or "Error:" in line:
                if current_issue:
                    issues.append(current_issue)
                
                # Start a new issue
                current_issue = {
                    "type": "Generic Issue",
                    "description": line.split(":", 1)[1].strip(),
                    "severity": "medium"
                }
            
            # Look for severity indicators
            elif current_issue and ("Severity:" in line or "Priority:" in line):
                severity_text = line.split(":", 1)[1].strip().lower()
                if "high" in severity_text:
                    current_issue["severity"] = "high"
                elif "low" in severity_text:
                    current_issue["severity"] = "low"
                else:
                    current_issue["severity"] = "medium"
            
            # Look for issue types
            elif current_issue and ("Type:" in line):
                current_issue["type"] = line.split(":", 1)[1].strip()
            
            # Add additional description if seems to be continuing the issue
            elif current_issue and line and not line.startswith(("#", "-", "*")) and ":" not in line:
                current_issue["description"] += " " + line
        
        # Add the last issue if exists
        if current_issue:
            issues.append(current_issue)
        
        # If we couldn't parse issues but there's text, create a generic issue
        if not issues and response.strip():
            issues.append({
                "type": "Analysis Result",
                "description": response.strip(),
                "severity": "medium"
            })
        
        return issues
    
    def _generate_summary(self, invoice_data: Dict[str, Any], issues: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the audit results
        
        Args:
            invoice_data: The invoice data
            issues: List of issues found
            
        Returns:
            Summary text
        """
        # Count issues by severity
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.get("severity", "medium").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        if not issues:
            summary = f"No issues found in invoice {invoice_data.get('invoice_id', 'UNKNOWN')}."
        else:
            summary = f"Found {len(issues)} issues in invoice {invoice_data.get('invoice_id', 'UNKNOWN')} "
            summary += f"({severity_counts['high']} high, {severity_counts['medium']} medium, {severity_counts['low']} low priority). "
            
            # Add recommendations based on severity
            if severity_counts["high"] > 0:
                summary += "Recommend immediate review due to high-priority issues. "
            elif severity_counts["medium"] > 0:
                summary += "Recommend review at earliest convenience. "
            else:
                summary += "Minor issues detected, review when possible. "
        
        return summary 