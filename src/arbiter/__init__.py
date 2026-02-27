"""Arbiter — three-tier evaluation framework for LLM conflict detection."""

__version__ = "0.1.0"

from .block_evaluator import BlockEvaluator, BlockScore
from .decomposer import Decomposer, DecompositionError
from .interference_tensor import InterferenceTensor, TensorEntry
from .pipeline import AnalysisResult, PromptAnalyzer
from .prompt_blocks import (
    BlockCategory,
    InterferencePattern,
    InterferenceType,
    Modality,
    PromptBlock,
    PromptCorpus,
    Severity,
    Tier,
)
from .registry import DomainScore, ModelProfile, ModelRegistry, Provider
from .rules import (
    BUILTIN_RULES,
    CompilationError,
    CompiledRuleSet,
    EvaluationRule,
    RuleSet,
    default_ruleset,
)
