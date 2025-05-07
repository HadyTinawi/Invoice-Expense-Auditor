"""
Audit Workflow Module

This module implements LangGraph-based workflows for invoice auditing.
It defines the state management, nodes, and edges for complex audit processes.
"""

import os
from typing import Dict, Any, List, Optional, Union, Callable, TypedDict, Annotated, Sequence
from datetime import datetime
import json

# LangChain imports
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOpenAI as LegacyChatOpenAI
from langchain.tools import BaseTool, tool

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Local imports
from .tools import AuditorTools


# Define the state schema for the audit workflow
class AuditState(TypedDict):
    """State for the audit workflow"""
    invoice_data: Dict[str, Any]
    policy_data: Dict[str, Any]
    issues: List[Dict[str, Any]]
    history: List[Union[HumanMessage, AIMessage]]
    next_steps: List[str]
    complete: bool
    audit_result: Dict[str, Any]


class AuditWorkflow:
    """LangGraph-based workflow for invoice auditing"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the audit workflow
        
        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.llm = self._get_llm()
        self.tools = self._create_tools()
        self.auditor_tools = AuditorTools()
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
        def check_duplicate(invoice_id: str, vendor: str, amount: float, date: str) -> str:
            """Check if an invoice is a duplicate based on ID, vendor, amount, and date"""
            result = self.auditor_tools.check_duplicate(invoice_id, vendor, amount, date)
            return json.dumps(result)
        
        @tool
        def check_policy_compliance(expense_category: str, amount: float, policy_data: Dict[str, Any]) -> str:
            """Check if an expense complies with policy"""
            result = self.auditor_tools.check_policy_compliance(expense_category, amount, policy_data)
            return json.dumps(result)
        
        @tool
        def verify_calculations(subtotal: float, tax: float, total: float, line_items: List[Dict[str, Any]]) -> str:
            """Verify that invoice calculations are correct"""
            result = self.auditor_tools.verify_calculations(subtotal, tax, total, line_items)
            return json.dumps(result)
        
        @tool
        def check_date_validity(invoice_date: str) -> str:
            """Check if an invoice date is valid"""
            result = self.auditor_tools.check_date_validity(invoice_date)
            return json.dumps(result)
        
        @tool
        def analyze_line_items(line_items: List[Dict[str, Any]]) -> str:
            """Analyze line items for common issues"""
            result = self.auditor_tools.analyze_line_items(line_items)
            return json.dumps(result)
        
        return [check_duplicate, check_policy_compliance, verify_calculations, check_date_validity, analyze_line_items]
    
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
                "verify_calculations",
                "check_date_validity",
                "analyze_line_items"
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
            issues = state["issues"]
            
            # Extract tool results from history
            tool_results = [msg.content for msg in history if isinstance(msg, AIMessage)]
            
            # Process results to identify issues
            for result in tool_results:
                try:
                    # Try to parse the result as JSON
                    result_data = json.loads(result)
                    
                    # Check for duplicate issues
                    if "is_duplicate" in result_data and result_data["is_duplicate"]:
                        issues.append({
                            "type": "Duplicate Invoice",
                            "description": result_data.get("reason", "Invoice appears to be a duplicate"),
                            "severity": "high",
                            "source": "langgraph_workflow"
                        })
                    
                    # Check for policy compliance issues
                    if "complies" in result_data and not result_data["complies"]:
                        issues.append({
                            "type": "Policy Violation",
                            "description": result_data.get("reason", "Invoice violates policy"),
                            "severity": result_data.get("severity", "medium"),
                            "source": "langgraph_workflow"
                        })
                    
                    # Check for calculation issues
                    if "is_correct" in result_data and not result_data["is_correct"]:
                        for issue in result_data.get("issues", []):
                            issues.append({
                                "type": "Calculation Error",
                                "description": issue.get("description", "Invoice has calculation errors"),
                                "severity": issue.get("severity", "medium"),
                                "source": "langgraph_workflow"
                            })
                    
                    # Check for date validity issues
                    if "is_valid" in result_data and not result_data["is_valid"]:
                        issues.append({
                            "type": "Date Issue",
                            "description": result_data.get("reason", "Invoice has date issues"),
                            "severity": result_data.get("severity", "medium"),
                            "source": "langgraph_workflow"
                        })
                    
                    # Check for line item issues
                    if "issues" in result_data and isinstance(result_data["issues"], list) and result_data["issues"]:
                        for issue_desc in result_data["issues"]:
                            if isinstance(issue_desc, str):
                                issues.append({
                                    "type": "Line Item Issue",
                                    "description": issue_desc,
                                    "severity": "medium",
                                    "source": "langgraph_workflow"
                                })
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, check for specific strings
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
        
        # 4. AI analysis node
        def ai_analysis(state: AuditState) -> AuditState:
            """Perform AI analysis of the invoice and issues"""
            invoice_data = state["invoice_data"]
            policy_data = state["policy_data"]
            issues = state["issues"]
            
            # Create a prompt for the AI to analyze the invoice and issues
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are an Invoice Audit Assistant. Analyze the invoice data and issues found.
                Look for patterns, inconsistencies, or additional issues that might not have been detected.
                Provide a comprehensive analysis and recommendations."""),
                HumanMessage(content=f"""
                Invoice Data: {json.dumps(invoice_data, indent=2)}
                Policy Data: {json.dumps(policy_data, indent=2)}
                Issues Found: {json.dumps(issues, indent=2)}
                
                Please provide your analysis and any additional insights or issues you can identify.
                """)
            ])
            
            # Get the AI's analysis
            ai_message = self.llm.invoke(prompt.to_messages())
            ai_analysis_text = ai_message.content
            
            # Add AI analysis as an issue if it found something new
            if "additional issue" in ai_analysis_text.lower() or "new issue" in ai_analysis_text.lower():
                issues.append({
                    "type": "AI-Detected Issue",
                    "description": ai_analysis_text,
                    "severity": "medium",
                    "source": "ai_analysis"
                })
            
            return {
                **state,
                "issues": issues,
                "history": state["history"] + [ai_message]
            }
        
        # 5. Summary generation node
        def generate_summary(state: AuditState) -> AuditState:
            """Generate a summary of the audit results"""
            invoice_data = state["invoice_data"]
            issues = state["issues"]
            
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
            
            # Create the final audit result
            audit_result = {
                "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
                "vendor": invoice_data.get("vendor", "UNKNOWN"),
                "total": invoice_data.get("total", 0.0),
                "issues_found": len(issues) > 0,
                "issues": issues,
                "summary": summary,
                "completed_at": datetime.now().isoformat()
            }
            
            # Mark the workflow as complete
            return {
                **state,
                "audit_result": audit_result,
                "complete": True
            }
        
        # 6. Decision node to determine next step
        def decide_next_step(state: AuditState) -> str:
            """Decide the next step in the workflow"""
            if not state["next_steps"]:
                return "ai_analysis"
            
            # Get the next step
            next_step = state["next_steps"][0]
            remaining_steps = state["next_steps"][1:]
            
            # Update the state
            state["next_steps"] = remaining_steps
            
            return next_step
        
        # Add nodes to the graph
        workflow.add_node("initial_analysis", initial_analysis)
        workflow.add_node("tool_node", tool_node)
        workflow.add_node("detect_issues", detect_issues)
        workflow.add_node("ai_analysis", ai_analysis)
        workflow.add_node("generate_summary", generate_summary)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "initial_analysis",
            decide_next_step,
            {
                "check_duplicate": "tool_node",
                "check_policy_compliance": "tool_node",
                "verify_calculations": "tool_node",
                "check_date_validity": "tool_node",
                "analyze_line_items": "tool_node",
                "ai_analysis": "ai_analysis"
            }
        )
        
        # Add regular edges
        workflow.add_edge("tool_node", "detect_issues")
        workflow.add_edge("detect_issues", decide_next_step)
        workflow.add_edge("ai_analysis", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        # Compile the graph
        return workflow.compile()
    
    def run_audit(self, invoice_data: Dict[str, Any], policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the audit workflow
        
        Args:
            invoice_data: The invoice data to audit
            policy_data: The policy data to check against
            
        Returns:
            Audit results
        """
        # Initialize the state
        initial_state = {
            "invoice_data": invoice_data,
            "policy_data": policy_data,
            "issues": [],
            "history": [],
            "next_steps": [],
            "complete": False,
            "audit_result": {}
        }
        
        # Run the graph
        try:
            result = self.graph.invoke(initial_state)
            return result["audit_result"]
        except Exception as e:
            # Handle any errors in the workflow
            return {
                "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
                "vendor": invoice_data.get("vendor", "UNKNOWN"),
                "total": invoice_data.get("total", 0.0),
                "issues_found": True,
                "issues": [{
                    "type": "Workflow Error",
                    "description": f"Error in audit workflow: {str(e)}",
                    "severity": "high",
                    "source": "workflow_error"
                }],
                "summary": f"Audit workflow failed with error: {str(e)}",
                "completed_at": datetime.now().isoformat(),
                "error": str(e)
            }