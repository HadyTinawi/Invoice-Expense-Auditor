"""
Duplicate Invoice Detector

This module provides advanced duplicate detection capabilities for invoices,
using multiple methods including exact matching, fuzzy matching, and similarity scoring.
"""

import hashlib
import difflib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
import pandas as pd
import numpy as np
from collections import defaultdict


class DuplicateDetector:
    """Advanced duplicate detection for invoices"""
    
    def __init__(self, invoice_history: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize the duplicate detector
        
        Args:
            invoice_history: Dictionary of previously processed invoices
        """
        self.invoice_history = invoice_history or {}
        self.invoice_hashes = {}  # Map invoice IDs to their hashes
        self.vendor_invoices = defaultdict(list)  # Group invoices by vendor
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes for faster duplicate detection"""
        for invoice_id, invoice_data in self.invoice_history.items():
            # Store hash
            invoice_hash = self.generate_invoice_hash(invoice_data)
            self.invoice_hashes[invoice_id] = invoice_hash
            
            # Group by vendor
            vendor = invoice_data.get("vendor", "UNKNOWN").lower()
            self.vendor_invoices[vendor].append(invoice_id)
    
    def add_invoice(self, invoice_id: str, invoice_data: Dict[str, Any]) -> None:
        """
        Add an invoice to the history
        
        Args:
            invoice_id: The invoice ID
            invoice_data: The invoice data
        """
        self.invoice_history[invoice_id] = invoice_data
        
        # Update indexes
        invoice_hash = self.generate_invoice_hash(invoice_data)
        self.invoice_hashes[invoice_id] = invoice_hash
        
        vendor = invoice_data.get("vendor", "UNKNOWN").lower()
        self.vendor_invoices[vendor].append(invoice_id)
    
    def generate_invoice_hash(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate a unique hash for an invoice
        
        Args:
            invoice_data: The invoice data to hash
            
        Returns:
            Hash string for the invoice
        """
        # Create a normalized string representation of key invoice data
        hash_input = (
            f"{invoice_data.get('invoice_id', '')}-"
            f"{invoice_data.get('vendor', '').lower()}-"
            f"{invoice_data.get('total', 0.0):.2f}-"
            f"{invoice_data.get('date', '')}"
        )
        
        # Generate hash
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        return hash_value
    
    def check_exact_duplicate(self, invoice_id: str, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an invoice is an exact duplicate
        
        Args:
            invoice_id: The invoice ID
            invoice_data: The invoice data
            
        Returns:
            Result with duplicate status and details
        """
        # Check if we've seen this ID before
        if invoice_id in self.invoice_history:
            return {
                "is_duplicate": True,
                "reason": f"Invoice ID {invoice_id} already exists in the system",
                "duplicate_type": "exact_id_match",
                "confidence": 1.0,
                "matched_invoice_id": invoice_id
            }
        
        # Generate hash and check if we've seen this exact invoice before
        invoice_hash = self.generate_invoice_hash(invoice_data)
        
        for stored_id, stored_hash in self.invoice_hashes.items():
            if stored_hash == invoice_hash:
                return {
                    "is_duplicate": True,
                    "reason": f"Invoice content exactly matches existing invoice {stored_id}",
                    "duplicate_type": "exact_content_match",
                    "confidence": 1.0,
                    "matched_invoice_id": stored_id
                }
        
        return {
            "is_duplicate": False,
            "reason": "No exact duplicates found",
            "confidence": 0.0
        }
    
    def calculate_invoice_similarity(self, invoice1: Dict[str, Any], invoice2: Dict[str, Any]) -> float:
        """
        Calculate similarity score between two invoices (0.0 to 1.0)
        
        Args:
            invoice1: First invoice data
            invoice2: Second invoice data
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Initialize weights for different fields
        weights = {
            "vendor": 0.2,
            "total": 0.3,
            "date": 0.2,
            "line_items": 0.3
        }
        
        scores = {}
        
        # Compare vendor (exact match)
        vendor1 = invoice1.get("vendor", "").lower()
        vendor2 = invoice2.get("vendor", "").lower()
        scores["vendor"] = 1.0 if vendor1 == vendor2 else 0.0
        
        # Compare total (within 1% tolerance)
        total1 = invoice1.get("total", 0.0)
        total2 = invoice2.get("total", 0.0)
        if total1 == 0 and total2 == 0:
            scores["total"] = 1.0
        elif total1 == 0 or total2 == 0:
            scores["total"] = 0.0
        else:
            diff_pct = abs(total1 - total2) / max(total1, total2)
            scores["total"] = 1.0 if diff_pct < 0.01 else max(0.0, 1.0 - diff_pct)
        
        # Compare date (exact match or close)
        date1 = invoice1.get("date", "")
        date2 = invoice2.get("date", "")
        if date1 == date2:
            scores["date"] = 1.0
        elif date1 and date2:
            try:
                # Try to parse dates and check proximity
                date_format = "%Y-%m-%d"
                d1 = datetime.strptime(date1, date_format)
                d2 = datetime.strptime(date2, date_format)
                days_diff = abs((d1 - d2).days)
                scores["date"] = 1.0 if days_diff == 0 else max(0.0, 1.0 - (days_diff / 30))
            except ValueError:
                scores["date"] = 0.0
        else:
            scores["date"] = 0.0
        
        # Compare line items
        line_items1 = invoice1.get("line_items", [])
        line_items2 = invoice2.get("line_items", [])
        
        if not line_items1 and not line_items2:
            scores["line_items"] = 1.0
        elif not line_items1 or not line_items2:
            scores["line_items"] = 0.0
        else:
            # Compare line item counts
            count_similarity = 1.0 - min(1.0, abs(len(line_items1) - len(line_items2)) / max(len(line_items1), len(line_items2)))
            
            # Compare line item content
            item_similarities = []
            for item1 in line_items1:
                best_match = 0.0
                for item2 in line_items2:
                    # Compare description
                    desc1 = item1.get("description", "").lower()
                    desc2 = item2.get("description", "").lower()
                    if desc1 and desc2:
                        desc_sim = difflib.SequenceMatcher(None, desc1, desc2).ratio()
                    else:
                        desc_sim = 0.0
                    
                    # Compare price
                    price1 = item1.get("price", 0.0)
                    price2 = item2.get("price", 0.0)
                    if price1 == 0 and price2 == 0:
                        price_sim = 1.0
                    elif price1 == 0 or price2 == 0:
                        price_sim = 0.0
                    else:
                        price_diff = abs(price1 - price2) / max(price1, price2)
                        price_sim = 1.0 if price_diff < 0.01 else max(0.0, 1.0 - price_diff)
                    
                    # Compare quantity
                    qty1 = item1.get("quantity", 0)
                    qty2 = item2.get("quantity", 0)
                    qty_sim = 1.0 if qty1 == qty2 else 0.0
                    
                    # Overall item similarity
                    item_sim = (desc_sim * 0.5) + (price_sim * 0.3) + (qty_sim * 0.2)
                    best_match = max(best_match, item_sim)
                
                item_similarities.append(best_match)
            
            # Average similarity across all line items
            content_similarity = sum(item_similarities) / len(item_similarities) if item_similarities else 0.0
            
            # Combine count and content similarity
            scores["line_items"] = (count_similarity * 0.3) + (content_similarity * 0.7)
        
        # Calculate weighted average
        weighted_score = sum(scores[key] * weights[key] for key in weights)
        
        return weighted_score
    
    def find_similar_invoices(self, invoice_data: Dict[str, Any], 
                             threshold: float = 0.8, 
                             max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find invoices similar to the given invoice
        
        Args:
            invoice_data: The invoice data to compare against
            threshold: Minimum similarity score (0.0 to 1.0)
            max_results: Maximum number of results to return
            
        Returns:
            List of similar invoices with similarity scores
        """
        results = []
        
        # First, filter by vendor to reduce comparison set
        vendor = invoice_data.get("vendor", "UNKNOWN").lower()
        candidate_ids = self.vendor_invoices.get(vendor, [])
        
        # If no vendor match, check all invoices
        if not candidate_ids:
            candidate_ids = list(self.invoice_history.keys())
        
        # Calculate similarity for each candidate
        for invoice_id in candidate_ids:
            stored_invoice = self.invoice_history[invoice_id]
            
            # Skip if it's the same invoice ID
            if invoice_data.get("invoice_id") == invoice_id:
                continue
            
            # Calculate similarity
            similarity = self.calculate_invoice_similarity(invoice_data, stored_invoice)
            
            if similarity >= threshold:
                results.append({
                    "invoice_id": invoice_id,
                    "similarity": similarity,
                    "invoice_data": stored_invoice
                })
        
        # Sort by similarity (descending) and limit results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]
    
    def check_duplicate(self, invoice_data: Dict[str, Any], 
                       similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Comprehensive duplicate check using multiple methods
        
        Args:
            invoice_data: The invoice data to check
            similarity_threshold: Threshold for considering invoices similar
            
        Returns:
            Result with duplicate status and details
        """
        invoice_id = invoice_data.get("invoice_id", "UNKNOWN")
        
        # First, check for exact duplicates
        exact_check = self.check_exact_duplicate(invoice_id, invoice_data)
        if exact_check["is_duplicate"]:
            return exact_check
        
        # Then, check for similar invoices
        similar_invoices = self.find_similar_invoices(invoice_data, threshold=similarity_threshold)
        
        if similar_invoices:
            best_match = similar_invoices[0]
            return {
                "is_duplicate": True,
                "reason": f"Invoice is very similar to existing invoice {best_match['invoice_id']} (similarity: {best_match['similarity']:.2f})",
                "duplicate_type": "similar_content",
                "confidence": best_match["similarity"],
                "matched_invoice_id": best_match["invoice_id"],
                "similar_invoices": similar_invoices
            }
        
        return {
            "is_duplicate": False,
            "reason": "No duplicates found",
            "confidence": 0.0
        }
    
    def get_duplicate_clusters(self, similarity_threshold: float = 0.8) -> List[List[str]]:
        """
        Group invoices into clusters of potential duplicates
        
        Args:
            similarity_threshold: Threshold for considering invoices similar
            
        Returns:
            List of invoice ID clusters
        """
        # Build similarity matrix
        invoice_ids = list(self.invoice_history.keys())
        n = len(invoice_ids)
        
        if n == 0:
            return []
        
        # Initialize clusters with each invoice in its own cluster
        clusters = [{invoice_id} for invoice_id in invoice_ids]
        
        # Merge clusters based on similarity
        for i in range(n):
            invoice1 = self.invoice_history[invoice_ids[i]]
            
            for j in range(i + 1, n):
                invoice2 = self.invoice_history[invoice_ids[j]]
                
                similarity = self.calculate_invoice_similarity(invoice1, invoice2)
                
                if similarity >= similarity_threshold:
                    # Find clusters containing these invoices
                    cluster_i = None
                    cluster_j = None
                    
                    for k, cluster in enumerate(clusters):
                        if invoice_ids[i] in cluster:
                            cluster_i = k
                        if invoice_ids[j] in cluster:
                            cluster_j = k
                        
                        if cluster_i is not None and cluster_j is not None:
                            break
                    
                    # Merge clusters if they're different
                    if cluster_i != cluster_j:
                        clusters[cluster_i].update(clusters[cluster_j])
                        clusters.pop(cluster_j)
        
        # Convert sets to lists for return
        return [list(cluster) for cluster in clusters if len(cluster) > 1]
    
    def generate_duplicate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report of potential duplicates
        
        Returns:
            Report with duplicate statistics and clusters
        """
        # Get duplicate clusters
        clusters = self.get_duplicate_clusters()
        
        # Calculate statistics
        total_invoices = len(self.invoice_history)
        total_clusters = len(clusters)
        total_duplicates = sum(len(cluster) for cluster in clusters)
        
        # Build detailed cluster information
        cluster_details = []
        for i, cluster in enumerate(clusters):
            cluster_invoices = []
            for invoice_id in cluster:
                invoice_data = self.invoice_history[invoice_id]
                cluster_invoices.append({
                    "invoice_id": invoice_id,
                    "vendor": invoice_data.get("vendor", "UNKNOWN"),
                    "date": invoice_data.get("date", ""),
                    "total": invoice_data.get("total", 0.0)
                })
            
            cluster_details.append({
                "cluster_id": i + 1,
                "size": len(cluster),
                "invoices": cluster_invoices
            })
        
        return {
            "total_invoices": total_invoices,
            "total_duplicate_clusters": total_clusters,
            "total_potential_duplicates": total_duplicates,
            "duplicate_percentage": (total_duplicates / total_invoices) * 100 if total_invoices > 0 else 0,
            "clusters": cluster_details
        }