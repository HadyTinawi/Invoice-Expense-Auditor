"""
Report Generator Example

This script demonstrates the report generator functionality by creating
sample reports in different formats from audit results.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any

from .report_generator import ReportGenerator, ReportFormat, generate_report


def create_sample_audit_results() -> Dict[str, Any]:
    """Create sample audit results for demonstration"""
    return {
        "invoice_id": "INV-2023-005",
        "vendor": "Tech Solutions Ltd.",
        "date": "2023-07-15",
        "total": 2450.00,
        "subtotal": 2250.00,
        "tax": 200.00,
        "issues_found": True,
        "issues": [
            {
                "type": "Rule Violation: total_matches_calculation",
                "description": "Total ($2450.00) doesn't match subtotal ($2250.00) + tax ($200.00) = $2450.00",
                "severity": "medium",
                "source": "rule_engine"
            },
            {
                "type": "Rule Violation: max_item_price",
                "description": "Line items exceed maximum price for their category: Premium Software License ($1200.00 > $400.00)",
                "severity": "high",
                "source": "rule_engine"
            },
            {
                "type": "Potential Duplicate Invoice",
                "description": "Very similar to invoice INV-2023-004 (same vendor, amount, and date)",
                "severity": "high",
                "source": "rule_based"
            },
            {
                "type": "AI-Detected Anomaly",
                "description": "Unusual spending pattern detected: 150% increase in software expenses compared to historical average",
                "severity": "medium",
                "source": "agent_analysis"
            }
        ],
        "summary": "Found 4 issues in invoice INV-2023-005 (2 high, 2 medium, 0 low priority). Recommend immediate review due to high-priority issues.",
        "rule_engine_results": {
            "total_rules": 7,
            "passed_rules": 5,
            "failed_rules": 2
        }
    }


def demonstrate_report_generator():
    """Demonstrate the report generator functionality"""
    print("Report Generator Demonstration")
    print("=" * 80)
    
    # Create sample audit results
    audit_results = create_sample_audit_results()
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                             "data", "reports")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate plain text report
    print("\nGenerating plain text report...")
    text_path = os.path.join(output_dir, "sample_report.txt")
    text_report = generate_report(audit_results, ReportFormat.PLAIN_TEXT, text_path)
    print(f"Plain text report saved to: {text_path}")
    print("First 500 characters of the report:")
    print("-" * 80)
    print(text_report[:500] + "...")
    print("-" * 80)
    
    # Generate HTML report
    print("\nGenerating HTML report...")
    html_path = os.path.join(output_dir, "sample_report.html")
    html_report = generate_report(audit_results, ReportFormat.HTML, html_path)
    print(f"HTML report saved to: {html_path}")
    print(f"HTML report size: {len(html_report)} characters")
    
    # Generate JSON report
    print("\nGenerating JSON report...")
    json_path = os.path.join(output_dir, "sample_report.json")
    json_report = generate_report(audit_results, ReportFormat.JSON, json_path)
    print(f"JSON report saved to: {json_path}")
    
    # Using the ReportGenerator class directly
    print("\nUsing ReportGenerator class directly...")
    generator = ReportGenerator()
    custom_report = generator.generate_report(
        audit_results, 
        ReportFormat.PLAIN_TEXT
    )
    print(f"Custom report generated with {len(custom_report)} characters")
    
    print("\nDemonstration complete!")


if __name__ == "__main__":
    demonstrate_report_generator()