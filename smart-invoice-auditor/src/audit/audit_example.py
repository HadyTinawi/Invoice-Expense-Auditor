"""
Rule-Based Auditing Example

This script demonstrates the rule-based auditing system for invoices,
including configurable rules for price verification, date validation,
and policy compliance.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from .rules import (
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


console = Console()


def create_sample_invoices():
    """Create sample invoices for demonstration"""
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
        # Invoice with line item sum error
        {
            "invoice_id": "INV-2023-004",
            "vendor": "Office Supplies Inc.",
            "date": "2023-07-10",
            "subtotal": 500.00,  # Incorrect subtotal (should be 475.00)
            "tax": 40.00,
            "total": 540.00,
            "line_items": [
                {
                    "description": "Standard Paper (Case)",
                    "category": "office_supplies",
                    "quantity": 5,
                    "price": 35.00  # 5 * 35 = 175
                },
                {
                    "description": "Pens (Box)",
                    "category": "office_supplies",
                    "quantity": 10,
                    "price": 10.00  # 10 * 10 = 100
                },
                {
                    "description": "Desk Lamp",
                    "category": "furniture",
                    "quantity": 2,
                    "price": 100.00  # 2 * 100 = 200
                }
                # Total: 175 + 100 + 200 = 475, not 500
            ]
        },
        # Invoice with future date
        {
            "invoice_id": "INV-2023-005",
            "vendor": "Consulting Group Inc.",
            "date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),  # Future date
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
        },
        # Invoice exceeding maximum amount
        {
            "invoice_id": "INV-2023-006",
            "vendor": "IT Services Inc.",
            "date": "2023-08-15",
            "subtotal": 8000.00,
            "tax": 640.00,
            "total": 8640.00,  # Exceeds typical max amount
            "line_items": [
                {
                    "description": "Server Hardware",
                    "category": "hardware",
                    "quantity": 1,
                    "price": 5000.00
                },
                {
                    "description": "IT Support (Monthly)",
                    "category": "services",
                    "quantity": 1,
                    "price": 3000.00
                }
            ]
        }
    ]


def create_sample_policy():
    """Create a sample policy for demonstration"""
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
            "furniture": 300.00,
            "consulting": 350.00
        }
    }


def demonstrate_basic_rules():
    """Demonstrate basic rule checks"""
    console.print("[bold blue]Demonstrating Basic Rule Checks[/bold blue]")
    
    # Create sample invoices
    invoices = create_sample_invoices()
    
    # Create individual rules
    total_rule = TotalMatchesCalculationRule()
    line_items_rule = LineItemsSumRule()
    date_rule = DateValidityRule()
    required_fields_rule = RequiredFieldsRule()
    
    # Check each invoice with each rule
    for i, invoice in enumerate(invoices[:4]):  # Use first 4 invoices
        console.print(f"\n[bold]Invoice {i+1}: {invoice['invoice_id']}[/bold]")
        
        # Display invoice summary
        console.print(Panel(
            f"Vendor: {invoice.get('vendor', 'UNKNOWN')}\n"
            f"Date: {invoice.get('date', 'UNKNOWN')}\n"
            f"Subtotal: ${invoice.get('subtotal', 0.0):.2f}\n"
            f"Tax: ${invoice.get('tax', 0.0):.2f}\n"
            f"Total: ${invoice.get('total', 0.0):.2f}",
            title="Invoice Summary",
            border_style="blue"
        ))
        
        # Check with each rule
        rules = [
            ("Total Calculation", total_rule),
            ("Line Items Sum", line_items_rule),
            ("Date Validity", date_rule),
            ("Required Fields", required_fields_rule)
        ]
        
        table = Table(title="Rule Check Results")
        table.add_column("Rule", style="cyan")
        table.add_column("Result", style="green")
        table.add_column("Message", style="yellow")
        
        for rule_name, rule in rules:
            result = rule.check(invoice)
            result_style = "green" if result.passed else "red"
            result_text = "✓ PASSED" if result.passed else "✗ FAILED"
            
            table.add_row(
                rule_name,
                f"[{result_style}]{result_text}[/{result_style}]",
                result.message
            )
        
        console.print(table)


def demonstrate_rule_sets():
    """Demonstrate rule sets"""
    console.print("[bold blue]Demonstrating Rule Sets[/bold blue]")
    
    # Create sample invoices
    invoices = create_sample_invoices()
    
    # Create sample policy
    policy = create_sample_policy()
    
    # Create default rule sets
    rule_sets = create_default_rule_sets()
    
    # Check each invoice with each rule set
    for rule_set_name, rule_set in rule_sets.items():
        console.print(f"\n[bold]Rule Set: {rule_set_name}[/bold]")
        console.print(f"Description: {rule_set.description}")
        console.print(f"Number of rules: {len(rule_set.rules)}")
        
        # Check a sample invoice
        invoice = invoices[1]  # Use the second invoice (with calculation error)
        context = {"policy_data": policy}
        
        result = rule_set.audit_invoice(invoice, context)
        
        # Display summary
        console.print(Panel(
            f"Invoice ID: {result['invoice_id']}\n"
            f"Total Rules: {result['total_rules']}\n"
            f"Passed Rules: {result['passed_rules']}\n"
            f"Failed Rules: {result['failed_rules']}\n"
            f"High Severity Issues: {result['severity_counts']['high']}\n"
            f"Medium Severity Issues: {result['severity_counts']['medium']}\n"
            f"Low Severity Issues: {result['severity_counts']['low']}",
            title="Audit Summary",
            border_style="yellow"
        ))
        
        # Display detailed results
        table = Table(title="Detailed Results")
        table.add_column("Rule ID", style="cyan")
        table.add_column("Result", style="green")
        table.add_column("Message", style="yellow")
        table.add_column("Severity", style="magenta")
        
        for rule_result in result["results"]:
            result_style = "green" if rule_result["passed"] else "red"
            result_text = "✓ PASSED" if rule_result["passed"] else "✗ FAILED"
            severity = rule_result["severity"]
            severity_style = {
                "low": "green",
                "medium": "yellow",
                "high": "red"
            }.get(severity.lower(), "yellow")
            
            table.add_row(
                rule_result["rule_id"],
                f"[{result_style}]{result_text}[/{result_style}]",
                rule_result["message"],
                f"[{severity_style}]{severity}[/{severity_style}]"
            )
        
        console.print(table)


def demonstrate_rule_engine():
    """Demonstrate the rule engine"""
    console.print("[bold blue]Demonstrating Rule Engine[/bold blue]")
    
    # Create sample invoices
    invoices = create_sample_invoices()
    
    # Create sample policy
    policy = create_sample_policy()
    
    # Create rule engine
    engine = RuleEngine()
    
    # Add default rule sets
    for name, rule_set in create_default_rule_sets().items():
        engine.add_rule_set(rule_set)
    
    # Create a custom rule set
    custom_rule_set = RuleSet(
        name="custom_audit",
        description="Custom audit rules for high-value invoices"
    )
    
    # Add a custom rule
    def check_high_value_invoice(invoice_data, context):
        total = invoice_data.get("total", 0.0)
        if total >= 3000.0:
            return False, f"Invoice total (${total:.2f}) requires special approval"
        return True, f"Invoice total (${total:.2f}) is within normal range"
    
    custom_rule = CustomRule(
        rule_id="high_value_check",
        description="Check if invoice requires special approval",
        check_func=check_high_value_invoice,
        severity="high"
    )
    
    custom_rule_set.add_rule(custom_rule)
    custom_rule_set.add_rule(RequiredFieldsRule())
    custom_rule_set.add_rule(DateValidityRule())
    
    # Add the custom rule set to the engine
    engine.add_rule_set(custom_rule_set)
    
    # List available rule sets
    console.print(f"Available rule sets: {', '.join(engine.list_rule_sets())}")
    
    # Audit invoices with different rule sets
    for i, invoice in enumerate(invoices):
        if i == 0 or i == 5:  # Only use first and last invoice for brevity
            console.print(f"\n[bold]Invoice {i+1}: {invoice['invoice_id']}[/bold]")
            
            # Display invoice summary
            console.print(Panel(
                f"Vendor: {invoice.get('vendor', 'UNKNOWN')}\n"
                f"Date: {invoice.get('date', 'UNKNOWN')}\n"
                f"Total: ${invoice.get('total', 0.0):.2f}",
                title="Invoice Summary",
                border_style="blue"
            ))
            
            # Audit with specific rule set
            rule_set_name = "comprehensive_audit" if i == 0 else "custom_audit"
            context = {"policy_data": policy}
            
            result = engine.audit_invoice(invoice, rule_set_name, context)
            
            # Display summary
            console.print(Panel(
                f"Rule Set: {rule_set_name}\n"
                f"Total Rules: {result['total_rules']}\n"
                f"Passed Rules: {result['passed_rules']}\n"
                f"Failed Rules: {result['failed_rules']}",
                title="Audit Summary",
                border_style="yellow"
            ))
            
            # Display detailed results
            table = Table(title="Detailed Results")
            table.add_column("Rule ID", style="cyan")
            table.add_column("Result", style="green")
            table.add_column("Message", style="yellow")
            
            for rule_result in result["results"]:
                result_style = "green" if rule_result["passed"] else "red"
                result_text = "✓ PASSED" if rule_result["passed"] else "✗ FAILED"
                
                table.add_row(
                    rule_result["rule_id"],
                    f"[{result_style}]{result_text}[/{result_style}]",
                    rule_result["message"]
                )
            
            console.print(table)


def demonstrate_rule_configuration():
    """Demonstrate rule configuration and serialization"""
    console.print("[bold blue]Demonstrating Rule Configuration and Serialization[/bold blue]")
    
    # Create a custom rule set
    custom_rule_set = RuleSet(
        name="configurable_audit",
        description="Configurable audit rules with custom parameters"
    )
    
    # Add rules with custom parameters
    custom_rule_set.add_rule(RequiredFieldsRule(
        required_fields=["invoice_id", "vendor", "date", "total", "payment_terms"]
    ))
    
    custom_rule_set.add_rule(DateValidityRule(
        max_age_days=180,  # 6 months
        allow_future_days=7  # Allow dates up to 7 days in the future
    ))
    
    custom_rule_set.add_rule(MaxAmountRule(
        max_amount=10000.0,  # Higher limit
        severity="high"
    ))
    
    # Convert to JSON and YAML
    json_str = custom_rule_set.to_json()
    yaml_str = custom_rule_set.to_yaml()
    
    # Display serialized formats
    console.print("[bold]JSON Representation:[/bold]")
    console.print(Panel(json_str, border_style="green"))
    
    console.print("[bold]YAML Representation:[/bold]")
    console.print(Panel(yaml_str, border_style="blue"))
    
    # Recreate from JSON
    recreated_rule_set = RuleSet.from_json(json_str)
    
    console.print(f"Recreated rule set: {recreated_rule_set.name}")
    console.print(f"Number of rules: {len(recreated_rule_set.rules)}")
    
    # Save to file
    rules_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                           "data", "rules")
    os.makedirs(rules_dir, exist_ok=True)
    
    file_path = os.path.join(rules_dir, "configurable_audit.json")
    with open(file_path, 'w') as f:
        f.write(json_str)
    
    console.print(f"Rule set saved to: {file_path}")
    
    # Create rule engine and load from file
    engine = RuleEngine()
    engine.load_rule_sets_from_file(file_path)
    
    console.print(f"Loaded rule sets: {', '.join(engine.list_rule_sets())}")


def main():
    """Main function to run all demonstrations"""
    console.print("[bold]Rule-Based Auditing System Demonstration[/bold]")
    console.print("=" * 80)
    
    demonstrate_basic_rules()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_rule_sets()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_rule_engine()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_rule_configuration()


if __name__ == "__main__":
    main()