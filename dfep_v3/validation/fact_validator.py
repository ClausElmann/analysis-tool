"""
dfep_v3/validation/fact_validator.py

Re-uses v2 fact validator (GOLD — no changes needed).
The validator verifies that AI-produced capabilities are grounded in extracted facts.
"""

from dfep_v2.validation.fact_validator import FactValidator, ValidationResult

__all__ = ["FactValidator", "ValidationResult"]
