"""SESP self-evolution core."""
from .apply_evolution import apply_proposal
from . import proposal_schema

__all__ = ["apply_proposal", "proposal_schema"]
