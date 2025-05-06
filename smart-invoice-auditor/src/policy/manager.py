"""
Policy Management Module

This module handles the storage, retrieval, and application of vendor policies
for invoice auditing.
"""

import os
import csv
import json
from typing import Dict, Any, List, Optional
import pandas as pd


class PolicyManager:
    """Manager for vendor policies"""
    
    def __init__(self, policy_dir: Optional[str] = None):
        """
        Initialize the policy manager
        
        Args:
            policy_dir: Directory containing policy files
        """
        self.policy_dir = policy_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                    "data", "policies")
        self.policies = {}
        self._load_policies()
    
    def _load_policies(self):
        """Load all policies from the policy directory"""
        if not os.path.exists(self.policy_dir):
            os.makedirs(self.policy_dir, exist_ok=True)
            return
        
        for filename in os.listdir(self.policy_dir):
            if filename.endswith('.csv'):
                vendor_name = os.path.splitext(filename)[0]
                policy_path = os.path.join(self.policy_dir, filename)
                self.policies[vendor_name] = self._load_csv_policy(policy_path)
            elif filename.endswith('.json'):
                vendor_name = os.path.splitext(filename)[0]
                policy_path = os.path.join(self.policy_dir, filename)
                self.policies[vendor_name] = self._load_json_policy(policy_path)
    
    def _load_csv_policy(self, policy_path: str) -> Dict[str, Any]:
        """Load a policy from a CSV file"""
        try:
            df = pd.read_csv(policy_path)
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Error loading policy from {policy_path}: {e}")
            return {}
    
    def _load_json_policy(self, policy_path: str) -> Dict[str, Any]:
        """Load a policy from a JSON file"""
        try:
            with open(policy_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading policy from {policy_path}: {e}")
            return {}
    
    def get_policy(self, vendor_name: str) -> Dict[str, Any]:
        """
        Get policy for a specific vendor
        
        Args:
            vendor_name: Name of the vendor
            
        Returns:
            Policy data for the vendor
        """
        return self.policies.get(vendor_name, {})
    
    def add_policy(self, vendor_name: str, policy_data: Dict[str, Any], file_format: str = 'csv'):
        """
        Add or update a vendor policy
        
        Args:
            vendor_name: Name of the vendor
            policy_data: Policy data to add
            file_format: Format to save the policy (csv or json)
        """
        self.policies[vendor_name] = policy_data
        
        # Save to file
        if file_format.lower() == 'csv':
            self._save_csv_policy(vendor_name, policy_data)
        elif file_format.lower() == 'json':
            self._save_json_policy(vendor_name, policy_data)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
    
    def _save_csv_policy(self, vendor_name: str, policy_data: Dict[str, Any]):
        """Save a policy to a CSV file"""
        if not os.path.exists(self.policy_dir):
            os.makedirs(self.policy_dir, exist_ok=True)
        
        policy_path = os.path.join(self.policy_dir, f"{vendor_name}.csv")
        df = pd.DataFrame(policy_data)
        df.to_csv(policy_path, index=False)
    
    def _save_json_policy(self, vendor_name: str, policy_data: Dict[str, Any]):
        """Save a policy to a JSON file"""
        if not os.path.exists(self.policy_dir):
            os.makedirs(self.policy_dir, exist_ok=True)
        
        policy_path = os.path.join(self.policy_dir, f"{vendor_name}.json")
        with open(policy_path, 'w') as f:
            json.dump(policy_data, f, indent=2)
    
    def list_vendors(self) -> List[str]:
        """List all vendors with policies"""
        return list(self.policies.keys())