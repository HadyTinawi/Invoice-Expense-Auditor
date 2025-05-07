"""
Policy Management Example

This script demonstrates the enhanced policy management capabilities
of the invoice auditor system, including policy loading, rule creation,
and invoice compliance checking.
"""

import os
import json
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from .manager import PolicyManager, PolicyRule, PolicyViolation


console = Console()


def create_sample_policies():
    """Create sample policy files for demonstration"""
    # Create policy directory if it doesn't exist
    policy_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                             "data", "policies")
    os.makedirs(policy_dir, exist_ok=True)
    
    # Sample JSON policy
    office_supplies_policy = {
        "max_amount": 1000.00,
        "allowed_categories": ["office_supplies", "electronics", "software"],
        "max_item_prices": {
            "office_supplies": 100.00,
            "electronics": 500.00,
            "software": 200.00,
            "furniture": 300.00
        },
        "required_fields": ["invoice_id", "vendor", "date", "total"],
        "rules": [
            {
                "rule_id": "office_supplies_date_range",
                "rule_type": "date_range",
                "parameters": {
                    "min_date": "2023-01-01",
                    "max_date": "2023-12-31"
                },
                "description": "Invoice date must be within current year",
                "severity": "medium"
            }
        ]
    }
    
    # Sample CSV policy (as list of dictionaries for conversion to CSV)
    tech_policy_data = [
        {
            "rule_id": "tech_max_amount",
            "rule_type": "max_amount",
            "parameters": json.dumps({"max_amount": 2000.00}),
            "description": "Maximum invoice amount for Tech Solutions",
            "severity": "high"
        },
        {
            "rule_id": "tech_allowed_categories",
            "rule_type": "allowed_categories",
            "parameters": json.dumps({"allowed_categories": ["electronics", "software", "cloud_services"]}),
            "description": "Allowed expense categories for Tech Solutions",
            "severity": "medium"
        }
    ]
    
    # Sample TXT policy content
    marketing_policy_content = """# Marketing Services Policy
# Simple key-value format

max_amount = 5000.00
allowed_categories = [marketing, advertising, design, consulting]
required_fields = [invoice_id, vendor, date, total, subtotal]

# Maximum prices by category
max_item_prices.marketing = 2000.00
max_item_prices.advertising = 3000.00
max_item_prices.design = 1500.00
max_item_prices.consulting = 1000.00
"""
    
    # Save the policies
    policy_manager = PolicyManager(policy_dir)
    
    # Save JSON policy
    policy_manager.add_policy("Office_Supplies_Inc", office_supplies_policy, "json")
    
    # Save CSV policy
    policy_manager.add_policy("Tech_Solutions_Ltd", tech_policy_data, "csv")
    
    # Save TXT policy
    txt_path = os.path.join(policy_dir, "Marketing_Services_Co.txt")
    with open(txt_path, 'w') as f:
        f.write(marketing_policy_content)
    
    console.print("[green]Sample policies created successfully![/green]")
    return policy_dir


def demonstrate_policy_loading():
    """Demonstrate loading policies from different file formats"""
    console.print("[bold blue]Demonstrating Policy Loading[/bold blue]")
    
    # Create sample policies
    policy_dir = create_sample_policies()
    
    # Load policies
    policy_manager = PolicyManager(policy_dir)
    
    # Display loaded vendors
    vendors = policy_manager.list_vendors()
    console.print(f"Loaded policies for {len(vendors)} vendors: {', '.join(vendors)}")
    
    # Display each policy
    for vendor in vendors:
        policy = policy_manager.get_policy(vendor)
        
        console.print(Panel(
            f"{json.dumps(policy, indent=2)}",
            title=f"Policy for {vendor}",
            border_style="green"
        ))
        
        # Display rules for this vendor
        if vendor in policy_manager.rules_by_vendor:
            rules = policy_manager.rules_by_vendor[vendor]
            
            table = Table(title=f"Rules for {vendor}")
            table.add_column("Rule ID", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Description", style="yellow")
            table.add_column("Severity", style="magenta")
            
            for rule in rules:
                table.add_row(
                    rule.rule_id,
                    rule.rule_type,
                    rule.description,
                    rule.severity
                )
            
            console.print(table)


def create_sample_invoices():
    """Create sample invoices for demonstration"""
    return [
        # Valid invoice
        {
            "invoice_id": "INV-2023-001",
            "vendor": "Office_Supplies_Inc",
            "date": "2023-05-15",
            "subtotal": 850.00,
            "tax": 68.00,
            "total": 918.00,
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
                    "price": 350.00  # Exceeds max price for furniture
                }
            ]
        },
        # Invoice with policy violations
        {
            "invoice_id": "INV-2023-002",
            "vendor": "Office_Supplies_Inc",
            "date": "2024-01-15",  # Outside allowed date range
            "subtotal": 1200.00,
            "tax": 96.00,
            "total": 1296.00,  # Exceeds max amount
            "line_items": [
                {
                    "description": "Laptop",
                    "category": "electronics",
                    "quantity": 1,
                    "price": 800.00  # Exceeds max price for electronics
                },
                {
                    "description": "Office Chair",
                    "category": "furniture",
                    "quantity": 2,
                    "price": 200.00
                }
            ]
        },
        # Invoice with unauthorized category
        {
            "invoice_id": "INV-2023-003",
            "vendor": "Tech_Solutions_Ltd",
            "date": "2023-06-20",
            "subtotal": 1500.00,
            "tax": 120.00,
            "total": 1620.00,
            "line_items": [
                {
                    "description": "Server Maintenance",
                    "category": "services",  # Not in allowed categories
                    "quantity": 1,
                    "price": 1500.00
                }
            ]
        },
        # Invoice with missing required fields
        {
            "invoice_id": "INV-2023-004",
            "vendor": "Marketing_Services_Co",
            # Missing date field
            "total": 4500.00,
            # Missing subtotal field
            "line_items": [
                {
                    "description": "Website Redesign",
                    "category": "design",
                    "quantity": 1,
                    "price": 4500.00  # Exceeds max price for design
                }
            ]
        }
    ]


