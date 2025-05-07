"""
Auditor Agent Examples

This module provides examples of how to use the invoice auditing agent framework.
"""

import os
import json
import argparse
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .auditor import AuditorAgent, AuditGraph
from .memory import InvoiceMemory, AuditMemory, create_conversation_memory
from .tools import AuditorTools
from .workflow import AuditWorkflow


console = Console()


def example_simple_audit():
    """Example of a simple audit using the AuditorAgent"""
    console.print("[bold blue]Running Simple Audit Example[/bold blue]")
    
    # Sample invoice data
    invoice_data = {
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
    }
    
    # Sample policy data
    policy_data = {
        "max_amount": 1000.00,
        "allowed_categories": ["office_supplies", "electronics", "software"],
        "max_item_prices": {
            "office_supplies": 100.00,
            "electronics": 500.00,
            "software": 200.00,
            "furniture": 300.00  # This will trigger a policy violation for the desk chair
        }
    }
    
    # Create the auditor agent
    agent_config = {
        "model_name": "gpt-4o",
        "temperature": 0.0,
        "verbose": True,
        "use_agent_analysis": True
    }
    
    console.print("Creating auditor agent...")
    agent = AuditorAgent(config=agent_config)
    
    # Run the audit
    console.print("Running audit...")
    with console.status("[bold green]Auditing invoice...[/bold green]"):
        audit_result = agent.audit_invoice(invoice_data, policy_data)
    
    # Display the results
    display_audit_results(audit_result)


def example_workflow_audit():
    """Example of a workflow-based audit using AuditWorkflow"""
    console.print("[bold blue]Running Workflow Audit Example[/bold blue]")
    
    # Sample invoice data with calculation error
    invoice_data = {
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
    }
    
    # Sample policy data
    policy_data = {
        "max_amount": 1500.00,
        "allowed_categories": ["office_supplies", "electronics", "software"],
        "max_item_prices": {
            "office_supplies": 100.00,
            "electronics": 500.00,
            "software": 350.00  # This will trigger a policy violation for the software license
        }
    }
    
    # Create the workflow
    workflow_config = {
        "model_name": "gpt-4o",
        "temperature": 0.0
    }
    
    console.print("Creating audit workflow...")
    workflow = AuditWorkflow(config=workflow_config)
    
    # Run the audit
    console.print("Running workflow-based audit...")
    with console.status("[bold green]Auditing invoice with workflow...[/bold green]"):
        audit_result = workflow.run_audit(invoice_data, policy_data)
    
    # Display the results
    display_audit_results(audit_result)


