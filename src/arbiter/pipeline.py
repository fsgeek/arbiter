"""Analysis pipeline — end-to-end prompt interference analysis.

Orchestrates: decompose → evaluate → assemble → summarize.

The pipeline supports two modes:
1. Structural-only: fast, no API calls, catches verbatim duplication and
   priority marker ambiguity. Good for CI or first-pass screening.
2. Full analysis: includes LLM-based evaluation for semantic interference
   (mandate/prohibition conflicts, scope overlaps, implicit dependencies).
   Requires an LLM backend and costs money.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .block_evaluator import BlockEvaluator, BlockScore
from .decomposer import Decomposer
from .interference_tensor import InterferenceTensor
from .prompt_blocks import PromptBlock
from .rules import CompiledRuleSet


class AnalysisResult(BaseModel):
    """Full pipeline output."""

    blocks: list[PromptBlock]
    tensor: InterferenceTensor
    score: float = Field(description="Summary interference score (0-1)")
    summary: str = Field(description="Human-readable report")


class PromptAnalyzer:
    """End-to-end prompt interference analyzer.

    Usage:
        rule_set = default_ruleset().compile()
        analyzer = PromptAnalyzer(rule_set)

        # Structural-only (fast, no API)
        result = analyzer.analyze_structural(blocks)

        # Full analysis requires the caller to run LLM calls
        # (because the caller controls the LLM backend and budget)
        pending = analyzer.pending_llm_work(blocks)
        llm_scores = [... run LLM calls ...]
        result = analyzer.analyze_with_scores(blocks, llm_scores)
    """

    def __init__(self, rule_set: CompiledRuleSet) -> None:
        self._rule_set = rule_set
        self._decomposer = Decomposer(rule_set)
        self._evaluator = BlockEvaluator(structural_only=False)
        self._structural_evaluator = BlockEvaluator(structural_only=True)

    @property
    def decomposer(self) -> Decomposer:
        """Access the decomposer for building prompts / parsing responses."""
        return self._decomposer

    @property
    def evaluator(self) -> BlockEvaluator:
        """Access the block evaluator for building LLM prompts / parsing responses."""
        return self._evaluator

    def analyze_structural(
        self,
        blocks: list[PromptBlock],
        *,
        threshold: float = 0.0,
    ) -> AnalysisResult:
        """Structural-only analysis. No API calls, runs in milliseconds.

        Catches verbatim duplication and priority marker ambiguity.
        Does not catch semantic interference (mandate/prohibition, scope
        overlap, implicit dependencies).
        """
        scores = self._structural_evaluator.evaluate_all_structural(
            blocks, self._rule_set
        )
        tensor = self._structural_evaluator.assemble_tensor(
            blocks, self._rule_set, scores, threshold=threshold
        )
        return AnalysisResult(
            blocks=blocks,
            tensor=tensor,
            score=tensor.summary_score(),
            summary=tensor.summary_report(),
        )

    def pending_llm_work(
        self, blocks: list[PromptBlock]
    ) -> list[tuple[PromptBlock, PromptBlock, object, str]]:
        """Return all (block_a, block_b, rule, prompt) tuples needing LLM evaluation.

        The caller runs the LLM calls through their preferred backend,
        then passes the resulting BlockScores to analyze_with_scores().
        """
        return self._evaluator.pending_llm_evaluations(blocks, self._rule_set)

    def analyze_with_scores(
        self,
        blocks: list[PromptBlock],
        llm_scores: list[BlockScore],
        *,
        threshold: float = 0.0,
    ) -> AnalysisResult:
        """Full analysis with both structural and LLM scores.

        Args:
            blocks: The decomposed prompt blocks.
            llm_scores: BlockScores from LLM evaluation (caller runs the calls).
            threshold: Minimum score to include in the tensor.
        """
        structural_scores = self._evaluator.evaluate_all_structural(
            blocks, self._rule_set
        )
        all_scores = structural_scores + llm_scores

        tensor = self._evaluator.assemble_tensor(
            blocks, self._rule_set, all_scores, threshold=threshold
        )
        return AnalysisResult(
            blocks=blocks,
            tensor=tensor,
            score=tensor.summary_score(),
            summary=tensor.summary_report(),
        )
