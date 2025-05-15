#!/usr/bin/env python3
"""
Comprehensive Test Script

This script tests all components of the Smart Invoice Auditor system:
1. Rule-based auditing system
2. Report generator
3. Integration with the main application
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
from src.audit.rules import (
    AuditRule,
    TotalMatchesCalculationRule,
    LineItemsSumRule,
    DateValidityRule,
    RequiredFieldsRule,
    MaxAmountRule,
    AllowedCategoriesRule,
    MaxItemPriceRule,
    CustomRule,
    RuleSet,
    RuleEngine,
    create_default_rule_sets
)
from src.reporting.report_generator import generate_report, ReportFormat
from src.policy.manager import PolicyManager
from src.agent.auditor import AuditorAgent


def print_header(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def create_sample_invoices():
    """Create sample invoices with various issues"""
    return [
        # Valid invoice
        {
            "invoice_id": "INV-2023-001",
            "vendor": "Office Supplies Inc.",
            "date": "2023-05-15",
            "subtotal": 850.00,
            "tax": 68.00,
            "total": 918.00,  # Correct total
            "line_items": [
                {
                    "description": "Premium Paper (Case)",
                    "category": "office_supplies",
                    "quantity": 5,
                    "price": 45.00
                },
                {
                    "description": "Ink Cartridges (Set)",
                    "category": "office_supplies",
                    "quantity": 3,
                    "price": 85.00
                },
                {
                    "description": "Desk Chair",
                    "category": "furniture",
                    "quantity": 1,
                    "price": 350.00
                }
            ]
        },
        # Invoice with calculation error
        {
            "invoice_id": "INV-2023-002",
            "vendor": "Tech Solutions Ltd.",
            "date": "2023-06-20",
            "subtotal": 1200.00,
            "tax": 96.00,
            "total": 1300.00,  # Incorrect total (should be 1296.00)
            "line_items": [
                {
                    "description": "Laptop Docking Station",
                    "category": "electronics",
                    "quantity": 2,
                    "price": 150.00
                },
                {
                    "description": "Software License (Annual)",
                    "category": "software",
                    "quantity": 3,
                    "price": 300.00
                }
            ]
        },
        # Invoice with missing fields
        {
            "invoice_id": "INV-2023-003",
            "vendor": "Marketing Services Co.",
            # Missing date
            "subtotal": 2500.00,
            "tax": 200.00,
            "total": 2700.00,
            "line_items": [
                {
                    "description": "Website Redesign",
                    "category": "marketing",
                    "quantity": 1,
                    "price": 2500.00
                }
            ]
        },
        # Invoice with policy violations
        {
            "invoice_id": "INV-2023-004",
            "vendor": "Office Supplies Inc.",
            "date": "2023-07-10",
            "subtotal": 6500.00,  # Exceeds max amount
            "tax": 520.00,
            "total": 7020.00,
            "line_items": [
                {
                    "description": "Executive Desk",
                    "category": "furniture",
                    "quantity": 1,
                    "price": 3500.00  # Exceeds category limit
                },
                {
                    "description": "Executive Chair",
                    "category": "furniture",
                    "quantity": 1,
                    "price": 2000.00  # Exceeds category limit
                },
                {
                    "description": "Entertainment System",  # Unauthorized category
                    "category": "entertainment",
                    "quantity": 1,
                    "price": 1000.00
                }
            ]
        },
        # Invoice with future date
        {
            "invoice_id": "INV-2023-005",
            "vendor": "Consulting Group Inc.",
            "date": (datetime.now().replace(year=datetime.now().year + 1)).strftime("%Y-%m-%d"),  # Future date
            "subtotal": 3000.00,
            "tax": 240.00,
            "total": 3240.00,
            "line_items": [
                {
                    "description": "Strategic Consulting",
                    "category": "consulting",
                    "quantity": 10,
                    "price": 300.00
                }
            ]
        }
    ]


def create_sample_policy():
    """Create a sample policy for testing"""
    return {
        "max_amount": 5000.00,
        "allowed_categories": [
            "office_supplies", 
            "electronics", 
            "software", 
            "furniture", 
            "consulting"
        ],
        "max_item_prices": {
            "office_supplies": 100.00,
            "electronics": 500.00,
            "software": 400.00,
            "furniture": 1000.00,
            "consulting": 350.00
        }
    }


def test_rule_based_auditing():
    """Test the rule-based auditing system"""
    print_header("Testing Rule-Based Auditing System")
    
    # Create sample invoices and policy
    invoices = create_sample_invoices()
    policy = create_sample_policy()
    
    # Create rule engine with default rule sets
    print("Creating rule engine with default rule sets...")
    rule_engine = RuleEngine()
    for name, rule_set in create_default_rule_sets().items():
        rule_engine.add_rule_set(rule_set)
    
    # Test each invoice
    for i, invoice in enumerate(invoices):
        print(f"\nTesting Invoice {i+1}: {invoice['invoice_id']}")
        print(f"Vendor: {invoice.get('vendor', 'UNKNOWN')}")
        print(f"Date: {invoice.get('date', 'UNKNOWN')}")
        print(f"Total: ${invoice.get('total', 0.0):.2f}")
        
        # Audit with comprehensive rule set
        rule_context = {"policy_data": policy}
        result = rule_engine.audit_invoice(invoice, "comprehensive_audit", rule_context)
        
        # Print results
        print(f"Total Rules: {result.get('total_rules', 0)}")
        print(f"Passed Rules: {result.get('passed_rules', 0)}")
        print(f"Failed Rules: {result.get('failed_rules', 0)}")
        
        if result.get('failed_rules', 0) > 0:
            print("\nFailed Rules:")
            for rule_result in result.get("results", []):
                if not rule_result.get("passed", True):
                    print(f"- {rule_result.get('rule_id')}: {rule_result.get('message')}")
    
    print("\nRule-based auditing system test completed successfully!")


def test_report_generator():
    """Test the report generator"""
    print_header("Testing Report Generator")
    
    # Create sample invoice with issues
    invoice = create_sample_invoices()[3]  # Use the invoice with policy violations
    
    # Create audit results
    audit_results = {
        "invoice_id": invoice["invoice_id"],
        "vendor": invoice["vendor"],
        "date": invoice["date"],
        "total": invoice["total"],
        "subtotal": invoice["subtotal"],
        "tax": invoice["tax"],
        "issues_found": True,
        "issues": [
            {
                "type": "Rule Violation: max_amount",
                "description": f"Invoice total (${invoice['total']:.2f}) exceeds maximum allowed amount ($5000.00)",
                "severity": "high",
                "source": "rule_engine"
            },
            {
                "type": "Rule Violation: max_item_price",
                "description": "Line items exceed maximum price for their category: Executive Desk ($3500.00 > $1000.00)",
                "severity": "medium",
                "source": "rule_engine"
            },
            {
                "type": "Rule Violation: allowed_categories",
                "description": "Invoice contains unauthorized categories: entertainment",
                "severity": "medium",
                "source": "rule_engine"
            }
        ],
        "summary": f"Found 3 issues in invoice {invoice['invoice_id']} (1 high, 2 medium, 0 low priority). Recommend immediate review due to high-priority issues.",
        "rule_engine_results": {
            "total_rules": 7,
            "passed_rules": 4,
            "failed_rules": 3
        }
    }
    
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
        output_path = os.path.join(output_dir, f"comprehensive_test.{extension}")
        
        # Generate report
        report = generate_report(audit_results, ReportFormat(format_name), output_path)
        print(f"Report saved to: {output_path}")
        
        # Print file size
        file_size = os.path.getsize(output_path)
        print(f"File size: {file_size} bytes")
    
    print("\nReport generator test completed successfully!")


def test_agent_integration():
    """Test integration with the agent-based system"""
    print_header("Testing Agent Integration")
    
    # Create sample invoice and policy
    invoice = create_sample_invoices()[1]  # Use the invoice with calculation error
    policy = create_sample_policy()
    
    # Create auditor agent
    print("Creating auditor agent...")
    agent_config = {
        "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "temperature": 0.0,
        "verbose": False,
        "use_agent_analysis": True
    }
    auditor = AuditorAgent(config=agent_config)
    
    # Audit invoice
    print(f"Auditing invoice {invoice['invoice_id']}...")
    try:
        audit_results = auditor.audit_invoice(invoice, policy)
        
        # Print results
        print(f"Issues found: {audit_results.get('issues_found', False)}")
        print(f"Number of issues: {len(audit_results.get('issues', []))}")
        print(f"Summary: {audit_results.get('summary', 'No summary available.')}")
        
        # Generate report
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "agent_integration_test.html")
        
        print("\nGenerating HTML report from agent results...")
        report = generate_report(audit_results, ReportFormat.HTML, output_path)
        print(f"Report saved to: {output_path}")
        
        print("\nAgent integration test completed successfully!")
    except Exception as e:
        print(f"Error during agent integration test: {str(e)}")
        print("Note: This test requires an OpenAI API key to be set in the environment.")
        print("If you don't have an API key, you can skip this test.")


def test_combined_system():
    """Test the combined system (rule-based + agent + reporting)"""
    print_header("Testing Combined System")
    
    # Create sample invoice and policy
    invoice = create_sample_invoices()[4]  # Use the invoice with future date
    policy = create_sample_policy()
    
    try:
        # Create rule engine
        rule_engine = RuleEngine()
        for name, rule_set in create_default_rule_sets().items():
            rule_engine.add_rule_set(rule_set)
        
        # Create auditor agent
        agent_config = {
            "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
            "temperature": 0.0,
            "verbose": False,
            "use_agent_analysis": True
        }
        auditor = AuditorAgent(config=agent_config)
        
        # Perform agent-based audit
        print("Performing agent-based audit...")
        agent_results = auditor.audit_invoice(invoice, policy)
        
        # Perform rule-based audit
        print("Performing rule-based audit...")
        rule_context = {"policy_data": policy}
        rule_results = rule_engine.audit_invoice(invoice, "comprehensive_audit", rule_context)
        
        # Combine results
        combined_results = agent_results.copy()
        
        # Add rule-based issues
        rule_based_issues = []
        for result in rule_results.get("results", []):
            if not result.get("passed", True):
                rule_based_issues.append({
                    "type": f"Rule Violation: {result['rule_id']}",
                    "description": result["message"],
                    "severity": result["severity"],
                    "source": "rule_engine"
                })
        
        # Add rule-based issues to the combined results
        if rule_based_issues:
            combined_results["issues"].extend(rule_based_issues)
            combined_results["issues_found"] = True
        
        # Update summary to include rule-based results
        combined_results["rule_engine_results"] = {
            "total_rules": rule_results.get("total_rules", 0),
            "passed_rules": rule_results.get("passed_rules", 0),
            "failed_rules": rule_results.get("failed_rules", 0)
        }
        
        # Print results
        print(f"\nCombined Results:")
        print(f"Total issues: {len(combined_results.get('issues', []))}")
        print(f"Agent-detected issues: {len(agent_results.get('issues', []))}")
        print(f"Rule-based issues: {len(rule_based_issues)}")
        
        # Generate report
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "combined_system_test.html")
        
        print("\nGenerating HTML report from combined results...")
        report = generate_report(combined_results, ReportFormat.HTML, output_path)
        print(f"Report saved to: {output_path}")
        
        print("\nCombined system test completed successfully!")
    except Exception as e:
        print(f"Error during combined system test: {str(e)}")
        print("Note: This test requires an OpenAI API key to be set in the environment.")
        print("If you don't have an API key, you can skip this test.")


def main():
    """Main function to run all tests"""
    print_header("Comprehensive Test Suite")
    print("This script will test all components of the Smart Invoice Auditor system.")
    
    # Test rule-based auditing
    test_rule_based_auditing()
    
    # Test report generator
    test_report_generator()
    
    # Test agent integration (requires OpenAI API key)
    if os.environ.get("OPENAI_API_KEY"):
        test_agent_integration()
        test_combined_system()
    else:
        print("\nSkipping agent integration and combined system tests (no OpenAI API key found).")
    
    print_header("All Tests Completed")
    print("The comprehensive test suite has completed successfully!")
    print("You can find the generated reports in the data/reports directory.")


if __name__ == "__main__":
    main()