def example_memory_usage():
    """Example of using memory components with the auditor agent"""
    console.print("[bold blue]Running Memory Usage Example[/bold blue]")
    
    # Create memory components
    invoice_memory = InvoiceMemory()
    audit_memory = AuditMemory()
    
    # Sample invoice data (potential duplicate)
    invoice_data_1 = {
        "invoice_id": "INV-2023-003",
        "vendor": "Marketing Services Co.",
        "date": "2023-07-10",
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
    }
    
    # Duplicate invoice with different ID
    invoice_data_2 = {
        "invoice_id": "INV-2023-004",
        "vendor": "Marketing Services Co.",
        "date": "2023-07-10",
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
    }
    
    # Sample policy data
    policy_data = {
        "max_amount": 3000.00,
        "allowed_categories": ["marketing", "advertising", "consulting"],
        "max_item_prices": {
            "marketing": 3000.00,
            "advertising": 1500.00,
            "consulting": 2000.00
        }
    }
    
    # Create the auditor tools
    auditor_tools = AuditorTools()
    
    # Generate invoice hashes
    hash_1 = auditor_tools.generate_invoice_hash(invoice_data_1)
    hash_2 = auditor_tools.generate_invoice_hash(invoice_data_2)
    
    console.print(f"Invoice 1 Hash: {hash_1}")
    console.print(f"Invoice 2 Hash: {hash_2}")
    
    # Store the first invoice in memory
    console.print("Storing first invoice in memory...")
    invoice_memory.add_invoice(invoice_data_1["invoice_id"], invoice_data_1, hash_1)
    
    # Check if the second invoice is a duplicate
    console.print("Checking if second invoice is a duplicate...")
    duplicate_check = invoice_memory.check_duplicate(invoice_data_2["invoice_id"], hash_2)
    
    console.print(Panel(
        f"Duplicate Check Result:\n{json.dumps(duplicate_check, indent=2)}",
        title="Duplicate Detection",
        border_style="yellow"
    ))
    
    # Create the auditor agent
    agent_config = {
        "model_name": "gpt-4o",
        "temperature": 0.0,
        "verbose": False,
        "use_agent_analysis": True
    }
    
    agent = AuditorAgent(config=agent_config)
    
    # Run the audit on the first invoice
    console.print("Running audit on first invoice...")
    with console.status("[bold green]Auditing first invoice...[/bold green]"):
        audit_result_1 = agent.audit_invoice(invoice_data_1, policy_data)
    
    # Store the audit result
    audit_memory.add_audit_result(invoice_data_1["invoice_id"], audit_result_1)
    
    # Display the results
    display_audit_results(audit_result_1)
    
    # Get statistics
    console.print("[bold]Memory Statistics:[/bold]")
    invoice_stats = invoice_memory.get_statistics()
    audit_stats = audit_memory.get_issue_statistics()
    
    console.print(f"Total invoices in memory: {invoice_stats['total_invoices']}")
    console.print(f"Total vendors: {invoice_stats['total_vendors']}")
    console.print(f"Total amount: ${invoice_stats['total_amount']:.2f}")
    
    console.print(f"Total audits in memory: {audit_stats['total_audits']}")
    console.print(f"Total issues found: {audit_stats['total_issues']}")


def display_audit_results(audit_result: Dict[str, Any]):
    """Display audit results in a formatted way"""
    # Display invoice info
    invoice_panel = Panel(
        f"Invoice ID: [bold]{audit_result.get('invoice_id', 'UNKNOWN')}[/bold]\n"
        f"Vendor: [bold]{audit_result.get('vendor', 'UNKNOWN')}[/bold]\n"
        f"Total: [bold]${audit_result.get('total', 0.0):.2f}[/bold]",
        title="Invoice Information",
        border_style="blue"
    )
    console.print(invoice_panel)
    
    # Display issues
    issues = audit_result.get("issues", [])
    if issues:
        console.print(f"\n[bold red]Found {len(issues)} issues:[/bold red]\n")
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("Issue Type")
        table.add_column("Description")
        table.add_column("Severity")
        table.add_column("Source")
        
        for issue in issues:
            severity = issue.get("severity", "medium")
            severity_color = {
                "low": "green",
                "medium": "yellow",
                "high": "red"
            }.get(severity.lower(), "yellow")
            
            table.add_row(
                issue.get("type", "UNKNOWN"),
                issue.get("description", "No description"),
                f"[{severity_color}]{severity}[/{severity_color}]",
                issue.get("source", "unknown")
            )
        
        console.print(table)
    else:
        console.print("\n[bold green]No issues found![/bold green]")
    
    # Display summary
    console.print(f"\n[bold]Summary:[/bold] {audit_result.get('summary', 'No summary available.')}")


def main():
    """Main function to run examples"""
    parser = argparse.ArgumentParser(description="Invoice Auditor Agent Examples")
    parser.add_argument("--example", type=str, choices=["simple", "workflow", "memory", "all"],
                       default="all", help="Example to run")
    
    args = parser.parse_args()
    
    if args.example == "simple" or args.example == "all":
        example_simple_audit()
        console.print("\n" + "-" * 80 + "\n")
    
    if args.example == "workflow" or args.example == "all":
        example_workflow_audit()
        console.print("\n" + "-" * 80 + "\n")
    
    if args.example == "memory" or args.example == "all":
        example_memory_usage()


if __name__ == "__main__":
    main()