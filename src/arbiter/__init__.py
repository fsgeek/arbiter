"""Arbiter — three-tier evaluation framework for LLM conflict detection."""

__version__ = "0.1.0"

from .block_evaluator import BlockEvaluator, BlockScore
from .decision_policy import DecisionPolicyConfig, DeterministicDecisionPolicy
from .decomposer import Decomposer, DecompositionError
from .episode import DeclaredLoss, Episode, EpisodeStore, TensorAnchor
from .heuristic_decomposer import heuristic_decompose
from .llm_caller import LLMCaller
from .interference_tensor import (
    AdjudicationDecision,
    DrafterIdentity,
    InterferenceTensor,
    TensorDeclaredLoss,
    TensorEntry,
    TensorEntryV2,
)
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
