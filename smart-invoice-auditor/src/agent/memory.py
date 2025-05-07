"""
Auditor Memory Module

This module provides memory components for the invoice auditing agent.
These components help track invoice history, maintain conversation context,
and store audit results for future reference.
"""

import os
import json
import pickle
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Set
import pandas as pd
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory


class InvoiceMemory:
    """Memory component for storing and retrieving invoice data"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the invoice memory
        
        Args:
            storage_dir: Directory to store invoice data (default: data/memory)
        """
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "memory"
        )
        self.invoices = {}
        self.invoice_hashes = set()
        self._load_invoices()
    
    def _load_invoices(self):
        """Load invoices from storage"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
            return
        
        invoice_file = os.path.join(self.storage_dir, "invoices.pkl")
        if os.path.exists(invoice_file):
            try:
                with open(invoice_file, 'rb') as f:
                    self.invoices = pickle.load(f)
                
                # Build hash set for quick duplicate checking
                for invoice_id, invoice_data in self.invoices.items():
                    if "hash" in invoice_data:
                        self.invoice_hashes.add(invoice_data["hash"])
            except Exception as e:
                print(f"Error loading invoices: {e}")
    
    def _save_invoices(self):
        """Save invoices to storage"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
        
        invoice_file = os.path.join(self.storage_dir, "invoices.pkl")
        try:
            with open(invoice_file, 'wb') as f:
                pickle.dump(self.invoices, f)
        except Exception as e:
            print(f"Error saving invoices: {e}")
    
    def add_invoice(self, invoice_id: str, invoice_data: Dict[str, Any], invoice_hash: str) -> bool:
        """
        Add an invoice to memory
        
        Args:
            invoice_id: The invoice ID
            invoice_data: The invoice data
            invoice_hash: Hash of the invoice data
            
        Returns:
            True if added successfully, False if it's a duplicate
        """
        # Check if we've seen this hash before
        if invoice_hash in self.invoice_hashes:
            return False
        
        # Add timestamp for when this invoice was processed
        invoice_data["processed_at"] = datetime.now().isoformat()
        invoice_data["hash"] = invoice_hash
        
        # Store the invoice
        self.invoices[invoice_id] = invoice_data
        self.invoice_hashes.add(invoice_hash)
        
        # Save to disk
        self._save_invoices()
        
        return True
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an invoice by ID
        
        Args:
            invoice_id: The invoice ID
            
        Returns:
            Invoice data or None if not found
        """
        return self.invoices.get(invoice_id)
    
    def check_duplicate(self, invoice_id: str, invoice_hash: str) -> Dict[str, Any]:
        """
        Check if an invoice is a duplicate
        
        Args:
            invoice_id: The invoice ID
            invoice_hash: Hash of the invoice data
            
        Returns:
            Result with duplicate status and details
        """
        # Check if we've seen this ID before
        if invoice_id in self.invoices:
            return {
                "is_duplicate": True,
                "reason": f"Invoice ID {invoice_id} already exists in the system",
                "duplicate_type": "id",
                "original_invoice": self.invoices[invoice_id]
            }
        
        # Check if we've seen this hash before
        if invoice_hash in self.invoice_hashes:
            # Find the invoice with this hash
            for stored_id, stored_invoice in self.invoices.items():
                if stored_invoice.get("hash") == invoice_hash:
                    return {
                        "is_duplicate": True,
                        "reason": f"Invoice content matches existing invoice {stored_id}",
                        "duplicate_type": "content",
                        "original_invoice_id": stored_id
                    }
        
        return {
            "is_duplicate": False,
            "reason": "No duplicates found"
        }
    
    def get_vendor_history(self, vendor_name: str) -> List[Dict[str, Any]]:
        """
        Get history of invoices from a specific vendor
        
        Args:
            vendor_name: The vendor name
            
        Returns:
            List of invoices from the vendor
        """
        vendor_invoices = []
        for invoice_id, invoice_data in self.invoices.items():
            if invoice_data.get("vendor", "").lower() == vendor_name.lower():
                vendor_invoices.append(invoice_data)
        
        # Sort by date if available
        vendor_invoices.sort(
            key=lambda x: x.get("date", ""),
            reverse=True
        )
        
        return vendor_invoices
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored invoices
        
        Returns:
            Statistics about the invoices in memory
        """
        if not self.invoices:
            return {
                "total_invoices": 0,
                "total_vendors": 0,
                "total_amount": 0.0,
                "average_amount": 0.0
            }
        
        vendors = set()
        total_amount = 0.0
        
        for invoice_data in self.invoices.values():
            vendors.add(invoice_data.get("vendor", "UNKNOWN"))
            total_amount += invoice_data.get("total", 0.0)
        
        return {
            "total_invoices": len(self.invoices),
            "total_vendors": len(vendors),
            "total_amount": total_amount,
            "average_amount": total_amount / len(self.invoices) if self.invoices else 0.0,
            "vendors": list(vendors)
        }
    
    def clear(self):
        """Clear all invoices from memory"""
        self.invoices = {}
        self.invoice_hashes = set()
        self._save_invoices()


