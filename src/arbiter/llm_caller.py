"""LLM caller — adapter that bridges prompt builders with evaluator backends.

This is the only module that makes API calls for the decomposer and block
evaluator pipelines. Everything else builds prompts and parses responses
but never calls an LLM directly. The caller bridges the gap.

Usage:
    from arbiter.evaluator import OpenAICompatibleEvaluator
    from arbiter.llm_caller import LLMCaller

    evaluator = OpenAICompatibleEvaluator(
        model="anthropic/claude-haiku-4-5-20251001",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    caller = LLMCaller(evaluator)
    blocks = await caller.decompose(text, source, rule_set)
    llm_scores = await caller.evaluate_llm_rules(blocks, rule_set)
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from .block_evaluator import BlockEvaluator, BlockScore
from .decomposer import Decomposer
from .prompt_blocks import PromptBlock
from .rules import CompiledRuleSet


class LLMCaller:
    """Adapter that runs decomposer and block evaluator prompts through LLM backends.

    Uses the OpenAI-compatible chat completions API through the evaluator's
    internal client. This keeps all API calls in one place.
    """

    def __init__(
        self,
        client,  # openai.OpenAI instance
        model: str,
        *,
        max_concurrent: int = 5,
    ) -> None:
        self._client = client
        self._model = model
        self._max_concurrent = max_concurrent

    def _call_llm(self, prompt: str, *, max_tokens: int = 4096) -> str:
        """Make a single synchronous LLM call. Returns raw response text."""
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    async def decompose(
        self, text: str, source: str, rule_set: CompiledRuleSet
    ) -> list[PromptBlock]:
        """Run LLM decomposition: build prompt -> call LLM -> parse response."""
        decomposer = Decomposer(rule_set)
        prompt = decomposer.build_prompt(text)

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            raw = await loop.run_in_executor(
                pool, lambda: self._call_llm(prompt, max_tokens=8192)
            )

        return decomposer.parse_response(raw, source)

    async def evaluate_llm_rules(
        self,
        blocks: list[PromptBlock],
        rule_set: CompiledRuleSet,
    ) -> list[BlockScore]:
        """Run all pending LLM evaluations concurrently.

        Returns a list of BlockScores from LLM evaluation.
        """
        evaluator = BlockEvaluator(structural_only=False)
        pending = evaluator.pending_llm_evaluations(blocks, rule_set)

        if not pending:
            return []

        loop = asyncio.get_event_loop()
        scores: list[BlockScore] = []

        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def _eval_one(block_a, block_b, rule, prompt):
            async with semaphore:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    raw = await loop.run_in_executor(
                        pool, lambda: self._call_llm(prompt)
                    )
                return evaluator.parse_llm_score(raw, block_a, block_b, rule)

        tasks = [
            _eval_one(block_a, block_b, rule, prompt)
            for block_a, block_b, rule, prompt in pending
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BlockScore):
                scores.append(result)
            elif isinstance(result, Exception):
                # Log but don't crash — partial results are better than none
                import sys
                print(f"  warning: LLM evaluation failed: {result}", file=sys.stderr)

        return scores
