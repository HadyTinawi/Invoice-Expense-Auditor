"""
Duplicate Invoice Detection Module

This module provides functionality to detect duplicate invoices in a collection of invoices.
It uses a combination of exact ID matching and hash comparison to identify duplicates.
"""

from typing import List, Dict, Tuple, Set, Any, Optional
import logging
from collections import defaultdict

from .invoice import Invoice
from .utils import invoice_comparison


# Configure logging
logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Class for detecting duplicate invoices in a collection.
    
    This class provides methods for finding duplicates using various strategies:
    - Exact invoice ID matching
    - Hash-based comparison
    - Key fields comparison (vendor, date, total)
    """
    
    def __init__(self, invoices: Optional[List[Invoice]] = None):
        """
        Initialize the duplicate detector with an optional list of invoices.
        
        Args:
            invoices: Optional list of invoices to check for duplicates
        """
        self.invoices = invoices or []
        self._id_index = defaultdict(list)
        self._hash_index = defaultdict(list)
        
        # Build indices if invoices were provided
        if self.invoices:
            self._build_indices()
    
    def add_invoice(self, invoice: Invoice) -> None:
        """
        Add a single invoice to the collection.
        
        Args:
            invoice: The invoice to add
        """
        self.invoices.append(invoice)
        self._add_to_indices(invoice)
    
    def add_invoices(self, invoices: List[Invoice]) -> None:
        """
        Add multiple invoices to the collection.
        
        Args:
            invoices: The invoices to add
        """
        self.invoices.extend(invoices)
        for invoice in invoices:
            self._add_to_indices(invoice)
    
    def clear(self) -> None:
        """Clear all invoices and indices."""
        self.invoices = []
        self._id_index = defaultdict(list)
        self._hash_index = defaultdict(list)
    
    def find_duplicates(self) -> Dict[str, List[Invoice]]:
        """
        Find all duplicate invoices in the collection.
        
        This method uses both ID and hash matching to find duplicates.
        
        Returns:
            Dictionary mapping each duplicate key to a list of duplicate invoices
        """
        # Find duplicates by ID and hash
        id_duplicates = self._find_duplicates_by_id()
        hash_duplicates = self._find_duplicates_by_hash()
        
        # Merge the results (using hash as the primary identifier)
        duplicates = {}
        
        # Add hash duplicates
        for hash_key, hash_group in hash_duplicates.items():
            if len(hash_group) > 1:
                duplicates[f"hash:{hash_key}"] = hash_group
        
        # Add ID duplicates (if not already covered by hash)
        for invoice_id, id_group in id_duplicates.items():
            if len(id_group) > 1:
                # Check if these invoices are already covered by hash groups
                already_covered = False
                for hash_key, hash_group in hash_duplicates.items():
                    # Check if this group is a subset of a hash group
                    invoice_ids_in_id_group = {invoice.invoice_id for invoice in id_group}
                    invoice_ids_in_hash_group = {invoice.invoice_id for invoice in hash_group}
                    
                    if invoice_ids_in_id_group.issubset(invoice_ids_in_hash_group):
                        already_covered = True
                        break
                
                if not already_covered:
                    duplicates[f"id:{invoice_id}"] = id_group
        
        return duplicates
    
    def find_duplicate_for_invoice(self, invoice: Invoice) -> Optional[Invoice]:
        """
        Find a duplicate for a specific invoice in the collection.
        
        This method checks if the given invoice is a duplicate of any invoice
        already in the collection.
        
        Args:
            invoice: The invoice to check for duplicates
            
        Returns:
            The first duplicate invoice found, or None if no duplicates are found
        """
        # Check by ID
        if invoice.invoice_id in self._id_index:
            for existing_invoice in self._id_index[invoice.invoice_id]:
                if existing_invoice is not invoice:  # Avoid self-comparison
                    # Verify it's a true duplicate using comparison
                    if is_duplicate(invoice, existing_invoice):
                        return existing_invoice
        
        # Check by hash
        if invoice.invoice_hash in self._hash_index:
            for existing_invoice in self._hash_index[invoice.invoice_hash]:
                if existing_invoice is not invoice:  # Avoid self-comparison
                    return existing_invoice
        
        return None
    
    def get_duplicate_groups(self) -> List[List[Invoice]]:
        """
        Get groups of duplicate invoices.
        
        Returns:
            List of lists, where each inner list contains duplicate invoices
        """
        duplicates = self.find_duplicates()
        return list(duplicates.values())
    
    def _build_indices(self) -> None:
        """Build the ID and hash indices for all invoices."""
        self._id_index = defaultdict(list)
        self._hash_index = defaultdict(list)
        
        for invoice in self.invoices:
            self._add_to_indices(invoice)
    
    def _add_to_indices(self, invoice: Invoice) -> None:
        """
        Add an invoice to the indices.
        
        Args:
            invoice: The invoice to add
        """
        self._id_index[invoice.invoice_id].append(invoice)
        self._hash_index[invoice.invoice_hash].append(invoice)
    
    def _find_duplicates_by_id(self) -> Dict[str, List[Invoice]]:
        """
        Find invoices with duplicate IDs.
        
        Returns:
            Dictionary mapping invoice IDs to lists of invoices with that ID
        """
        return {
            invoice_id: invoices 
            for invoice_id, invoices in self._id_index.items() 
            if len(invoices) > 1
        }
    
    def _find_duplicates_by_hash(self) -> Dict[str, List[Invoice]]:
        """
        Find invoices with duplicate hashes.
        
        Returns:
            Dictionary mapping invoice hashes to lists of invoices with that hash
        """
        return {
            invoice_hash: invoices 
            for invoice_hash, invoices in self._hash_index.items() 
            if len(invoices) > 1
        }


def find_duplicates(invoices: List[Invoice]) -> Dict[str, List[Invoice]]:
    """
    Find duplicate invoices in a list.
    
    This is a convenience function that creates a DuplicateDetector,
    adds the invoices, and returns the duplicate groups.
    
    Args:
        invoices: List of invoices to check for duplicates
        
    Returns:
        Dictionary mapping each duplicate key to a list of duplicate invoices
    """
    detector = DuplicateDetector(invoices)
    return detector.find_duplicates()


def is_duplicate(invoice1: Invoice, invoice2: Invoice) -> bool:
    """
    Check if two invoices are duplicates of each other.
    
    This is a simple wrapper around the invoice_comparison function
    that returns just the boolean result.
    
    Args:
        invoice1: First invoice to compare
        invoice2: Second invoice to compare
        
    Returns:
        True if the invoices are considered duplicates, False otherwise
    """
    comparison = invoice_comparison(invoice1, invoice2)
    return comparison["is_duplicate"]


def find_duplicate_in_list(invoice: Invoice, invoice_list: List[Invoice]) -> Optional[Invoice]:
    """
    Find a duplicate of the given invoice in a list of invoices.
    
    Args:
        invoice: The invoice to check
        invoice_list: List of invoices to check against
        
    Returns:
        The first duplicate invoice found, or None if no duplicates are found
    """
    for existing_invoice in invoice_list:
        if existing_invoice is not invoice:  # Avoid self-comparison
            if is_duplicate(invoice, existing_invoice):
                return existing_invoice
    return None 