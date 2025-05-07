"""
Auditor Agent Module

This module implements the agent-based logic for auditing invoices,
detecting errors, duplicates, and policy violations using LangChain.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
import pandas as pd

# LangChain imports
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOpenAI as LegacyChatOpenAI

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Sequence

# Local imports
from src.policy import PolicyManager, PolicyRule, PolicyViolation


# Define the state schema for the audit graph
class AuditState(TypedDict):
    """State for the audit workflow"""
    invoice_data: Dict[str, Any]
    policy_data: Dict[str, Any]
    issues: List[Dict[str, Any]]
    history: List[Union[HumanMessage, AIMessage]]
    next_steps: List[str]
    complete: bool


class AuditorAgent:
    """Agent for auditing invoices and detecting issues"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the auditor agent with configuration"""
        self.config = config or {}
        self.invoice_history = {}  # Store invoice history for duplicate detection
        self.llm = self._get_llm()
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.tools = self._create_tools()
        self.agent_executor = self._setup_agent()
        self.policy_manager = PolicyManager()
    
    def _get_llm(self) -> BaseChatModel:
        """Get the language model based on configuration"""
        model_name = self.config.get("model_name", "gpt-4o")
        temperature = self.config.get("temperature", 0.0)
        
        try:
            # Try to use the newer ChatOpenAI class
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        except ImportError:
            # Fall back to legacy ChatOpenAI if needed
            return LegacyChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                openai_api_key=os.environ.get("OPENAI_API_KEY")
            )
    
    def _create_tools(self) -> List[BaseTool]:
        """Create tools for the agent to use"""
        tools = [
            # Tool for checking if an invoice is a duplicate
            StructuredTool.from_function(
                func=self._tool_check_duplicate,
                name="check_duplicate_invoice",
                description="Check if an invoice is a duplicate based on invoice ID, vendor, and amount"
            ),
            
            # Tool for checking policy compliance
            StructuredTool.from_function(
                func=self._tool_check_policy_compliance,
                name="check_policy_compliance",
                description="Check if invoice items comply with vendor policies"
            ),
            
            # Tool for verifying calculations
            StructuredTool.from_function(
                func=self._tool_verify_calculations,
                name="verify_calculations",
                description="Verify that invoice calculations (subtotal, tax, total) are correct"
            ),
            
            # Tool for checking date validity
            StructuredTool.from_function(
                func=self._tool_check_date_validity,
                name="check_date_validity",
                description="Check if invoice dates are valid and within acceptable ranges"
            ),
            
            # Tool for generating a hash of invoice data
            StructuredTool.from_function(
                func=self._tool_generate_invoice_hash,
                name="generate_invoice_hash",
                description="Generate a unique hash for an invoice to aid in duplicate detection"
            )
        ]
        return tools
    
    def _setup_agent(self) -> AgentExecutor:
        """Set up the LangChain agent"""
        # Define the system prompt
        system_prompt = """You are an Invoice Auditing Assistant designed to analyze invoice data and detect issues.
        Your job is to carefully examine invoices for:
        1. Duplicate invoices (same invoice ID, vendor, or very similar amounts and dates)
        2. Policy violations (charges that exceed allowed limits or unauthorized expense categories)
        3. Calculation errors (incorrect subtotals, tax calculations, or totals)
        4. Date inconsistencies (future dates, unreasonably old dates)
        
        For each issue found, provide:
        - A clear description of the problem
        - The severity (low, medium, high)
        - A recommendation for resolution
        
        Be thorough in your analysis and use the provided tools to check various aspects of the invoice.
        """
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        
        # Create the agent executor
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.config.get("verbose", False),
            handle_parsing_errors=True
        )
    
    def audit_invoice(self, invoice_data: Dict[str, Any], policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audit an invoice against policy data
        
        Args:
            invoice_data: Extracted invoice data from OCR
            policy_data: Policy data for compliance checking
            
        Returns:
            Audit results with detected issues
        """
        # Store invoice data in history for duplicate detection in future runs
        invoice_id = invoice_data.get("invoice_id", "UNKNOWN")
        if invoice_id != "UNKNOWN":
            self.invoice_history[invoice_id] = invoice_data
        
        # Perform rule-based checks first
        duplicate_issues = self._check_for_duplicates(invoice_data)
        policy_issues = self._check_policy_compliance(invoice_data, policy_data)
        calculation_issues = self._check_calculations(invoice_data)
        
        # Combine rule-based issues
        rule_based_issues = duplicate_issues + policy_issues + calculation_issues
        
        # Use the agent for more complex analysis if configured to do so
        if self.config.get("use_agent_analysis", True):
            # Prepare input for the agent
            agent_input = {
                "input": f"""Please analyze this invoice data and identify any issues:
                Invoice Data: {json.dumps(invoice_data, indent=2)}
                Policy Data: {json.dumps(policy_data, indent=2)}
                
                Issues already identified through rule-based checks:
                {json.dumps(rule_based_issues, indent=2) if rule_based_issues else "None"}
                
                Please identify any additional issues or provide more insights on the existing issues.
                """
            }
            
            # Run the agent
            agent_result = self.agent_executor.invoke(agent_input)
            agent_output = agent_result.get("output", "")
            
            # Extract additional issues identified by the agent
            # This is a simple approach - in a production system, you might want to
            # parse the agent's output more carefully
            agent_issues = []
            if "additional issues" in agent_output.lower() or "new issue" in agent_output.lower():
                agent_issues = [{
                    "type": "AI-Detected Issue",
                    "description": agent_output,
                    "severity": "medium",
                    "source": "agent_analysis"
                }]
            
            # Combine all issues
            all_issues = rule_based_issues + agent_issues
        else:
            all_issues = rule_based_issues
        
        return {
            "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
            "vendor": invoice_data.get("vendor", "UNKNOWN"),
            "total": invoice_data.get("total", 0.0),
            "issues_found": len(all_issues) > 0,
            "issues": all_issues,
            "summary": self._generate_summary(invoice_data, all_issues)
        }
    
    def _check_for_duplicates(self, invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for duplicate invoices using rule-based approach"""
        issues = []
        invoice_id = invoice_data.get("invoice_id", "UNKNOWN")
        
        # Skip check if invoice ID is unknown
        if invoice_id == "UNKNOWN":
            return []
        
        # Check if we've seen this invoice ID before (excluding the current one)
        for stored_id, stored_invoice in self.invoice_history.items():
            if stored_id == invoice_id and stored_invoice != invoice_data:
                issues.append({
                    "type": "Duplicate Invoice ID",
                    "description": f"Invoice ID {invoice_id} has been used before with different details",
                    "severity": "high",
                    "source": "rule_based"
                })
                break
        
        # Check for similar invoices (same vendor, close amount, close date)
        vendor = invoice_data.get("vendor", "UNKNOWN")
        total = invoice_data.get("total", 0.0)
        date = invoice_data.get("date", "UNKNOWN")
        
        for stored_id, stored_invoice in self.invoice_history.items():
            if stored_id != invoice_id and stored_invoice.get("vendor") == vendor:
                stored_total = stored_invoice.get("total", 0.0)
                stored_date = stored_invoice.get("date", "UNKNOWN")
                
                # Check if amount is very similar (within 1%)
                if abs(stored_total - total) / max(stored_total, total, 1.0) < 0.01:
                    # If date is also close or the same, flag as potential duplicate
                    if stored_date == date:
                        issues.append({
                            "type": "Potential Duplicate Invoice",
                            "description": f"Very similar to invoice {stored_id} (same vendor, amount, and date)",
                            "severity": "high",
                            "source": "rule_based"
                        })
                        break
        
        return issues
    
    def _check_policy_compliance(self, invoice_data: Dict[str, Any], policy_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for policy compliance issues using enhanced policy manager"""
        issues = []
        
        # Skip if no policy data
        if not policy_data:
            return []
        
        # Get vendor name
        vendor_name = invoice_data.get("vendor", "UNKNOWN")
        
        # Use the policy manager to check compliance
        compliance_result = self.policy_manager.check_invoice_compliance(invoice_data, vendor_name)
        
        # Convert policy violations to issues
        if not compliance_result["compliant"]:
            for violation in compliance_result["violations"]:
                issues.append({
                    "type": f"Policy Violation: {violation['rule_id']}",
                    "description": violation["description"],
                    "severity": violation["severity"],
                    "source": "policy_manager"
                })
        
        return issues
    
    def _check_calculations(self, invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for calculation errors in the invoice using rule-based approach"""
        issues = []
        
        # Check if subtotal + tax = total
        subtotal = invoice_data.get("subtotal", 0.0)
        tax = invoice_data.get("tax", 0.0)
        total = invoice_data.get("total", 0.0)
        
        # Only check if we have all three values
        if subtotal > 0 and total > 0:
            expected_total = subtotal + tax
            # Allow for small rounding differences (1 cent)
            if abs(expected_total - total) > 0.01:
                issues.append({
                    "type": "Calculation Error",
                    "description": f"Invoice total (${total:.2f}) doesn't match subtotal (${subtotal:.2f}) + tax (${tax:.2f}) = ${expected_total:.2f}",
                    "severity": "medium",
                    "source": "rule_based"
                })
        
        # Check line items sum to subtotal
        line_items = invoice_data.get("line_items", [])
        if line_items and subtotal > 0:
            line_sum = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in line_items)
            # Allow for small rounding differences (1 cent)
            if abs(line_sum - subtotal) > 0.01:
                issues.append({
                    "type": "Line Item Sum Error",
                    "description": f"Line items sum (${line_sum:.2f}) doesn't match invoice subtotal (${subtotal:.2f})",
                    "severity": "medium",
                    "source": "rule_based"
                })
        
        return issues
    
    def _generate_summary(self, invoice_data: Dict[str, Any], issues: List[Dict[str, Any]]) -> str:
        """Generate a summary of the audit results"""
        if not issues:
            return f"No issues found in invoice {invoice_data.get('invoice_id', 'UNKNOWN')}."
        
        # Count issues by severity
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.get("severity", "medium").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
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
    
    # Tool implementations
    def _tool_check_duplicate(self, invoice_id: str, vendor: str, amount: float, date: str) -> str:
        """Tool for checking if an invoice is a duplicate"""
        for stored_id, stored_invoice in self.invoice_history.items():
            if stored_id == invoice_id:
                return f"DUPLICATE FOUND: Invoice ID {invoice_id} already exists in the system."
            
            if (stored_invoice.get("vendor") == vendor and 
                abs(stored_invoice.get("total", 0.0) - amount) < 0.01 and
                stored_invoice.get("date") == date):
                return f"POTENTIAL DUPLICATE: Very similar to invoice {stored_id} with same vendor, amount, and date."
        
        return "No duplicates found."
    
    def _tool_check_policy_compliance(self, expense_category: str, amount: float, policy_data: Dict[str, Any]) -> str:
        """Tool for checking if an expense complies with policy"""
        # Create a simplified invoice for checking
        invoice_data = {
            "invoice_id": "TOOL-CHECK",
            "vendor": "TOOL-VENDOR",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total": amount,
            "line_items": [
                {
                    "description": "Item being checked",
                    "category": expense_category,
                    "quantity": 1,
                    "price": amount
                }
            ]
        }
        
        # Create temporary policy rules
        rules = []
        
        # Rule for allowed categories
        if "allowed_categories" in policy_data:
            rules.append(PolicyRule(
                rule_id="check_allowed_categories",
                rule_type="allowed_categories",
                parameters={"allowed_categories": policy_data["allowed_categories"]},
                description="Allowed expense categories",
                severity="medium"
            ))
        
        # Rule for max item prices
        if "max_item_prices" in policy_data:
            rules.append(PolicyRule(
                rule_id="check_max_item_price",
                rule_type="max_item_price",
                parameters={"max_item_prices": policy_data["max_item_prices"]},
                description="Maximum prices by category",
                severity="medium"
            ))
        
        # Check each rule
        for rule in rules:
            violation = rule.check(invoice_data)
            if violation:
                return f"POLICY VIOLATION: {violation.description}"
        
        return f"Expense complies with policy for category '{expense_category}' and amount ${amount:.2f}"
    
    def _tool_verify_calculations(self, subtotal: float, tax: float, total: float, line_items: List[Dict[str, Any]]) -> str:
        """Tool for verifying invoice calculations"""
        issues = []
        
        # Check if subtotal + tax = total
        expected_total = subtotal + tax
        if abs(expected_total - total) > 0.01:
            issues.append(f"Total (${total:.2f}) doesn't match subtotal (${subtotal:.2f}) + tax (${tax:.2f}) = ${expected_total:.2f}")
        
        # Check if line items sum to subtotal
        if line_items:
            line_sum = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in line_items)
            if abs(line_sum - subtotal) > 0.01:
                issues.append(f"Line items sum (${line_sum:.2f}) doesn't match subtotal (${subtotal:.2f})")
        
        if issues:
            return "CALCULATION ERRORS FOUND:\n" + "\n".join(issues)
        
        return "All calculations verified: subtotal, tax, total, and line items are consistent."
    
    def _tool_check_date_validity(self, invoice_date: str) -> str:
        """Tool for checking if invoice dates are valid"""
        try:
            # Try to parse the date
            date_format = "%Y-%m-%d"
            invoice_date_obj = datetime.strptime(invoice_date, date_format)
            
            # Check if date is in the future
            if invoice_date_obj > datetime.now():
                return f"INVALID DATE: Invoice date {invoice_date} is in the future."
            
            # Check if date is too old (more than 1 year)
            one_year_ago = datetime.now().replace(year=datetime.now().year - 1)
            if invoice_date_obj < one_year_ago:
                return f"SUSPICIOUS DATE: Invoice date {invoice_date} is more than one year old."
            
            return f"Date {invoice_date} is valid."
        except ValueError:
            return f"INVALID DATE FORMAT: Could not parse date '{invoice_date}'. Expected format is YYYY-MM-DD."
    
    def _tool_generate_invoice_hash(self, invoice_data: Dict[str, Any]) -> str:
        """Tool for generating a unique hash for an invoice"""
        # Create a string representation of key invoice data
        hash_input = f"{invoice_data.get('invoice_id', '')}-{invoice_data.get('vendor', '')}-{invoice_data.get('total', 0.0)}-{invoice_data.get('date', '')}"
        
        # Generate hash
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        return f"Invoice hash: {hash_value}"


