"""
Reporting Package for Smart Invoice Auditor

This package provides reporting capabilities for audit results,
including detailed reports with explanations for each flagged issue.
"""

from .report_generator import (
    ReportGenerator,
    ReportFormat,
    generate_report
)

__all__ = [
    'ReportGenerator',
    'ReportFormat',
    'generate_report'
]