def demonstrate_policy_checking():
    """Demonstrate checking invoices against policies"""
    console.print("[bold blue]Demonstrating Policy Checking[/bold blue]")
    
    # Load policies
    policy_manager = PolicyManager()
    
    # Create sample invoices
    invoices = create_sample_invoices()
    
    # Check each invoice
    for i, invoice in enumerate(invoices):
        vendor = invoice.get("vendor", "UNKNOWN")
        
        console.print(f"\n[bold]Checking Invoice {i+1}: {invoice['invoice_id']} from {vendor}[/bold]")
        
        # Display invoice summary
        console.print(Panel(
            f"Invoice ID: {invoice.get('invoice_id', 'UNKNOWN')}\n"
            f"Vendor: {vendor}\n"
            f"Date: {invoice.get('date', 'UNKNOWN')}\n"
            f"Total: ${invoice.get('total', 0.0):.2f}\n"
            f"Line Items: {len(invoice.get('line_items', []))}",
            title="Invoice Summary",
            border_style="blue"
        ))
        
        # Check compliance
        result = policy_manager.check_invoice_compliance(invoice)
        
        # Display result
        if result["compliant"]:
            console.print("[bold green]✓ Invoice complies with all policies[/bold green]")
        else:
            console.print(f"[bold red]✗ Found {result['violation_count']} policy violations[/bold red]")
            
            # Display violations
            table = Table(title="Policy Violations")
            table.add_column("Rule ID", style="cyan")
            table.add_column("Description", style="yellow")
            table.add_column("Severity", style="magenta")
            
            for violation in result["violations"]:
                severity = violation["severity"]
                severity_color = {
                    "low": "green",
                    "medium": "yellow",
                    "high": "red"
                }.get(severity.lower(), "yellow")
                
                table.add_row(
                    violation["rule_id"],
                    violation["description"],
                    f"[{severity_color}]{severity}[/{severity_color}]"
                )
            
            console.print(table)


def demonstrate_custom_rule_creation():
    """Demonstrate creating custom policy rules"""
    console.print("[bold blue]Demonstrating Custom Rule Creation[/bold blue]")
    
    # Load policies
    policy_manager = PolicyManager()
    
    # Create a custom rule
    custom_rule = PolicyRule(
        rule_id="custom_invoice_id_format",
        rule_type="regex_match",
        parameters={
            "field": "invoice_id",
            "pattern": r"^INV-\d{4}-\d{3}$"
        },
        description="Invoice ID must follow the format INV-YYYY-NNN",
        severity="medium"
    )
    
    # Add the rule to a vendor's policy
    vendor_name = "Office_Supplies_Inc"
    policy_manager.add_rule(vendor_name, custom_rule)
    
    console.print(f"Added custom rule to {vendor_name} policy")
    
    # Create a test invoice with invalid format
    test_invoice = {
        "invoice_id": "INVOICE-2023-1",  # Invalid format
        "vendor": vendor_name,
        "date": "2023-05-15",
        "subtotal": 100.00,
        "tax": 8.00,
        "total": 108.00
    }
    
    # Check compliance
    result = policy_manager.check_invoice_compliance(test_invoice)
    
    # Display result
    if result["compliant"]:
        console.print("[bold green]✓ Invoice complies with all policies[/bold green]")
    else:
        console.print(f"[bold red]✗ Found {result['violation_count']} policy violations[/bold red]")
        
        # Display violations
        table = Table(title="Policy Violations")
        table.add_column("Rule ID", style="cyan")
        table.add_column("Description", style="yellow")
        table.add_column("Severity", style="magenta")
        
        for violation in result["violations"]:
            severity = violation["severity"]
            severity_color = {
                "low": "green",
                "medium": "yellow",
                "high": "red"
            }.get(severity.lower(), "yellow")
            
            table.add_row(
                violation["rule_id"],
                violation["description"],
                f"[{severity_color}]{severity}[/{severity_color}]"
            )
        
        console.print(table)


def main():
    """Main function to run all demonstrations"""
    console.print("[bold]Policy Management Demonstration[/bold]")
    console.print("=" * 80)
    
    demonstrate_policy_loading()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_policy_checking()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_custom_rule_creation()


if __name__ == "__main__":
    main()