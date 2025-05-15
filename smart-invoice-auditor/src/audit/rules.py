"""
Rule-Based Auditing System

This module provides a configurable rule-based system for auditing invoices,
with rules for price verification, date validation, and policy compliance.
"""

import re
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable, Type, Tuple
from abc import ABC, abstractmethod


class AuditResult:
    """Result of an audit rule check"""
    
    def __init__(self, rule_id: str, passed: bool, message: str, severity: str = "medium"):
        """
        Initialize an audit result
        
        Args:
            rule_id: ID of the rule that was checked
            passed: Whether the check passed
            message: Description of the result
            severity: Severity level if failed (low, medium, high)
        """
        self.rule_id = rule_id
        self.passed = passed
        self.message = message
        self.severity = severity
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp
        }


class AuditRule(ABC):
    """Base class for audit rules"""
    
    def __init__(self, rule_id: str, description: str, severity: str = "medium"):
        """
        Initialize an audit rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails (low, medium, high)
        """
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
    
    @abstractmethod
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """
        Check if the invoice passes this rule
        
        Args:
            invoice_data: The invoice data to check
            context: Additional context for the check (e.g., policy data)
            
        Returns:
            AuditResult with the check result
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "type": self.__class__.__name__
        }


class TotalMatchesCalculationRule(AuditRule):
    """Rule to check if invoice total matches calculation from subtotal and tax"""
    
    def __init__(self, rule_id: str = "total_matches_calculation", 
                description: str = "Invoice total should match subtotal + tax",
                severity: str = "medium", tolerance: float = 0.01):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            tolerance: Tolerance for floating point comparison
        """
        super().__init__(rule_id, description, severity)
        self.tolerance = tolerance
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if invoice total matches subtotal + tax"""
        subtotal = invoice_data.get("subtotal", 0.0)
        tax = invoice_data.get("tax", 0.0)
        total = invoice_data.get("total", 0.0)
        
        # Skip check if we don't have all values
        if subtotal == 0.0 or total == 0.0:
            return AuditResult(
                self.rule_id,
                True,
                "Skipped check due to missing values",
                self.severity
            )
        
        expected_total = subtotal + tax
        if abs(expected_total - total) <= self.tolerance:
            return AuditResult(
                self.rule_id,
                True,
                f"Total (${total:.2f}) matches subtotal (${subtotal:.2f}) + tax (${tax:.2f})",
                self.severity
            )
        else:
            return AuditResult(
                self.rule_id,
                False,
                f"Total (${total:.2f}) doesn't match subtotal (${subtotal:.2f}) + tax (${tax:.2f}) = ${expected_total:.2f}",
                self.severity
            )


class LineItemsSumRule(AuditRule):
    """Rule to check if line items sum to subtotal"""
    
    def __init__(self, rule_id: str = "line_items_sum", 
                description: str = "Line items should sum to subtotal",
                severity: str = "medium", tolerance: float = 0.01):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            tolerance: Tolerance for floating point comparison
        """
        super().__init__(rule_id, description, severity)
        self.tolerance = tolerance
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if line items sum to subtotal"""
        subtotal = invoice_data.get("subtotal", 0.0)
        line_items = invoice_data.get("line_items", [])
        
        # Skip check if we don't have line items or subtotal
        if not line_items or subtotal == 0.0:
            return AuditResult(
                self.rule_id,
                True,
                "Skipped check due to missing values",
                self.severity
            )
        
        line_sum = sum(item.get("price", 0.0) * item.get("quantity", 1.0) for item in line_items)
        if abs(line_sum - subtotal) <= self.tolerance:
            return AuditResult(
                self.rule_id,
                True,
                f"Line items sum (${line_sum:.2f}) matches subtotal (${subtotal:.2f})",
                self.severity
            )
        else:
            return AuditResult(
                self.rule_id,
                False,
                f"Line items sum (${line_sum:.2f}) doesn't match subtotal (${subtotal:.2f})",
                self.severity
            )


class DateValidityRule(AuditRule):
    """Rule to check if invoice date is valid"""
    
    def __init__(self, rule_id: str = "date_validity", 
                description: str = "Invoice date should be valid and within acceptable range",
                severity: str = "medium", max_age_days: int = 365, 
                allow_future_days: int = 0):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            max_age_days: Maximum age of invoice in days
            allow_future_days: Number of days in future to allow
        """
        super().__init__(rule_id, description, severity)
        self.max_age_days = max_age_days
        self.allow_future_days = allow_future_days
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if invoice date is valid"""
        date_str = invoice_data.get("date", "")
        
        # Skip check if no date
        if not date_str:
            return AuditResult(
                self.rule_id,
                False,
                "Invoice is missing a date",
                self.severity
            )
        
        try:
            # Parse date
            date_format = "%Y-%m-%d"
            invoice_date = datetime.strptime(date_str, date_format)
            
            # Check if date is too far in the future
            future_limit = datetime.now() + timedelta(days=self.allow_future_days)
            if invoice_date > future_limit:
                return AuditResult(
                    self.rule_id,
                    False,
                    f"Invoice date {date_str} is too far in the future",
                    self.severity
                )
            
            # Check if date is too old
            past_limit = datetime.now() - timedelta(days=self.max_age_days)
            if invoice_date < past_limit:
                return AuditResult(
                    self.rule_id,
                    False,
                    f"Invoice date {date_str} is too old (more than {self.max_age_days} days)",
                    self.severity
                )
            
            return AuditResult(
                self.rule_id,
                True,
                f"Invoice date {date_str} is valid",
                self.severity
            )
        except ValueError:
            return AuditResult(
                self.rule_id,
                False,
                f"Invalid date format: {date_str}. Expected format is YYYY-MM-DD",
                self.severity
            )


class RequiredFieldsRule(AuditRule):
    """Rule to check if invoice has all required fields"""
    
    def __init__(self, rule_id: str = "required_fields", 
                description: str = "Invoice should have all required fields",
                severity: str = "high", 
                required_fields: Optional[List[str]] = None):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            required_fields: List of required field names
        """
        super().__init__(rule_id, description, severity)
        self.required_fields = required_fields or ["invoice_id", "vendor", "date", "total"]
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if invoice has all required fields"""
        missing_fields = []
        
        for field in self.required_fields:
            if field not in invoice_data or not invoice_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return AuditResult(
                self.rule_id,
                False,
                f"Invoice is missing required fields: {', '.join(missing_fields)}",
                self.severity
            )
        else:
            return AuditResult(
                self.rule_id,
                True,
                "Invoice has all required fields",
                self.severity
            )


class MaxAmountRule(AuditRule):
    """Rule to check if invoice total exceeds maximum amount"""
    
    def __init__(self, rule_id: str = "max_amount", 
                description: str = "Invoice total should not exceed maximum amount",
                severity: str = "high", max_amount: float = 5000.0):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            max_amount: Maximum allowed invoice amount
        """
        super().__init__(rule_id, description, severity)
        self.max_amount = max_amount
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if invoice total exceeds maximum amount"""
        total = invoice_data.get("total", 0.0)
        
        # Get max amount from context if provided
        max_amount = self.max_amount
        if context and "policy_data" in context:
            policy_data = context["policy_data"]
            if isinstance(policy_data, dict) and "max_amount" in policy_data:
                max_amount = float(policy_data["max_amount"])
        
        if total > max_amount:
            return AuditResult(
                self.rule_id,
                False,
                f"Invoice total (${total:.2f}) exceeds maximum allowed amount (${max_amount:.2f})",
                self.severity
            )
        else:
            return AuditResult(
                self.rule_id,
                True,
                f"Invoice total (${total:.2f}) is within allowed limit",
                self.severity
            )


class AllowedCategoriesRule(AuditRule):
    """Rule to check if invoice line items have allowed categories"""
    
    def __init__(self, rule_id: str = "allowed_categories", 
                description: str = "Line items should have allowed categories",
                severity: str = "medium", 
                allowed_categories: Optional[List[str]] = None):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            allowed_categories: List of allowed category names
        """
        super().__init__(rule_id, description, severity)
        self.allowed_categories = allowed_categories or []
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if invoice line items have allowed categories"""
        line_items = invoice_data.get("line_items", [])
        
        # Skip check if no line items
        if not line_items:
            return AuditResult(
                self.rule_id,
                True,
                "No line items to check",
                self.severity
            )
        
        # Get allowed categories from context if provided
        allowed_categories = self.allowed_categories
        if context and "policy_data" in context:
            policy_data = context["policy_data"]
            if isinstance(policy_data, dict) and "allowed_categories" in policy_data:
                allowed_categories = policy_data["allowed_categories"]
        
        # Convert to lowercase for case-insensitive comparison
        allowed_categories_lower = [c.lower() for c in allowed_categories]
        
        # Check each line item
        unauthorized_categories = set()
        for item in line_items:
            category = item.get("category", "").lower()
            if category and category not in allowed_categories_lower:
                unauthorized_categories.add(category)
        
        if unauthorized_categories:
            return AuditResult(
                self.rule_id,
                False,
                f"Invoice contains unauthorized categories: {', '.join(unauthorized_categories)}",
                self.severity
            )
        else:
            return AuditResult(
                self.rule_id,
                True,
                "All line item categories are allowed",
                self.severity
            )


class MaxItemPriceRule(AuditRule):
    """Rule to check if line items exceed maximum price for their category"""
    
    def __init__(self, rule_id: str = "max_item_price", 
                description: str = "Line items should not exceed maximum price for their category",
                severity: str = "medium", 
                max_prices: Optional[Dict[str, float]] = None):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            severity: Severity level if rule fails
            max_prices: Dictionary mapping category names to maximum prices
        """
        super().__init__(rule_id, description, severity)
        self.max_prices = max_prices or {}
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check if line items exceed maximum price for their category"""
        line_items = invoice_data.get("line_items", [])
        
        # Skip check if no line items
        if not line_items:
            return AuditResult(
                self.rule_id,
                True,
                "No line items to check",
                self.severity
            )
        
        # Get max prices from context if provided
        max_prices = self.max_prices
        if context and "policy_data" in context:
            policy_data = context["policy_data"]
            if isinstance(policy_data, dict) and "max_item_prices" in policy_data:
                max_prices = policy_data["max_item_prices"]
        
        # Check each line item
        violations = []
        for item in line_items:
            category = item.get("category", "").lower()
            price = item.get("price", 0.0)
            
            if category in max_prices and price > float(max_prices[category]):
                violations.append({
                    "description": item.get("description", "Unknown"),
                    "category": category,
                    "price": price,
                    "max_price": float(max_prices[category])
                })
        
        if violations:
            violation_details = ", ".join([
                f"{v['description']} (${v['price']:.2f} > ${v['max_price']:.2f})"
                for v in violations
            ])
            return AuditResult(
                self.rule_id,
                False,
                f"Line items exceed maximum price for their category: {violation_details}",
                self.severity
            )
        else:
            return AuditResult(
                self.rule_id,
                True,
                "All line items are within price limits for their categories",
                self.severity
            )


class CustomRule(AuditRule):
    """Rule that uses a custom function for checking"""
    
    def __init__(self, rule_id: str, description: str, 
                check_func: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Tuple[bool, str]],
                severity: str = "medium"):
        """
        Initialize the rule
        
        Args:
            rule_id: Unique identifier for the rule
            description: Description of what the rule checks
            check_func: Function that performs the check
            severity: Severity level if rule fails
        """
        super().__init__(rule_id, description, severity)
        self.check_func = check_func
    
    def check(self, invoice_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AuditResult:
        """Check using the custom function"""
        passed, message = self.check_func(invoice_data, context)
        return AuditResult(self.rule_id, passed, message, self.severity)


class RuleRegistry:
    """Registry of available audit rules"""
    
    _rules: Dict[str, Type[AuditRule]] = {
        "total_matches_calculation": TotalMatchesCalculationRule,
        "line_items_sum": LineItemsSumRule,
        "date_validity": DateValidityRule,
        "required_fields": RequiredFieldsRule,
        "max_amount": MaxAmountRule,
        "allowed_categories": AllowedCategoriesRule,
        "max_item_price": MaxItemPriceRule
    }
    
    @classmethod
    def get_rule_class(cls, rule_type: str) -> Optional[Type[AuditRule]]:
        """Get a rule class by type name"""
        return cls._rules.get(rule_type)
    
    @classmethod
    def register_rule(cls, rule_type: str, rule_class: Type[AuditRule]):
        """Register a new rule class"""
        cls._rules[rule_type] = rule_class
    
    @classmethod
    def create_rule(cls, rule_type: str, **kwargs) -> Optional[AuditRule]:
        """Create a rule instance by type name"""
        rule_class = cls.get_rule_class(rule_type)
        if rule_class:
            return rule_class(**kwargs)
        return None
    
    @classmethod
    def list_available_rules(cls) -> List[str]:
        """List all available rule types"""
        return list(cls._rules.keys())


class RuleSet:
    """A set of audit rules to apply to invoices"""
    
    def __init__(self, name: str, description: str = "", rules: Optional[List[AuditRule]] = None):
        """
        Initialize a rule set
        
        Args:
            name: Name of the rule set
            description: Description of the rule set
            rules: List of rules to include
        """
        self.name = name
        self.description = description
        self.rules = rules or []
    
    def add_rule(self, rule: AuditRule):
        """Add a rule to the set"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str):
        """Remove a rule from the set by ID"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
    
    def audit_invoice(self, invoice_data: Dict[str, Any], 
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Audit an invoice using all rules in the set
        
        Args:
            invoice_data: The invoice data to audit
            context: Additional context for the audit
            
        Returns:
            Audit results
        """
        results = []
        
        for rule in self.rules:
            result = rule.check(invoice_data, context)
            results.append(result.to_dict())
        
        # Count results by status
        passed = sum(1 for r in results if r["passed"])
        failed = len(results) - passed
        
        # Count by severity for failed checks
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for result in results:
            if not result["passed"]:
                severity = result["severity"].lower()
                if severity in severity_counts:
                    severity_counts[severity] += 1
        
        return {
            "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
            "ruleset_name": self.name,
            "total_rules": len(self.rules),
            "passed_rules": passed,
            "failed_rules": failed,
            "severity_counts": severity_counts,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule set to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "rules": [rule.to_dict() for rule in self.rules]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleSet':
        """Create a rule set from dictionary representation"""
        name = data.get("name", "Unnamed Rule Set")
        description = data.get("description", "")
        
        rule_set = cls(name, description)
        
        for rule_data in data.get("rules", []):
            rule_type = rule_data.get("type") or rule_data.get("rule_type")
            if not rule_type:
                continue
            
            # Remove type from kwargs
            kwargs = {k: v for k, v in rule_data.items() if k not in ("type", "rule_type")}
            
            rule = RuleRegistry.create_rule(rule_type, **kwargs)
            if rule:
                rule_set.add_rule(rule)
        
        return rule_set
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RuleSet':
        """Create a rule set from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'RuleSet':
        """Create a rule set from YAML string"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    def to_json(self) -> str:
        """Convert rule set to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_yaml(self) -> str:
        """Convert rule set to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False)


