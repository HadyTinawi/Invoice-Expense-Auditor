"""
Report Generator Module

This module provides functionality for generating detailed reports from audit results,
with explanations for each flagged issue. It supports multiple output formats including
HTML and plain text.
"""

import os
import json
import enum
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable
import html
import textwrap


class ReportFormat(enum.Enum):
    """Enum for supported report formats"""
    PLAIN_TEXT = "text"
    HTML = "html"
    JSON = "json"


class ReportGenerator:
    """Generator for detailed audit reports"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the report generator
        
        Args:
            templates_dir: Directory containing report templates (optional)
        """
        self.templates_dir = templates_dir
        self.issue_explanations = self._load_issue_explanations()
    
    def _load_issue_explanations(self) -> Dict[str, Dict[str, str]]:
        """Load explanations for different issue types"""
        # Default explanations for common issues
        return {
            # Calculation issues
            "total_matches_calculation": {
                "title": "Total Calculation Error",
                "explanation": "The invoice total doesn't match the sum of subtotal and tax. This could indicate a calculation error, intentional manipulation, or a simple mistake in arithmetic.",
                "recommendation": "Verify all calculations and request a corrected invoice if necessary."
            },
            "line_items_sum": {
                "title": "Line Items Sum Error",
                "explanation": "The sum of line items doesn't match the subtotal. This could indicate missing items, calculation errors, or hidden charges.",
                "recommendation": "Compare each line item calculation and verify the subtotal matches the sum of all items."
            },
            
            # Date issues
            "date_validity": {
                "title": "Date Validity Issue",
                "explanation": "The invoice date is either in the future, too old, or in an invalid format. Future-dated invoices may indicate an attempt to manipulate payment timing, while very old invoices might be submitted late to bypass fiscal year controls.",
                "recommendation": "Verify the correct date with the vendor and ensure it complies with your organization's invoice dating policies."
            },
            
            # Field issues
            "required_fields": {
                "title": "Missing Required Fields",
                "explanation": "The invoice is missing one or more required fields. Complete information is necessary for proper accounting, tax compliance, and audit trails.",
                "recommendation": "Request a complete invoice from the vendor with all required information."
            },
            
            # Policy issues
            "max_amount": {
                "title": "Maximum Amount Exceeded",
                "explanation": "The invoice total exceeds the maximum allowed amount for this type of expense. This could indicate unauthorized spending or a purchase that requires additional approval.",
                "recommendation": "Verify if proper authorization was obtained for this expense and check if it should have been processed through a different procurement channel."
            },
            "allowed_categories": {
                "title": "Unauthorized Expense Category",
                "explanation": "The invoice contains expense categories that are not authorized by company policy. This could indicate an attempt to categorize expenses incorrectly to bypass spending controls.",
                "recommendation": "Review the expense categorization and determine if it's appropriate or if the expense should be rejected."
            },
            "max_item_price": {
                "title": "Item Price Limit Exceeded",
                "explanation": "One or more items exceed the maximum allowed price for their category. This could indicate premium purchases that require special approval.",
                "recommendation": "Verify if the items with excessive prices were authorized and if they represent the best value for the organization."
            },
            
            # Duplicate issues
            "duplicate_invoice": {
                "title": "Potential Duplicate Invoice",
                "explanation": "This invoice appears to be a duplicate of a previously processed invoice. Processing duplicates can lead to double payments.",
                "recommendation": "Compare with the suspected duplicate invoice and verify with the vendor if this is a new charge or a duplicate submission."
            },
            
            # Generic issues
            "rule_violation": {
                "title": "Policy Rule Violation",
                "explanation": "The invoice violates one or more company policy rules. Policy rules are in place to ensure compliance with internal controls and external regulations.",
                "recommendation": "Review the specific violation details and determine if an exception is warranted or if the invoice should be rejected."
            },
            
            # AI-detected issues
            "ai_detected_issue": {
                "title": "AI-Detected Anomaly",
                "explanation": "Our AI system has detected an unusual pattern or anomaly in this invoice that doesn't match typical vendor behavior or company spending patterns.",
                "recommendation": "Review the specific details of the anomaly and investigate further if necessary."
            }
        }
    
    def generate_report(self, 
                       audit_results: Dict[str, Any], 
                       format: ReportFormat = ReportFormat.PLAIN_TEXT,
                       output_path: Optional[str] = None) -> str:
        """
        Generate a detailed report from audit results
        
        Args:
            audit_results: The audit results to report on
            format: The desired report format
            output_path: Path to save the report (optional)
            
        Returns:
            The generated report as a string
        """
        if format == ReportFormat.PLAIN_TEXT:
            report = self._generate_text_report(audit_results)
        elif format == ReportFormat.HTML:
            report = self._generate_html_report(audit_results)
        elif format == ReportFormat.JSON:
            report = self._generate_json_report(audit_results)
        else:
            raise ValueError(f"Unsupported report format: {format}")
        
        # Save report if output path is provided
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def _generate_text_report(self, audit_results: Dict[str, Any]) -> str:
        """Generate a plain text report"""
        lines = []
        
        # Report header
        lines.append("=" * 80)
        lines.append("INVOICE AUDIT REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Invoice information
        lines.append("INVOICE INFORMATION")
        lines.append("-" * 80)
        lines.append(f"Invoice ID: {audit_results.get('invoice_id', 'UNKNOWN')}")
        lines.append(f"Vendor: {audit_results.get('vendor', 'UNKNOWN')}")
        lines.append(f"Date: {audit_results.get('date', 'UNKNOWN')}")
        lines.append(f"Total: ${audit_results.get('total', 0.0):.2f}")
        lines.append("")
        
        # Summary
        lines.append("AUDIT SUMMARY")
        lines.append("-" * 80)
        lines.append(audit_results.get('summary', 'No summary available.'))
        lines.append("")
        
        # Rule-based results if available
        if "rule_engine_results" in audit_results:
            rule_results = audit_results["rule_engine_results"]
            lines.append("RULE-BASED AUDIT RESULTS")
            lines.append("-" * 80)
            lines.append(f"Total Rules: {rule_results.get('total_rules', 0)}")
            lines.append(f"Passed Rules: {rule_results.get('passed_rules', 0)}")
            lines.append(f"Failed Rules: {rule_results.get('failed_rules', 0)}")
            lines.append("")
        
        # Issues
        issues = audit_results.get("issues", [])
        if issues:
            lines.append("DETAILED ISSUES")
            lines.append("-" * 80)
            lines.append(f"Found {len(issues)} issues:")
            lines.append("")
            
            for i, issue in enumerate(issues, 1):
                issue_type = issue.get("type", "UNKNOWN")
                description = issue.get("description", "No description")
                severity = issue.get("severity", "medium")
                source = issue.get("source", "unknown")
                
                # Get explanation for this issue type
                explanation_key = self._get_explanation_key(issue_type)
                explanation = self.issue_explanations.get(explanation_key, {})
                
                lines.append(f"ISSUE {i}: {explanation.get('title', issue_type)}")
                lines.append(f"Severity: {severity.upper()}")
                lines.append(f"Source: {source}")
                lines.append(f"Description: {description}")
                
                if explanation:
                    lines.append("")
                    lines.append("Explanation:")
                    lines.append(textwrap.fill(explanation.get("explanation", ""), width=80))
                    lines.append("")
                    lines.append("Recommendation:")
                    lines.append(textwrap.fill(explanation.get("recommendation", ""), width=80))
                
                lines.append("-" * 80)
        else:
            lines.append("No issues found. The invoice appears to be valid.")
        
        # Footer
        lines.append("")
        lines.append("End of Report")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _generate_html_report(self, audit_results: Dict[str, Any]) -> str:
        """Generate an HTML report"""
        # Helper function to escape HTML
        def h(text):
            return html.escape(str(text))
        
        # Helper function for severity color
        def severity_color(severity):
            return {
                "low": "#28a745",    # Green
                "medium": "#ffc107", # Yellow
                "high": "#dc3545"    # Red
            }.get(severity.lower(), "#6c757d")  # Gray default
        
        # Start building HTML
        html_parts = []
        
        # HTML header
        html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice Audit Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #f8f9fa;
            padding: 20px;
            border-bottom: 3px solid #dee2e6;
            margin-bottom: 30px;
        }
        .section {
            margin-bottom: 30px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            overflow: hidden;
        }
        .section-header {
            background-color: #f8f9fa;
            padding: 10px 15px;
            border-bottom: 1px solid #dee2e6;
            font-weight: bold;
        }
        .section-content {
            padding: 15px;
        }
        .info-table {
            width: 100%;
            border-collapse: collapse;
        }
        .info-table td {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }
        .info-table td:first-child {
            font-weight: bold;
            width: 200px;
        }
        .issue {
            margin-bottom: 20px;
            border-left: 5px solid #6c757d;
            padding-left: 15px;
        }
        .issue-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .issue-title {
            font-weight: bold;
            font-size: 18px;
        }
        .severity-badge {
            padding: 5px 10px;
            border-radius: 3px;
            color: white;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
        }
        .explanation {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
            margin-top: 10px;
        }
        .recommendation {
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 3px;
            margin-top: 10px;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 12px;
            color: #6c757d;
        }
        .summary-metrics {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .metric {
            text-align: center;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            flex: 1;
            margin: 0 5px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
        }
        .metric-label {
            font-size: 14px;
            color: #6c757d;
        }
    </style>
</head>
<body>
""")
        
        # Report header
        html_parts.append(f"""
    <div class="header">
        <h1>Invoice Audit Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
""")
        
        # Invoice information
        html_parts.append(f"""
    <div class="section">
        <div class="section-header">Invoice Information</div>
        <div class="section-content">
            <table class="info-table">
                <tr>
                    <td>Invoice ID:</td>
                    <td>{h(audit_results.get('invoice_id', 'UNKNOWN'))}</td>
                </tr>
                <tr>
                    <td>Vendor:</td>
                    <td>{h(audit_results.get('vendor', 'UNKNOWN'))}</td>
                </tr>
                <tr>
                    <td>Date:</td>
                    <td>{h(audit_results.get('date', 'UNKNOWN'))}</td>
                </tr>
                <tr>
                    <td>Total:</td>
                    <td>${audit_results.get('total', 0.0):.2f}</td>
                </tr>
            </table>
        </div>
    </div>
""")
        
        # Summary
        html_parts.append(f"""
    <div class="section">
        <div class="section-header">Audit Summary</div>
        <div class="section-content">
            <p>{h(audit_results.get('summary', 'No summary available.'))}</p>
""")
        
        # Rule-based results if available
        if "rule_engine_results" in audit_results:
            rule_results = audit_results["rule_engine_results"]
            total_rules = rule_results.get('total_rules', 0)
            passed_rules = rule_results.get('passed_rules', 0)
            failed_rules = rule_results.get('failed_rules', 0)
            
            html_parts.append(f"""
            <div class="summary-metrics">
                <div class="metric">
                    <div class="metric-value">{total_rules}</div>
                    <div class="metric-label">Total Rules</div>
                </div>
                <div class="metric" style="color: #28a745;">
                    <div class="metric-value">{passed_rules}</div>
                    <div class="metric-label">Passed Rules</div>
                </div>
                <div class="metric" style="color: #dc3545;">
                    <div class="metric-value">{failed_rules}</div>
                    <div class="metric-label">Failed Rules</div>
                </div>
            </div>
""")
        
        html_parts.append("        </div>\n    </div>")
        
        # Issues
        issues = audit_results.get("issues", [])
        if issues:
            html_parts.append(f"""
    <div class="section">
        <div class="section-header">Detailed Issues ({len(issues)})</div>
        <div class="section-content">
""")
            
            for i, issue in enumerate(issues, 1):
                issue_type = issue.get("type", "UNKNOWN")
                description = issue.get("description", "No description")
                severity = issue.get("severity", "medium")
                source = issue.get("source", "unknown")
                
                # Get explanation for this issue type
                explanation_key = self._get_explanation_key(issue_type)
                explanation = self.issue_explanations.get(explanation_key, {})
                
                html_parts.append(f"""
            <div class="issue" style="border-left-color: {severity_color(severity)}">
                <div class="issue-header">
                    <div class="issue-title">{h(explanation.get('title', issue_type))}</div>
                    <div class="severity-badge" style="background-color: {severity_color(severity)}">
                        {h(severity)}
                    </div>
                </div>
                <p><strong>Source:</strong> {h(source)}</p>
                <p><strong>Description:</strong> {h(description)}</p>
""")
                
                if explanation:
                    html_parts.append(f"""
                <div class="explanation">
                    <strong>Explanation:</strong>
                    <p>{h(explanation.get("explanation", ""))}</p>
                </div>
                <div class="recommendation">
                    <strong>Recommendation:</strong>
                    <p>{h(explanation.get("recommendation", ""))}</p>
                </div>
""")
                
                html_parts.append("            </div>")
            
            html_parts.append("        </div>\n    </div>")
        else:
            html_parts.append("""
    <div class="section">
        <div class="section-header">Issues</div>
        <div class="section-content">
            <p style="color: #28a745; font-weight: bold;">No issues found. The invoice appears to be valid.</p>
        </div>
    </div>
""")
        
        # Footer
        html_parts.append("""
    <div class="footer">
        <p>Generated by Smart Invoice Auditor</p>
    </div>
</body>
</html>
""")
        
        return "".join(html_parts)
    
    def _generate_json_report(self, audit_results: Dict[str, Any]) -> str:
        """Generate a JSON report"""
        # Create a copy of the audit results to avoid modifying the original
        report_data = audit_results.copy()
        
        # Add explanations to each issue
        if "issues" in report_data:
            for issue in report_data["issues"]:
                issue_type = issue.get("type", "UNKNOWN")
                explanation_key = self._get_explanation_key(issue_type)
                explanation = self.issue_explanations.get(explanation_key, {})
                
                if explanation:
                    issue["explanation"] = explanation.get("explanation", "")
                    issue["recommendation"] = explanation.get("recommendation", "")
                    issue["title"] = explanation.get("title", issue_type)
        
        # Add report metadata
        report_data["report_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "generator": "Smart Invoice Auditor Report Generator"
        }
        
        # Convert to JSON string with indentation
        return json.dumps(report_data, indent=2)
    
    def _get_explanation_key(self, issue_type: str) -> str:
        """
        Get the explanation key for an issue type
        
        Args:
            issue_type: The issue type string
            
        Returns:
            The key to use for looking up explanations
        """
        # Extract the base type from issue types like "Rule Violation: rule_id"
        if ":" in issue_type:
            parts = issue_type.split(":", 1)
            if parts[0].strip().lower() == "rule violation":
                return parts[1].strip().lower()
        
        # Convert to lowercase and remove spaces
        key = issue_type.lower().replace(" ", "_")
        
        # Handle special cases
        if "duplicate" in key:
            return "duplicate_invoice"
        elif "ai" in key and "detect" in key:
            return "ai_detected_issue"
        elif "rule" in key and "violation" in key:
            return "rule_violation"
        
        return key


def generate_report(audit_results: Dict[str, Any], 
                   format: Union[ReportFormat, str] = ReportFormat.PLAIN_TEXT,
                   output_path: Optional[str] = None) -> str:
    """
    Generate a detailed report from audit results
    
    Args:
        audit_results: The audit results to report on
        format: The desired report format (ReportFormat enum or string)
        output_path: Path to save the report (optional)
        
    Returns:
        The generated report as a string
    """
    # Convert string format to enum if needed
    if isinstance(format, str):
        format = ReportFormat(format)
    
    # Create generator and generate report
    generator = ReportGenerator()
    return generator.generate_report(audit_results, format, output_path)