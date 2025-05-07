"""
Duplicate Detection Example

This script demonstrates the advanced duplicate detection capabilities
of the invoice auditor system.
"""

import os
import json
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from .duplicate_detector import DuplicateDetector


console = Console()


def load_sample_invoices() -> List[Dict[str, Any]]:
    """Load sample invoices for demonstration"""
    return [
        # Original invoice
        {
            "invoice_id": "INV-2023-001",
            "vendor": "Office Supplies Inc.",
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
                    "price": 350.00
                }
            ]
        },
        # Exact duplicate with different ID
        {
            "invoice_id": "INV-2023-001-DUP",
            "vendor": "Office Supplies Inc.",
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
                    "price": 350.00
                }
            ]
        },
        # Similar invoice with small differences
        {
            "invoice_id": "INV-2023-002",
            "vendor": "Office Supplies Inc.",
            "date": "2023-05-16",  # One day later
            "subtotal": 850.00,
            "tax": 68.00,
            "total": 920.00,  # Slightly different total
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
        # Different invoice from same vendor
        {
            "invoice_id": "INV-2023-003",
            "vendor": "Office Supplies Inc.",
            "date": "2023-06-20",  # Different month
            "subtotal": 420.00,
            "tax": 33.60,
            "total": 453.60,
            "line_items": [
                {
                    "description": "Standard Paper (Case)",
                    "category": "office_supplies",
                    "quantity": 4,
                    "price": 30.00
                },
                {
                    "description": "Pens (Box)",
                    "category": "office_supplies",
                    "quantity": 10,
                    "price": 12.00
                },
                {
                    "description": "Desk Lamp",
                    "category": "furniture",
                    "quantity": 2,
                    "price": 75.00
                }
            ]
        },
        # Invoice from different vendor
        {
            "invoice_id": "INV-2023-004",
            "vendor": "Tech Solutions Ltd.",
            "date": "2023-05-15",  # Same date as first invoice
            "subtotal": 1200.00,
            "tax": 96.00,
            "total": 1296.00,
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
        # Potential fraud - same invoice resubmitted with small changes
        {
            "invoice_id": "INV-2023-005",
            "vendor": "Office Supplies Inc.",
            "date": "2023-05-15",  # Same date
            "subtotal": 850.00,
            "tax": 68.00,
            "total": 918.00,
            "line_items": [
                {
                    "description": "Premium Paper (Case)",  # Same items
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
                    "description": "Office Chair",  # Slightly different description
                    "category": "furniture",
                    "quantity": 1,
                    "price": 350.00
                }
            ]
        }
    ]


def demonstrate_exact_matching():
    """Demonstrate exact duplicate matching"""
    console.print("[bold blue]Demonstrating Exact Duplicate Matching[/bold blue]")
    
    # Load sample invoices
    invoices = load_sample_invoices()
    
    # Create detector with first invoice in history
    detector = DuplicateDetector({invoices[0]["invoice_id"]: invoices[0]})
    
    # Check the exact duplicate
    result = detector.check_exact_duplicate(invoices[1]["invoice_id"], invoices[1])
    
    console.print(Panel(
        f"Checking invoice {invoices[1]['invoice_id']} against {invoices[0]['invoice_id']}:\n\n"
        f"Result: {json.dumps(result, indent=2)}",
        title="Exact Duplicate Check",
        border_style="red" if result["is_duplicate"] else "green"
    ))
    
    # Check a non-duplicate
    result = detector.check_exact_duplicate(invoices[4]["invoice_id"], invoices[4])
    
    console.print(Panel(
        f"Checking invoice {invoices[4]['invoice_id']} against {invoices[0]['invoice_id']}:\n\n"
        f"Result: {json.dumps(result, indent=2)}",
        title="Exact Duplicate Check",
        border_style="red" if result["is_duplicate"] else "green"
    ))


def demonstrate_similarity_scoring():
    """Demonstrate similarity scoring between invoices"""
    console.print("[bold blue]Demonstrating Invoice Similarity Scoring[/bold blue]")
    
    # Load sample invoices
    invoices = load_sample_invoices()
    
    # Create detector
    detector = DuplicateDetector()
    
    # Create a table to show similarity scores
    table = Table(title="Invoice Similarity Scores")
    table.add_column("Invoice 1", style="cyan")
    table.add_column("Invoice 2", style="cyan")
    table.add_column("Similarity Score", style="magenta")
    table.add_column("Interpretation", style="yellow")
    
    # Compare the first invoice with all others
    base_invoice = invoices[0]
    
    for i, invoice in enumerate(invoices[1:], 1):
        similarity = detector.calculate_invoice_similarity(base_invoice, invoice)
        
        interpretation = "Unknown"
        if similarity >= 0.95:
            interpretation = "Exact Duplicate"
            style = "bold red"
        elif similarity >= 0.85:
            interpretation = "Very Similar (Likely Duplicate)"
            style = "red"
        elif similarity >= 0.70:
            interpretation = "Somewhat Similar (Possible Duplicate)"
            style = "yellow"
        else:
            interpretation = "Different Invoice"
            style = "green"
        
        table.add_row(
            f"{base_invoice['invoice_id']}",
            f"{invoice['invoice_id']}",
            f"{similarity:.4f}",
            f"[{style}]{interpretation}[/{style}]"
        )
    
    console.print(table)


def demonstrate_duplicate_detection():
    """Demonstrate comprehensive duplicate detection"""
    console.print("[bold blue]Demonstrating Comprehensive Duplicate Detection[/bold blue]")
    
    # Load sample invoices
    invoices = load_sample_invoices()
    
    # Create detector with first invoice in history
    invoice_history = {invoices[0]["invoice_id"]: invoices[0]}
    detector = DuplicateDetector(invoice_history)
    
    # Check each invoice
    for i, invoice in enumerate(invoices[1:], 1):
        result = detector.check_duplicate(invoice)
        
        console.print(Panel(
            f"Checking invoice {invoice['invoice_id']}:\n\n"
            f"Result: {json.dumps(result, indent=2)}",
            title=f"Duplicate Check {i}",
            border_style="red" if result["is_duplicate"] else "green"
        ))
        
        # Add to history for next checks
        if not result["is_duplicate"]:
            detector.add_invoice(invoice["invoice_id"], invoice)


def demonstrate_duplicate_clusters():
    """Demonstrate duplicate clustering"""
    console.print("[bold blue]Demonstrating Duplicate Clustering[/bold blue]")
    
    # Load sample invoices
    invoices = load_sample_invoices()
    
    # Create detector with all invoices
    invoice_history = {invoice["invoice_id"]: invoice for invoice in invoices}
    detector = DuplicateDetector(invoice_history)
    
    # Get duplicate clusters
    clusters = detector.get_duplicate_clusters(similarity_threshold=0.85)
    
    # Display clusters
    console.print(f"Found {len(clusters)} duplicate clusters:")
    
    for i, cluster in enumerate(clusters, 1):
        table = Table(title=f"Duplicate Cluster {i}")
        table.add_column("Invoice ID", style="cyan")
        table.add_column("Vendor", style="green")
        table.add_column("Date", style="yellow")
        table.add_column("Total", style="magenta")
        
        for invoice_id in cluster:
            invoice = invoice_history[invoice_id]
            table.add_row(
                invoice_id,
                invoice["vendor"],
                invoice["date"],
                f"${invoice['total']:.2f}"
            )
        
        console.print(table)
        console.print("")


def demonstrate_duplicate_report():
    """Demonstrate duplicate report generation"""
    console.print("[bold blue]Demonstrating Duplicate Report Generation[/bold blue]")
    
    # Load sample invoices
    invoices = load_sample_invoices()
    
    # Create detector with all invoices
    invoice_history = {invoice["invoice_id"]: invoice for invoice in invoices}
    detector = DuplicateDetector(invoice_history)
    
    # Generate report
    report = detector.generate_duplicate_report()
    
    # Display report summary
    console.print(Panel(
        f"Total Invoices: {report['total_invoices']}\n"
        f"Duplicate Clusters: {report['total_duplicate_clusters']}\n"
        f"Potential Duplicates: {report['total_potential_duplicates']}\n"
        f"Duplicate Percentage: {report['duplicate_percentage']:.2f}%",
        title="Duplicate Report Summary",
        border_style="blue"
    ))
    
    # Display cluster details
    for cluster in report["clusters"]:
        table = Table(title=f"Duplicate Cluster {cluster['cluster_id']}")
        table.add_column("Invoice ID", style="cyan")
        table.add_column("Vendor", style="green")
        table.add_column("Date", style="yellow")
        table.add_column("Total", style="magenta")
        
        for invoice in cluster["invoices"]:
            table.add_row(
                invoice["invoice_id"],
                invoice["vendor"],
                invoice["date"],
                f"${invoice['total']:.2f}"
            )
        
        console.print(table)
        console.print("")


def main():
    """Main function to run all demonstrations"""
    console.print("[bold]Advanced Duplicate Detection Demonstration[/bold]")
    console.print("=" * 80)
    
    demonstrate_exact_matching()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_similarity_scoring()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_duplicate_detection()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_duplicate_clusters()
    console.print("\n" + "=" * 80 + "\n")
    
    demonstrate_duplicate_report()


if __name__ == "__main__":
    main()