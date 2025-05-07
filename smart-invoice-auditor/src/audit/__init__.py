"""
Audit Package for Smart Invoice Auditor

This package provides rule-based auditing capabilities for invoices,
including configurable rules for price verification, date validation,
and policy compliance.
"""

from .rules import (
    AuditResult,
    AuditRule,
    TotalMatchesCalculationRule,
    LineItemsSumRule,
    DateValidityRule,
    RequiredFieldsRule,
    MaxAmountRule,
    AllowedCategoriesRule,
    MaxItemPriceRule,
    CustomRule,
    RuleRegistry,
    RuleSet,
    RuleEngine,
    create_default_rule_sets
)

__all__ = [
    'AuditResult',
    'AuditRule',
    'TotalMatchesCalculationRule',
    'LineItemsSumRule',
    'DateValidityRule',
    'RequiredFieldsRule',
    'MaxAmountRule',
    'AllowedCategoriesRule',
    'MaxItemPriceRule',
    'CustomRule',
    'RuleRegistry',
    'RuleSet',
    'RuleEngine',
    'create_default_rule_sets'
]