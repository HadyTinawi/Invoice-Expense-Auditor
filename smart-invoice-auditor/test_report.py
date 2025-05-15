#!/usr/bin/env python3
"""
Test script for the report generator
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.reporting.report_generator import generate_report, ReportFormat


def create_sample_audit_results():
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
            }
        ],
        "summary": "Found 2 issues in invoice INV-2023-005 (1 high, 1 medium, 0 low priority). Recommend review at earliest convenience.",
        "rule_engine_results": {
            "total_rules": 7,
            "passed_rules": 5,
            "failed_rules": 2
        }
    }


def main():
    """Main function"""
    print("Testing Report Generator")
    print("=" * 80)
    
    # Create sample audit results
    audit_results = create_sample_audit_results()
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate reports in different formats
    formats = [
        ("text", "txt", "Plain Text"),
        ("html", "html", "HTML"),
        ("json", "json", "JSON")
    ]
    
    for format_name, extension, description in formats:
        print(f"\nGenerating {description} report...")
        output_path = os.path.join(output_dir, f"test_report.{extension}")
        
        # Generate report
        report = generate_report(audit_results, ReportFormat(format_name), output_path)
        print(f"Report saved to: {output_path}")
        
        # Print file size
        file_size = os.path.getsize(output_path)
        print(f"File size: {file_size} bytes")
    
    print("\nTest completed successfully!")


if __name__ == "__main__":
    main()