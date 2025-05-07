#!/usr/bin/env python3
"""
Smart Invoice Auditor - Web Interface

This module provides a Streamlit-based web interface for the Smart Invoice Auditor.
"""

import os
import sys
import json
import tempfile
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr.processor import create_processor
from src.agent.auditor import AuditorAgent
from src.policy.manager import PolicyManager
from src.audit.rules import RuleEngine, create_default_rule_sets
from src.reporting.report_generator import generate_report, ReportFormat


# Set page configuration
st.set_page_config(
    page_title="Smart Invoice Auditor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


def process_invoice(invoice_file, policy_file=None, ocr_engine="tesseract"):
    """
    Process and audit an invoice
    
    Args:
        invoice_file: Uploaded invoice file
        policy_file: Uploaded policy file (optional)
        ocr_engine: OCR engine to use
        
    Returns:
        Audit results
    """
    # Save uploaded invoice to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_invoice:
        tmp_invoice.write(invoice_file.getvalue())
        invoice_path = tmp_invoice.name
    
    # Create OCR processor
    ocr_processor = create_processor(ocr_engine)
    
    # Process invoice
    with st.spinner("Extracting data from invoice..."):
        invoice_data = ocr_processor.process_pdf(invoice_path)
    
    # Load policy data
    policy_manager = PolicyManager()
    if policy_file:
        # Save uploaded policy to a temporary file
        file_ext = ".csv" if policy_file.name.endswith(".csv") else ".json"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_policy:
            tmp_policy.write(policy_file.getvalue())
            policy_path = tmp_policy.name
        
        if file_ext == ".csv":
            policy_data = policy_manager._load_csv_policy(policy_path)
        else:
            policy_data = policy_manager._load_json_policy(policy_path)
        
        # Clean up temporary policy file
        os.unlink(policy_path)
    else:
        # Try to find policy based on vendor name
        vendor_name = invoice_data.get("vendor", "UNKNOWN")
        policy_data = policy_manager.get_policy(vendor_name)
        
        if not policy_data:
            st.warning(f"No policy found for vendor: {vendor_name}")
            policy_data = {}
    
    # Create auditor agent with configuration
    agent_config = {
        "model_name": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "temperature": 0.0,
        "verbose": False,
        "use_agent_analysis": True
    }
    
    # Create rule engine with default rule sets
    rule_engine = RuleEngine()
    for name, rule_set in create_default_rule_sets().items():
        rule_engine.add_rule_set(rule_set)
    
    # Decide whether to use the simple agent or the workflow
    use_workflow = os.environ.get("USE_WORKFLOW", "false").lower() == "true"
    
    # Perform agent-based audit
    if use_workflow:
        from src.agent.workflow import AuditWorkflow
        workflow = AuditWorkflow(config=agent_config)
        
        # Audit invoice using workflow
        with st.spinner("Analyzing invoice using LangGraph workflow..."):
            agent_results = workflow.run_audit(invoice_data, policy_data)
    else:
        auditor = AuditorAgent(config=agent_config)
        
        # Audit invoice using agent
        with st.spinner("Analyzing invoice using LangChain agent..."):
            agent_results = auditor.audit_invoice(invoice_data, policy_data)
    
    # Perform rule-based audit
    with st.spinner("Performing rule-based audit..."):
        rule_context = {"policy_data": policy_data}
        rule_results = rule_engine.audit_invoice(invoice_data, "comprehensive_audit", rule_context)
    
    # Combine results
    audit_results = agent_results.copy()
    
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
        audit_results["issues"].extend(rule_based_issues)
        audit_results["issues_found"] = True
    
    # Update summary to include rule-based results
    audit_results["rule_engine_results"] = {
        "total_rules": rule_results.get("total_rules", 0),
        "passed_rules": rule_results.get("passed_rules", 0),
        "failed_rules": rule_results.get("failed_rules", 0)
    }
    
    # Clean up temporary invoice file
    os.unlink(invoice_path)
    
    return audit_results


def display_results(audit_results):
    """Display audit results in the Streamlit UI"""
    # Display invoice info
    st.subheader("Invoice Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Invoice ID", audit_results.get("invoice_id", "UNKNOWN"))
    with col2:
        st.metric("Vendor", audit_results.get("vendor", "UNKNOWN"))
    with col3:
        st.metric("Total", f"${audit_results.get('total', 0.0):.2f}")
    
    # Display rule-based audit results if available
    if "rule_engine_results" in audit_results:
        st.subheader("Rule-Based Audit")
        rule_results = audit_results["rule_engine_results"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rules", rule_results.get("total_rules", 0))
        with col2:
            st.metric("Passed Rules", rule_results.get("passed_rules", 0),
                     delta=rule_results.get("passed_rules", 0), delta_color="normal")
        with col3:
            st.metric("Failed Rules", rule_results.get("failed_rules", 0),
                     delta=-rule_results.get("failed_rules", 0), delta_color="inverse")
    
    # Display issues
    st.subheader("Audit Results")
    issues = audit_results.get("issues", [])
    if issues:
        st.error(f"Found {len(issues)} issues")
        
        # Convert issues to DataFrame for display
        issues_df = pd.DataFrame(issues)
        
        # Add filters for source and severity
        if not issues_df.empty and 'source' in issues_df.columns:
            sources = ['All'] + sorted(issues_df['source'].unique().tolist())
            selected_source = st.selectbox('Filter by source:', sources)
            
            if selected_source != 'All':
                issues_df = issues_df[issues_df['source'] == selected_source]
        
        if not issues_df.empty and 'severity' in issues_df.columns:
            severities = ['All', 'high', 'medium', 'low']
            selected_severity = st.selectbox('Filter by severity:', severities)
            
            if selected_severity != 'All':
                issues_df = issues_df[issues_df['severity'] == selected_severity]
        
        st.dataframe(issues_df, use_container_width=True)
    else:
        st.success("No issues found!")
    
    # Display summary
    st.subheader("Summary")
    st.write(audit_results.get("summary", "No summary available."))
    
    # Option to download results
    results_json = json.dumps(audit_results, indent=2)
    st.download_button(
        label="Download Audit Results",
        data=results_json,
        file_name="audit_results.json",
        mime="application/json"
    )
    
    # Report generation options
    st.subheader("Generate Detailed Report")
    
    col1, col2 = st.columns(2)
    with col1:
        report_format = st.selectbox(
            "Report Format",
            options=["text", "html", "json"],
            index=1,  # Default to HTML
            format_func=lambda x: {"text": "Plain Text", "html": "HTML", "json": "JSON"}[x]
        )
    
    # Generate report button
    if st.button("Generate Report"):
        try:
            # Generate report
            format_enum = ReportFormat(report_format)
            report = generate_report(audit_results, format_enum)
            
            # Determine file extension and mime type
            file_ext = {"text": "txt", "html": "html", "json": "json"}[report_format]
            mime_type = {"text": "text/plain", "html": "text/html", "json": "application/json"}[report_format]
            
            # Offer download
            st.download_button(
                label=f"Download {file_ext.upper()} Report",
                data=report,
                file_name=f"invoice_audit_report.{file_ext}",
                mime=mime_type,
                key="report_download"
            )
            
            # Preview for HTML reports
            if report_format == "html":
                with st.expander("Preview HTML Report"):
                    st.components.v1.html(report, height=500, scrolling=True)
            
            # Preview for text reports
            elif report_format == "text":
                with st.expander("Preview Text Report"):
                    st.text(report)
            
            # Preview for JSON reports
            elif report_format == "json":
                with st.expander("Preview JSON Report"):
                    st.json(json.loads(report))
                    
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")


def main():
    """Main function for the Streamlit app"""
    st.title("Smart Invoice Auditor")
    st.markdown("Detect billing errors and policy violations in invoices")
    
    # Sidebar
    st.sidebar.header("Settings")
    
    ocr_engine = st.sidebar.selectbox(
        "OCR Engine",
        options=["tesseract", "textract"],
        index=0
    )
    
    st.sidebar.header("About")
    st.sidebar.info(
        "This tool uses OCR and AI to audit invoices, "
        "detect errors, duplicates, and policy violations."
    )
    
    # Main content
    tab1, tab2 = st.tabs(["Upload Invoice", "Manage Policies"])
    
    # Upload Invoice tab
    with tab1:
        st.header("Upload Invoice")
        
        invoice_file = st.file_uploader("Upload Invoice PDF", type=["pdf"])
        policy_file = st.file_uploader("Upload Policy File (Optional)", type=["csv", "json"])
        
        if invoice_file:
            st.image("https://via.placeholder.com/800x400?text=Invoice+Preview", caption="Invoice Preview")
            
            if st.button("Audit Invoice"):
                audit_results = process_invoice(invoice_file, policy_file, ocr_engine)
                display_results(audit_results)
    
    # Manage Policies tab
    with tab2:
        st.header("Manage Policies")
        
        policy_manager = PolicyManager()
        vendors = policy_manager.list_vendors()
        
        if vendors:
            selected_vendor = st.selectbox("Select Vendor", options=vendors)
            
            if selected_vendor:
                policy_data = policy_manager.get_policy(selected_vendor)
                
                if isinstance(policy_data, list):
                    # Convert list of dicts to DataFrame
                    policy_df = pd.DataFrame(policy_data)
                    st.dataframe(policy_df, use_container_width=True)
                else:
                    # Display JSON data
                    st.json(policy_data)
        else:
            st.info("No vendor policies found. Upload a policy file to get started.")
        
        st.subheader("Upload New Policy")
        new_policy_file = st.file_uploader("Upload Policy File", type=["csv", "json"])
        new_vendor_name = st.text_input("Vendor Name")
        
        if new_policy_file and new_vendor_name and st.button("Add Policy"):
            file_ext = ".csv" if new_policy_file.name.endswith(".csv") else ".json"
            
            # Save uploaded policy to the policies directory
            policy_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     "data", "policies")
            os.makedirs(policy_dir, exist_ok=True)
            
            policy_path = os.path.join(policy_dir, f"{new_vendor_name}{file_ext}")
            with open(policy_path, "wb") as f:
                f.write(new_policy_file.getvalue())
            
            st.success(f"Policy for {new_vendor_name} added successfully!")
            st.experimental_rerun()


if __name__ == "__main__":
    main()