class AuditMemory:
    """Memory component for storing and retrieving audit results"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the audit memory
        
        Args:
            storage_dir: Directory to store audit data (default: data/memory)
        """
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "memory"
        )
        self.audit_results = {}
        self._load_audit_results()
    
    def _load_audit_results(self):
        """Load audit results from storage"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
            return
        
        audit_file = os.path.join(self.storage_dir, "audit_results.pkl")
        if os.path.exists(audit_file):
            try:
                with open(audit_file, 'rb') as f:
                    self.audit_results = pickle.load(f)
            except Exception as e:
                print(f"Error loading audit results: {e}")
    
    def _save_audit_results(self):
        """Save audit results to storage"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
        
        audit_file = os.path.join(self.storage_dir, "audit_results.pkl")
        try:
            with open(audit_file, 'wb') as f:
                pickle.dump(self.audit_results, f)
        except Exception as e:
            print(f"Error saving audit results: {e}")
    
    def add_audit_result(self, invoice_id: str, audit_result: Dict[str, Any]):
        """
        Add an audit result to memory
        
        Args:
            invoice_id: The invoice ID
            audit_result: The audit result data
        """
        # Add timestamp for when this audit was performed
        audit_result["audited_at"] = datetime.now().isoformat()
        
        # Store the audit result
        self.audit_results[invoice_id] = audit_result
        
        # Save to disk
        self._save_audit_results()
    
    def get_audit_result(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an audit result by invoice ID
        
        Args:
            invoice_id: The invoice ID
            
        Returns:
            Audit result or None if not found
        """
        return self.audit_results.get(invoice_id)
    
    def get_issue_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about issues found in audits
        
        Returns:
            Statistics about the issues found
        """
        if not self.audit_results:
            return {
                "total_audits": 0,
                "total_issues": 0,
                "issues_by_type": {},
                "issues_by_severity": {}
            }
        
        total_issues = 0
        issues_by_type = {}
        issues_by_severity = {"high": 0, "medium": 0, "low": 0}
        
        for audit_result in self.audit_results.values():
            issues = audit_result.get("issues", [])
            total_issues += len(issues)
            
            for issue in issues:
                issue_type = issue.get("type", "unknown")
                if issue_type in issues_by_type:
                    issues_by_type[issue_type] += 1
                else:
                    issues_by_type[issue_type] = 1
                
                severity = issue.get("severity", "medium").lower()
                if severity in issues_by_severity:
                    issues_by_severity[severity] += 1
        
        return {
            "total_audits": len(self.audit_results),
            "total_issues": total_issues,
            "issues_by_type": issues_by_type,
            "issues_by_severity": issues_by_severity,
            "average_issues_per_audit": total_issues / len(self.audit_results) if self.audit_results else 0.0
        }
    
    def clear(self):
        """Clear all audit results from memory"""
        self.audit_results = {}
        self._save_audit_results()


def create_conversation_memory(memory_type: str = "buffer", max_token_limit: int = 2000) -> Union[ConversationBufferMemory, ConversationSummaryMemory]:
    """
    Create a conversation memory component
    
    Args:
        memory_type: Type of memory to create (buffer or summary)
        max_token_limit: Maximum number of tokens to store in memory
        
    Returns:
        Conversation memory component
    """
    if memory_type.lower() == "summary":
        from langchain_openai import ChatOpenAI
        
        # Create a summarization LLM with low temperature for consistent summaries
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.0,
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        return ConversationSummaryMemory(
            llm=llm,
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=max_token_limit
        )
    else:
        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=max_token_limit
        )