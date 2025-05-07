#!/usr/bin/env python3
"""
Test script to verify that all modules can be imported correctly.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Importing modules...")
    
    # Import from audit module
    from smart_invoice_auditor.src.audit.rules import (
        AuditResult,
        AuditRule,
        RuleEngine,
        create_default_rule_sets
    )
    print("✓ Successfully imported audit.rules")
    
    # Import from agent module
    from smart_invoice_auditor.src.agent.auditor import AuditorAgent
    print("✓ Successfully imported agent.auditor")
    
    # Import from policy module
    from smart_invoice_auditor.src.policy.manager import PolicyManager
    print("✓ Successfully imported policy.manager")
    
    # Import from ocr module
    from smart_invoice_auditor.src.ocr.processor import create_processor
    print("✓ Successfully imported ocr.processor")
except ImportError:
    print("Trying alternative import paths...")
    
    try:
        # Import from audit module
        from src.audit.rules import (
            AuditResult,
            AuditRule,
            RuleEngine,
            create_default_rule_sets
        )
        print("✓ Successfully imported audit.rules")
        
        # Import from agent module
        from src.agent.auditor import AuditorAgent
        print("✓ Successfully imported agent.auditor")
        
        # Import from policy module
        from src.policy.manager import PolicyManager
        print("✓ Successfully imported policy.manager")
        
        # Import from ocr module
        from src.ocr.processor import create_processor
        print("✓ Successfully imported ocr.processor")
    except ImportError as e:
        print(f"Alternative import paths also failed: {e}")
        print("\nImport test failed!")
        sys.exit(1)
    else:
        print("\nAll imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    
    # Print Python path for debugging
    print("\nPython path:")
    for path in sys.path:
        print(f"  {path}")