class RuleEngine:
    """Engine for applying rule sets to invoices"""
    
    def __init__(self):
        """Initialize the rule engine"""
        self.rule_sets: Dict[str, RuleSet] = {}
    
    def add_rule_set(self, rule_set: RuleSet):
        """Add a rule set to the engine"""
        self.rule_sets[rule_set.name] = rule_set
    
    def remove_rule_set(self, name: str):
        """Remove a rule set from the engine"""
        if name in self.rule_sets:
            del self.rule_sets[name]
    
    def get_rule_set(self, name: str) -> Optional[RuleSet]:
        """Get a rule set by name"""
        return self.rule_sets.get(name)
    
    def list_rule_sets(self) -> List[str]:
        """List all rule set names"""
        return list(self.rule_sets.keys())
    
    def audit_invoice(self, invoice_data: Dict[str, Any], 
                     rule_set_name: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Audit an invoice using a specific rule set or all rule sets
        
        Args:
            invoice_data: The invoice data to audit
            rule_set_name: Name of the rule set to use (or None for all)
            context: Additional context for the audit
            
        Returns:
            Audit results
        """
        if rule_set_name:
            # Use specific rule set
            rule_set = self.get_rule_set(rule_set_name)
            if not rule_set:
                return {
                    "error": f"Rule set '{rule_set_name}' not found",
                    "invoice_id": invoice_data.get("invoice_id", "UNKNOWN")
                }
            
            return rule_set.audit_invoice(invoice_data, context)
        else:
            # Use all rule sets
            all_results = {}
            for name, rule_set in self.rule_sets.items():
                all_results[name] = rule_set.audit_invoice(invoice_data, context)
            
            # Aggregate results
            total_rules = sum(r["total_rules"] for r in all_results.values())
            passed_rules = sum(r["passed_rules"] for r in all_results.values())
            failed_rules = sum(r["failed_rules"] for r in all_results.values())
            
            # Aggregate severity counts
            severity_counts = {"high": 0, "medium": 0, "low": 0}
            for result in all_results.values():
                for severity, count in result["severity_counts"].items():
                    severity_counts[severity] += count
            
            return {
                "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
                "total_rule_sets": len(all_results),
                "total_rules": total_rules,
                "passed_rules": passed_rules,
                "failed_rules": failed_rules,
                "severity_counts": severity_counts,
                "rule_set_results": all_results,
                "timestamp": datetime.now().isoformat()
            }
    
    def load_rule_sets_from_file(self, file_path: str):
        """
        Load rule sets from a JSON or YAML file
        
        Args:
            file_path: Path to the file
        """
        with open(file_path, 'r') as f:
            content = f.read()
            
            if file_path.endswith('.json'):
                data = json.loads(content)
            elif file_path.endswith(('.yml', '.yaml')):
                data = yaml.safe_load(content)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            if isinstance(data, list):
                # List of rule sets
                for rule_set_data in data:
                    rule_set = RuleSet.from_dict(rule_set_data)
                    self.add_rule_set(rule_set)
            elif isinstance(data, dict):
                # Single rule set or dictionary of rule sets
                if "name" in data and "rules" in data:
                    # Single rule set
                    rule_set = RuleSet.from_dict(data)
                    self.add_rule_set(rule_set)
                else:
                    # Dictionary of rule sets
                    for name, rule_set_data in data.items():
                        if isinstance(rule_set_data, dict):
                            rule_set_data["name"] = name
                            rule_set = RuleSet.from_dict(rule_set_data)
                            self.add_rule_set(rule_set)
    
    def save_rule_sets_to_file(self, file_path: str):
        """
        Save all rule sets to a JSON or YAML file
        
        Args:
            file_path: Path to the file
        """
        rule_sets_data = {name: rule_set.to_dict() for name, rule_set in self.rule_sets.items()}
        
        with open(file_path, 'w') as f:
            if file_path.endswith('.json'):
                json.dump(rule_sets_data, f, indent=2)
            elif file_path.endswith(('.yml', '.yaml')):
                yaml.dump(rule_sets_data, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")


# Create default rule sets
def create_default_rule_sets() -> Dict[str, RuleSet]:
    """Create default rule sets"""
    # Basic validation rule set
    basic_validation = RuleSet(
        name="basic_validation",
        description="Basic invoice validation rules"
    )
    basic_validation.add_rule(RequiredFieldsRule())
    basic_validation.add_rule(DateValidityRule())
    basic_validation.add_rule(TotalMatchesCalculationRule())
    
    # Calculation verification rule set
    calculation_verification = RuleSet(
        name="calculation_verification",
        description="Rules for verifying invoice calculations"
    )
    calculation_verification.add_rule(TotalMatchesCalculationRule())
    calculation_verification.add_rule(LineItemsSumRule())
    
    # Policy compliance rule set
    policy_compliance = RuleSet(
        name="policy_compliance",
        description="Rules for checking policy compliance"
    )
    policy_compliance.add_rule(MaxAmountRule())
    policy_compliance.add_rule(AllowedCategoriesRule())
    policy_compliance.add_rule(MaxItemPriceRule())
    
    # Comprehensive audit rule set
    comprehensive_audit = RuleSet(
        name="comprehensive_audit",
        description="Comprehensive invoice audit rules"
    )
    comprehensive_audit.add_rule(RequiredFieldsRule())
    comprehensive_audit.add_rule(DateValidityRule())
    comprehensive_audit.add_rule(TotalMatchesCalculationRule())
    comprehensive_audit.add_rule(LineItemsSumRule())
    comprehensive_audit.add_rule(MaxAmountRule())
    comprehensive_audit.add_rule(AllowedCategoriesRule())
    comprehensive_audit.add_rule(MaxItemPriceRule())
    
    return {
        "basic_validation": basic_validation,
        "calculation_verification": calculation_verification,
        "policy_compliance": policy_compliance,
        "comprehensive_audit": comprehensive_audit
    }