class AuditGraph:
    """LangGraph implementation for more complex audit workflows"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the audit graph"""
        self.config = config or {}
        self.llm = self._get_llm()
        self.tools = self._create_tools()
        self.graph = self._build_graph()
    
    def _get_llm(self) -> BaseChatModel:
        """Get the language model based on configuration"""
        model_name = self.config.get("model_name", "gpt-4o")
        temperature = self.config.get("temperature", 0.0)
        
        try:
            # Try to use the newer ChatOpenAI class
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        except ImportError:
            # Fall back to legacy ChatOpenAI if needed
            return LegacyChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                openai_api_key=os.environ.get("OPENAI_API_KEY")
            )
    
    def _create_tools(self) -> List[Callable]:
        """Create tools for the audit workflow"""
        @tool
        def check_duplicate(invoice_id: str, vendor: str, amount: float) -> str:
            """Check if an invoice is a duplicate based on ID, vendor, and amount"""
            # Implementation would check against a database or history
            return "No duplicates found."
        
        @tool
        def check_policy_compliance(expense_category: str, amount: float, policy_data: Dict[str, Any]) -> str:
            """Check if an expense complies with policy"""
            # Implementation would check against policy rules
            return "Expense complies with policy."
        
        @tool
        def verify_calculations(subtotal: float, tax: float, total: float) -> str:
            """Verify that invoice calculations are correct"""
            expected_total = subtotal + tax
            if abs(expected_total - total) > 0.01:
                return f"Error: Total (${total:.2f}) doesn't match subtotal (${subtotal:.2f}) + tax (${tax:.2f}) = ${expected_total:.2f}"
            return "Calculations are correct."
        
        return [check_duplicate, check_policy_compliance, verify_calculations]
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create the graph
        workflow = StateGraph(AuditState)
        
        # Define nodes
        
        # 1. Initial analysis node
        def initial_analysis(state: AuditState) -> AuditState:
            """Perform initial analysis of the invoice"""
            invoice_data = state["invoice_data"]
            policy_data = state["policy_data"]
            
            # Add initial steps to check
            next_steps = [
                "check_duplicate",
                "check_policy_compliance",
                "verify_calculations"
            ]
            
            return {
                **state,
                "next_steps": next_steps
            }
        
        # 2. Tool execution node using LangGraph's ToolNode
        tool_node = ToolNode(self.tools)
        
        # 3. Issue detection node
        def detect_issues(state: AuditState) -> AuditState:
            """Detect issues based on tool results and invoice data"""
            invoice_data = state["invoice_data"]
            policy_data = state["policy_data"]
            history = state["history"]
            
            # Extract tool results from history
            tool_results = [msg.content for msg in history if isinstance(msg, AIMessage)]
            
            # Process results to identify issues
            issues = state["issues"]
            
            # Example logic to extract issues from tool results
            for result in tool_results:
                if "Error:" in result or "POLICY VIOLATION:" in result or "DUPLICATE FOUND:" in result:
                    issues.append({
                        "type": "Tool-Detected Issue",
                        "description": result,
                        "severity": "medium",
                        "source": "langgraph_workflow"
                    })
            
            return {
                **state,
                "issues": issues
            }
        
        # 4. Summary generation node
        def generate_summary(state: AuditState) -> AuditState:
            """Generate a summary of the audit results"""
            invoice_data = state["invoice_data"]
            issues = state["issues"]
            
            if not issues:
                summary = f"No issues found in invoice {invoice_data.get('invoice_id', 'UNKNOWN')}."
            else:
                summary = f"Found {len(issues)} issues in invoice {invoice_data.get('invoice_id', 'UNKNOWN')}."
            
            # Mark the workflow as complete
            return {
                **state,
                "summary": summary,
                "complete": True
            }
        
        # 5. Decision node to determine next step
        def decide_next_step(state: AuditState) -> str:
            """Decide the next step in the workflow"""
            if not state["next_steps"]:
                return "generate_summary"
            
            # Get the next step
            next_step = state["next_steps"][0]
            remaining_steps = state["next_steps"][1:]
            
            # Update the state
            state["next_steps"] = remaining_steps
            
            if next_step == "check_duplicate":
                return "check_duplicate"
            elif next_step == "check_policy_compliance":
                return "check_policy_compliance"
            elif next_step == "verify_calculations":
                return "verify_calculations"
            else:
                return "detect_issues"
        
        # Add nodes to the graph
        workflow.add_node("initial_analysis", initial_analysis)
        workflow.add_node("tool_node", tool_node)
        workflow.add_node("detect_issues", detect_issues)
        workflow.add_node("generate_summary", generate_summary)
        
        # Add edges
        workflow.add_edge("initial_analysis", decide_next_step)
        workflow.add_edge("check_duplicate", "detect_issues")
        workflow.add_edge("check_policy_compliance", "detect_issues")
        workflow.add_edge("verify_calculations", "detect_issues")
        workflow.add_edge("detect_issues", decide_next_step)
        workflow.add_edge("generate_summary", END)
        
        # Compile the graph
        self.graph = workflow.compile()
        
        return self.graph
    
    def run_audit(self, invoice_data: Dict[str, Any], policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the audit workflow using LangGraph"""
        # Initialize the state
        initial_state = {
            "invoice_data": invoice_data,
            "policy_data": policy_data,
            "issues": [],
            "history": [],
            "next_steps": [],
            "complete": False
        }
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Format the result for return
        return {
            "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
            "vendor": invoice_data.get("vendor", "UNKNOWN"),
            "total": invoice_data.get("total", 0.0),
            "issues_found": len(result["issues"]) > 0,
            "issues": result["issues"],
            "summary": result.get("summary", "Audit completed.")
        }