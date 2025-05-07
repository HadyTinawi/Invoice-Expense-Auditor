#!/usr/bin/env python3
"""
Test script for the CLI interface with report generation
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.reporting.report_generator import generate_report, ReportFormat


def main():
    """Main function for the CLI test"""
    parser = argparse.ArgumentParser(description="Test CLI for Report Generation")
    
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="Path to the input JSON file with audit results")
    parser.add_argument("--report", "-r", type=str, required=True,
                        help="Path to save the detailed report")
    parser.add_argument("--format", "-f", type=str, choices=["text", "html", "json"], default="html",
                        help="Format for the detailed report (default: html)")
    
    args = parser.parse_args()
    
    # Print banner
    print("=" * 80)
    print("Report Generator CLI Test")
    print("=" * 80)
    
    # Load audit results
    print(f"Loading audit results from: {args.input}")
    try:
        with open(args.input, 'r') as f:
            audit_results = json.load(f)
    except Exception as e:
        print(f"Error loading audit results: {str(e)}")
        sys.exit(1)
    
    # Generate report
    print(f"Generating {args.format} report...")
    try:
        # Convert string format to enum
        format_enum = ReportFormat(args.format)
        
        # Generate report
        report = generate_report(audit_results, format_enum, args.report)
        print(f"Report saved to: {args.report}")
        
        # Print file size
        file_size = os.path.getsize(args.report)
        print(f"File size: {file_size} bytes")
        
        print("\nReport generation successful!")
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()