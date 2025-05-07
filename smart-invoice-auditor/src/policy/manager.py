"""
Policy Management Module

This module handles the storage, retrieval, and application of vendor policies
for invoice auditing. It provides capabilities to check invoices against policies
and identify violations.
"""

import os
import csv
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd


class PolicyViolation:
    """Represents a policy violation found during invoice checking"""
    
    def __init__(self, rule_id: str, description: str, severity: str = "medium",
                 affected_items: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize a policy violation
        
        Args:
            rule_id: Identifier for the violated rule
            description: Description of the violation
            severity: Severity level (low, medium, high)
            affected_items: List of affected line items
        """
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
        self.affected_items = affected_items or []
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "affected_items": self.affected_items,
            "timestamp": self.timestamp
        }


class PolicyRule:
    """Represents a policy rule that can be checked against invoices"""
    
    def __init__(self, rule_id: str, rule_type: str, parameters: Dict[str, Any],
                 description: str, severity: str = "medium"):
        """
        Initialize a policy rule
        
        Args:
            rule_id: Unique identifier for the rule
            rule_type: Type of rule (e.g., max_amount, allowed_category)
            parameters: Parameters for the rule
            description: Description of the rule
            severity: Severity if violated (low, medium, high)
        """
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.parameters = parameters
        self.description = description
        self.severity = severity
    
    def check(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """
        Check if the invoice violates this rule
        
        Args:
            invoice_data: The invoice data to check
            
        Returns:
            PolicyViolation if rule is violated, None otherwise
        """
        if self.rule_type == "max_amount":
            return self._check_max_amount(invoice_data)
        elif self.rule_type == "allowed_categories":
            return self._check_allowed_categories(invoice_data)
        elif self.rule_type == "max_item_price":
            return self._check_max_item_price(invoice_data)
        elif self.rule_type == "required_fields":
            return self._check_required_fields(invoice_data)
        elif self.rule_type == "date_range":
            return self._check_date_range(invoice_data)
        elif self.rule_type == "regex_match":
            return self._check_regex_match(invoice_data)
        return None
    
    def _check_max_amount(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check if invoice total exceeds maximum amount"""
        max_amount = float(self.parameters.get("max_amount", 0))
        total = invoice_data.get("total", 0.0)
        
        if total > max_amount:
            return PolicyViolation(
                self.rule_id,
                f"Invoice total (${total:.2f}) exceeds maximum allowed amount (${max_amount:.2f})",
                self.severity
            )
        return None
    
    def _check_allowed_categories(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check if all line items have allowed categories"""
        allowed_categories = [c.lower() for c in self.parameters.get("allowed_categories", [])]
        line_items = invoice_data.get("line_items", [])
        
        violations = []
        for item in line_items:
            category = item.get("category", "").lower()
            if category and category not in allowed_categories:
                violations.append(item)
        
        if violations:
            categories = ", ".join(set(item.get("category", "") for item in violations))
            return PolicyViolation(
                self.rule_id,
                f"Invoice contains unauthorized categories: {categories}",
                self.severity,
                violations
            )
        return None
    
    def _check_max_item_price(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check if any line items exceed maximum price for their category"""
        max_prices = self.parameters.get("max_item_prices", {})
        line_items = invoice_data.get("line_items", [])
        
        violations = []
        for item in line_items:
            category = item.get("category", "").lower()
            price = item.get("price", 0.0)
            
            if category in max_prices and price > float(max_prices[category]):
                violations.append(item)
        
        if violations:
            return PolicyViolation(
                self.rule_id,
                f"Invoice contains items that exceed maximum price for their category",
                self.severity,
                violations
            )
        return None
    
    def _check_required_fields(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check if invoice has all required fields"""
        required_fields = self.parameters.get("required_fields", [])
        missing_fields = []
        
        for field in required_fields:
            if field not in invoice_data or not invoice_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return PolicyViolation(
                self.rule_id,
                f"Invoice is missing required fields: {', '.join(missing_fields)}",
                self.severity
            )
        return None
    
    def _check_date_range(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check if invoice date is within allowed range"""
        date_str = invoice_data.get("date", "")
        if not date_str:
            return None
        
        try:
            date_format = "%Y-%m-%d"
            invoice_date = datetime.strptime(date_str, date_format)
            
            min_date_str = self.parameters.get("min_date")
            max_date_str = self.parameters.get("max_date")
            
            if min_date_str:
                min_date = datetime.strptime(min_date_str, date_format)
                if invoice_date < min_date:
                    return PolicyViolation(
                        self.rule_id,
                        f"Invoice date {date_str} is before minimum allowed date {min_date_str}",
                        self.severity
                    )
            
            if max_date_str:
                max_date = datetime.strptime(max_date_str, date_format)
                if invoice_date > max_date:
                    return PolicyViolation(
                        self.rule_id,
                        f"Invoice date {date_str} is after maximum allowed date {max_date_str}",
                        self.severity
                    )
        except ValueError:
            return PolicyViolation(
                self.rule_id,
                f"Invoice has invalid date format: {date_str}",
                self.severity
            )
        
        return None
    
    def _check_regex_match(self, invoice_data: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check if specified field matches regex pattern"""
        field = self.parameters.get("field", "")
        pattern = self.parameters.get("pattern", "")
        
        if not field or not pattern or field not in invoice_data:
            return None
        
        value = str(invoice_data[field])
        if not re.match(pattern, value):
            return PolicyViolation(
                self.rule_id,
                f"Field '{field}' with value '{value}' does not match required pattern",
                self.severity
            )
        
        return None
    
    @classmethod
    def from_dict(cls, rule_dict: Dict[str, Any]) -> 'PolicyRule':
        """Create a rule from dictionary representation"""
        return cls(
            rule_id=rule_dict.get("rule_id", "unknown"),
            rule_type=rule_dict.get("rule_type", "unknown"),
            parameters=rule_dict.get("parameters", {}),
            description=rule_dict.get("description", ""),
            severity=rule_dict.get("severity", "medium")
        )


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
        self.rules_by_vendor = {}
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
                self._create_rules_from_policy(vendor_name, self.policies[vendor_name])
            elif filename.endswith('.json'):
                vendor_name = os.path.splitext(filename)[0]
                policy_path = os.path.join(self.policy_dir, filename)
                self.policies[vendor_name] = self._load_json_policy(policy_path)
                self._create_rules_from_policy(vendor_name, self.policies[vendor_name])
            elif filename.endswith('.txt'):
                vendor_name = os.path.splitext(filename)[0]
                policy_path = os.path.join(self.policy_dir, filename)
                self.policies[vendor_name] = self._load_txt_policy(policy_path)
                self._create_rules_from_policy(vendor_name, self.policies[vendor_name])
    
    def _create_rules_from_policy(self, vendor_name: str, policy_data: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """Create rules from policy data"""
        rules = []
        
        # Handle different policy data formats
        if isinstance(policy_data, list):
            # List of records (from CSV)
            for i, record in enumerate(policy_data):
                if "rule_type" in record:
                    # This is already a rule definition
                    rule = PolicyRule.from_dict(record)
                    rules.append(rule)
        elif isinstance(policy_data, dict):
            # JSON format
            if "rules" in policy_data:
                # Explicit rules array
                for rule_data in policy_data["rules"]:
                    rule = PolicyRule.from_dict(rule_data)
                    rules.append(rule)
            else:
                # Convert policy elements to rules
                if "max_amount" in policy_data:
                    rules.append(PolicyRule(
                        rule_id=f"{vendor_name}_max_amount",
                        rule_type="max_amount",
                        parameters={"max_amount": policy_data["max_amount"]},
                        description=f"Maximum invoice amount for {vendor_name}",
                        severity="high"
                    ))
                
                if "allowed_categories" in policy_data:
                    rules.append(PolicyRule(
                        rule_id=f"{vendor_name}_allowed_categories",
                        rule_type="allowed_categories",
                        parameters={"allowed_categories": policy_data["allowed_categories"]},
                        description=f"Allowed expense categories for {vendor_name}",
                        severity="medium"
                    ))
                
                if "max_item_prices" in policy_data:
                    rules.append(PolicyRule(
                        rule_id=f"{vendor_name}_max_item_prices",
                        rule_type="max_item_price",
                        parameters={"max_item_prices": policy_data["max_item_prices"]},
                        description=f"Maximum prices by category for {vendor_name}",
                        severity="medium"
                    ))
                
                if "required_fields" in policy_data:
                    rules.append(PolicyRule(
                        rule_id=f"{vendor_name}_required_fields",
                        rule_type="required_fields",
                        parameters={"required_fields": policy_data["required_fields"]},
                        description=f"Required invoice fields for {vendor_name}",
                        severity="medium"
                    ))
        
        self.rules_by_vendor[vendor_name] = rules
    
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
    
    def _load_txt_policy(self, policy_path: str) -> Dict[str, Any]:
        """Load a policy from a TXT file with key=value format"""
        policy_data = {}
        try:
            with open(policy_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Try to convert to appropriate type
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        elif value.replace('.', '', 1).isdigit():
                            value = float(value) if '.' in value else int(value)
                        elif value.startswith('[') and value.endswith(']'):
                            # Simple list parsing
                            items = value[1:-1].split(',')
                            value = [item.strip() for item in items]
                        
                        policy_data[key] = value
        except Exception as e:
            print(f"Error loading policy from {policy_path}: {e}")
        
        return policy_data
    
    def get_policy(self, vendor_name: str) -> Dict[str, Any]:
        """
        Get policy for a specific vendor
        
        Args:
            vendor_name: Name of the vendor
            
        Returns:
            Policy data for the vendor
        """
        return self.policies.get(vendor_name, {})
    
    def add_policy(self, vendor_name: str, policy_data: Dict[str, Any], file_format: str = 'json'):
        """
        Add or update a vendor policy
        
        Args:
            vendor_name: Name of the vendor
            policy_data: Policy data to add
            file_format: Format to save the policy (csv, json, or txt)
        """
        self.policies[vendor_name] = policy_data
        
        # Create rules from policy
        self._create_rules_from_policy(vendor_name, policy_data)
        
        # Save to file
        if file_format.lower() == 'csv':
            self._save_csv_policy(vendor_name, policy_data)
        elif file_format.lower() == 'json':
            self._save_json_policy(vendor_name, policy_data)
        elif file_format.lower() == 'txt':
            self._save_txt_policy(vendor_name, policy_data)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
    
    def _save_csv_policy(self, vendor_name: str, policy_data: Dict[str, Any]):
        """Save a policy to a CSV file"""
        if not os.path.exists(self.policy_dir):
            os.makedirs(self.policy_dir, exist_ok=True)
        
        policy_path = os.path.join(self.policy_dir, f"{vendor_name}.csv")
        df = pd.DataFrame(policy_data if isinstance(policy_data, list) else [policy_data])
        df.to_csv(policy_path, index=False)
    
    def _save_json_policy(self, vendor_name: str, policy_data: Dict[str, Any]):
        """Save a policy to a JSON file"""
        if not os.path.exists(self.policy_dir):
            os.makedirs(self.policy_dir, exist_ok=True)
        
        policy_path = os.path.join(self.policy_dir, f"{vendor_name}.json")
        with open(policy_path, 'w') as f:
            json.dump(policy_data, f, indent=2)
    
    def _save_txt_policy(self, vendor_name: str, policy_data: Dict[str, Any]):
        """Save a policy to a TXT file with key=value format"""
        if not os.path.exists(self.policy_dir):
            os.makedirs(self.policy_dir, exist_ok=True)
        
        policy_path = os.path.join(self.policy_dir, f"{vendor_name}.txt")
        with open(policy_path, 'w') as f:
            f.write(f"# Policy for {vendor_name}\n")
            f.write(f"# Generated on {datetime.now().isoformat()}\n\n")
            
            for key, value in policy_data.items():
                if isinstance(value, list):
                    value_str = f"[{', '.join(str(item) for item in value)}]"
                else:
                    value_str = str(value)
                
                f.write(f"{key} = {value_str}\n")
    
    def list_vendors(self) -> List[str]:
        """List all vendors with policies"""
        return list(self.policies.keys())
    
    def check_invoice(self, invoice_data: Dict[str, Any], vendor_name: Optional[str] = None) -> List[PolicyViolation]:
        """
        Check if an invoice violates any policies
        
        Args:
            invoice_data: The invoice data to check
            vendor_name: Optional vendor name to use specific policy
                         If not provided, will use vendor from invoice data
            
        Returns:
            List of policy violations found
        """
        # Determine vendor name
        if not vendor_name:
            vendor_name = invoice_data.get("vendor", "")
        
        if not vendor_name or vendor_name not in self.rules_by_vendor:
            return []
        
        # Check each rule for the vendor
        violations = []
        for rule in self.rules_by_vendor[vendor_name]:
            violation = rule.check(invoice_data)
            if violation:
                violations.append(violation)
        
        return violations
    
    def check_invoice_compliance(self, invoice_data: Dict[str, Any],
                                vendor_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if an invoice complies with policies and return detailed results
        
        Args:
            invoice_data: The invoice data to check
            vendor_name: Optional vendor name to use specific policy
            
        Returns:
            Compliance check results
        """
        # Get violations
        violations = self.check_invoice(invoice_data, vendor_name)
        
        # Determine vendor name
        if not vendor_name:
            vendor_name = invoice_data.get("vendor", "")
        
        # Format results
        result = {
            "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
            "vendor": vendor_name,
            "compliant": len(violations) == 0,
            "violations": [v.to_dict() for v in violations],
            "violation_count": len(violations),
            "checked_at": datetime.now().isoformat()
        }
        
        # Add severity counts
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for violation in violations:
            severity = violation.severity.lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        result["severity_counts"] = severity_counts
        
        return result
    
    def add_rule(self, vendor_name: str, rule: PolicyRule):
        """
        Add a rule to a vendor's policy
        
        Args:
            vendor_name: Name of the vendor
            rule: The rule to add
        """
        if vendor_name not in self.rules_by_vendor:
            self.rules_by_vendor[vendor_name] = []
        
        self.rules_by_vendor[vendor_name].append(rule)
        
        # Update the policy data if it exists
        if vendor_name in self.policies:
            policy_data = self.policies[vendor_name]
            
            if isinstance(policy_data, dict):
                if "rules" not in policy_data:
                    policy_data["rules"] = []
                
                policy_data["rules"].append({
                    "rule_id": rule.rule_id,
                    "rule_type": rule.rule_type,
                    "parameters": rule.parameters,
                    "description": rule.description,
                    "severity": rule.severity
                })
                
                # Save the updated policy
                self._save_json_policy(vendor_name, policy_data)