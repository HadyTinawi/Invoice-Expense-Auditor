#!/usr/bin/env python3
"""
Smart Invoice Auditor - CLI Interface

This module provides a command-line interface for the Smart Invoice Auditor.
"""

import os
import sys
import argparse
from typing import Dict, Any, Optional
from pathlib import Path
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr.processor import create_processor
from src.agent.auditor import AuditorAgent
from src.policy.manager import PolicyManager


console = Console()


def process_invoice(invoice_path: str, policy_path: Optional[str] = None, 
                   ocr_engine: str = "tesseract", output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Process and audit an invoice
    
    Args:
        invoice_path: Path to the invoice PDF
        policy_path: Path to the policy file (optional)
        ocr_engine: OCR engine to use (tesseract or textract)
        output_path: Path to save the audit results (optional)
        
    Returns:
        Audit results
    """
    # Validate invoice path
    if not os.path.exists(invoice_path):
        console.print(f"[bold red]Error:[/bold red] Invoice file not found: {invoice_path}")
        sys.exit(1)
    
    # Create OCR processor
    console.print(f"Creating OCR processor ({ocr_engine})...")
    ocr_processor = create_processor(ocr_engine)
    
    # Process invoice
    console.print(f"Processing invoice: {invoice_path}")
    with console.status("[bold green]Extracting data from invoice...[/bold green]"):
        invoice_data = ocr_processor.process_pdf(invoice_path)
    
    # Load policy data
    policy_manager = PolicyManager()
    if policy_path:
        # Load specific policy file
        if not os.path.exists(policy_path):
            console.print(f"[bold red]Error:[/bold red] Policy file not found: {policy_path}")
            sys.exit(1)
        
        if policy_path.endswith('.csv'):
            vendor_name = os.path.splitext(os.path.basename(policy_path))[0]
            policy_data = policy_manager._load_csv_policy(policy_path)
        elif policy_path.endswith('.json'):
            vendor_name = os.path.splitext(os.path.basename(policy_path))[0]
            policy_data = policy_manager._load_json_policy(policy_path)
        else:
            console.print(f"[bold red]Error:[/bold red] Unsupported policy file format: {policy_path}")
            sys.exit(1)
    else:
        # Try to find policy based on vendor name
        vendor_name = invoice_data.get("vendor", "UNKNOWN")
        policy_data = policy_manager.get_policy(vendor_name)
        
        if not policy_data:
            console.print(f"[bold yellow]Warning:[/bold yellow] No policy found for vendor: {vendor_name}")
            policy_data = {}
    
    # Create auditor agent with configuration
    console.print("Creating auditor agent...")
    agent_config = {
        "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "temperature": 0.0,
        "verbose": False,
        "use_agent_analysis": True
    }
    
    # Decide whether to use the simple agent or the workflow
    use_workflow = os.environ.get("USE_WORKFLOW", "false").lower() == "true"
    
    if use_workflow:
        from src.agent.workflow import AuditWorkflow
        workflow = AuditWorkflow(config=agent_config)
        
        # Audit invoice using workflow
        console.print("Auditing invoice using LangGraph workflow...")
        with console.status("[bold green]Analyzing invoice for issues...[/bold green]"):
            audit_results = workflow.run_audit(invoice_data, policy_data)
    else:
        auditor = AuditorAgent(config=agent_config)
        
        # Audit invoice using agent
        console.print("Auditing invoice using LangChain agent...")
        with console.status("[bold green]Analyzing invoice for issues...[/bold green]"):
            audit_results = auditor.audit_invoice(invoice_data, policy_data)
    
    # Save results if output path is provided
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(audit_results, f, indent=2)
        console.print(f"Audit results saved to: {output_path}")
    
    return audit_results


def display_results(audit_results: Dict[str, Any]):
    """Display audit results in a formatted way"""
    console.print("\n")
    
    # Display invoice info
    invoice_panel = Panel(
        f"Invoice ID: [bold]{audit_results.get('invoice_id', 'UNKNOWN')}[/bold]\n"
        f"Vendor: [bold]{audit_results.get('vendor', 'UNKNOWN')}[/bold]\n"
        f"Total: [bold]${audit_results.get('total', 0.0):.2f}[/bold]",
        title="Invoice Information",
        border_style="blue"
    )
    console.print(invoice_panel)
    
    # Display issues
    issues = audit_results.get("issues", [])
    if issues:
        console.print(f"\n[bold red]Found {len(issues)} issues:[/bold red]\n")
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("Issue Type")
        table.add_column("Description")
        table.add_column("Severity")
        
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
                f"[{severity_color}]{severity}[/{severity_color}]"
            )
        
        console.print(table)
    else:
        console.print("\n[bold green]No issues found![/bold green]")
    
    # Display summary
    console.print(f"\n[bold]Summary:[/bold] {audit_results.get('summary', 'No summary available.')}")


def run_demo():
    """Run a demo with sample data"""
    # Get the path to the sample invoice
    sample_invoice_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     "data", "invoices")
    sample_policy_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "data", "policies")
    
    # Check if sample data exists
    if not os.path.exists(sample_invoice_dir) or not os.listdir(sample_invoice_dir):
        console.print("[bold red]Error:[/bold red] No sample invoices found in data/invoices directory.")
        sys.exit(1)
    
    # Get the first sample invoice
    sample_invoice = os.path.join(sample_invoice_dir, os.listdir(sample_invoice_dir)[0])
    
    # Get the first sample policy if available
    sample_policy = None
    if os.path.exists(sample_policy_dir) and os.listdir(sample_policy_dir):
        sample_policy = os.path.join(sample_policy_dir, os.listdir(sample_policy_dir)[0])
    
    console.print(f"[bold]Running demo with sample invoice:[/bold] {sample_invoice}")
    if sample_policy:
        console.print(f"[bold]Using sample policy:[/bold] {sample_policy}")
    
    # Process the sample invoice
    audit_results = process_invoice(sample_invoice, sample_policy)
    
    # Display the results
    display_results(audit_results)


def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="Smart Invoice Auditor - Detect billing errors and policy violations")
    
    parser.add_argument("--invoice", "-i", type=str, help="Path to the invoice PDF file")
    parser.add_argument("--policy", "-p", type=str, help="Path to the policy file (CSV or JSON)")
    parser.add_argument("--ocr", "-o", type=str, choices=["tesseract", "textract"], default="tesseract",
                        help="OCR engine to use (default: tesseract)")
    parser.add_argument("--output", type=str, help="Path to save the audit results (JSON)")
    parser.add_argument("--demo", action="store_true", help="Run with sample data")
    
    args = parser.parse_args()
    
    # Print banner
    console.print("[bold blue]Smart Invoice Auditor[/bold blue]")
    console.print("[italic]Detect billing errors and policy violations in invoices[/italic]\n")
    
    if args.demo:
        run_demo()
    elif args.invoice:
        # Process the invoice
        audit_results = process_invoice(args.invoice, args.policy, args.ocr, args.output)
        
        # Display the results
        display_results(audit_results)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()