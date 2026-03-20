"""Ablation runner — orchestrate ablation experiments across configurations and models.

The runner does NOT make API calls directly. It uses the provided LLMCaller,
keeping the caller in control of budget and backend choice.

Supports:
- Async execution with semaphore-throttled concurrency
- Cost estimation using ModelRegistry profiles
- Resume from partial runs (skips already-completed combinations)
- Progress callbacks
"""

from __future__ import annotations

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..llm_caller import LLMCaller
from ..registry import ModelRegistry
from .battery import ProbeBattery
from .configuration import AblationConfig
from .probe import Probe, ProbeResult


# ---------------------------------------------------------------------------
# AblationRun
# ---------------------------------------------------------------------------


class AblationRun(BaseModel):
    """State for a complete ablation experiment."""

    id: str = Field(description="Unique run identifier")
    configs: list[AblationConfig] = Field(default_factory=list)
    battery: ProbeBattery
    models: list[str] = Field(description="Model IDs from registry")
    trials_per_probe: int = Field(default=3, ge=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    results: list[ProbeResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def completed_keys(self) -> set[tuple[str, str, str, int]]:
        """Set of (config_id, probe_id, model_id, trial) already completed."""
        return {
            (r.config_id, r.probe_id, r.model_id, r.trial)
            for r in self.results
        }

    def results_for_config(self, config_id: str) -> list[ProbeResult]:
        """All results for a specific configuration."""
        return [r for r in self.results if r.config_id == config_id]

    def results_for_probe(self, probe_id: str) -> list[ProbeResult]:
        """All results for a specific probe."""
        return [r for r in self.results if r.probe_id == probe_id]

    def results_for_model(self, model_id: str) -> list[ProbeResult]:
        """All results for a specific model."""
        return [r for r in self.results if r.model_id == model_id]


# ---------------------------------------------------------------------------
# AblationRunner
# ---------------------------------------------------------------------------


class AblationRunner:
    """Orchestrate ablation experiments with async execution and resume support.

    The runner uses LLMCaller for all API interactions. It never makes
    direct API calls.
    """

    def __init__(
        self,
        caller: LLMCaller,
        registry: ModelRegistry | None = None,
        budget_usd: float | None = None,
    ) -> None:
        """Initialize runner with LLM caller and optional registry.

        Args:
            caller: LLMCaller instance for making API calls.
            registry: Optional ModelRegistry for cost estimation.
            budget_usd: Optional budget ceiling. If set, estimate_cost()
                results are checked before execution.
        """
        self._caller = caller
        self._registry = registry
        self._budget_usd = budget_usd

    async def run_phase(
        self,
        run: AblationRun,
        phase: str,
        *,
        corpus: object,  # PromptCorpus — kept as object to avoid circular import at runtime
        concurrency: int = 5,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> AblationRun:
        """Execute all (config, probe, model, trial) combinations for a phase.

        Uses semaphore for concurrency control. Records all results.
        Supports resume (skips already-completed combinations).

        Args:
            run: The ablation run (configs, battery, models).
            phase: Phase identifier for filtering configs ("baseline",
                "phase0", "phase1", "phase2", "phase3").
            corpus: PromptCorpus for assembling system prompts.
            concurrency: Max concurrent API calls.
            progress_callback: Called with (completed, total) counts.

        Returns:
            The run with results populated.

        Raises:
            ValueError: If budget would be exceeded.
            RuntimeError: If no configs match the phase.
        """
        from ..prompt_blocks import PromptCorpus as _PromptCorpus

        if not isinstance(corpus, _PromptCorpus):
            raise TypeError(
                f"corpus must be a PromptCorpus, got {type(corpus).__name__}"
            )

        # Filter configs for this phase
        phase_configs = [c for c in run.configs if c.phase == phase]
        if not phase_configs:
            raise RuntimeError(
                f"No configs found for phase {phase!r}. "
                f"Available phases: {sorted(set(c.phase for c in run.configs))}"
            )

        # Build work items
        completed = run.completed_keys()
        work_items: list[tuple[AblationConfig, Probe, str, int]] = []

        for config in phase_configs:
            for probe in run.battery.probes:
                for model_id in run.models:
                    for trial in range(run.trials_per_probe):
                        key = (config.id, probe.id, model_id, trial)
                        if key not in completed:
                            work_items.append((config, probe, model_id, trial))

        total = len(work_items) + len(completed)
        done = len(completed)

        if not work_items:
            if progress_callback:
                progress_callback(done, total)
            return run

        # Check budget if set
        if self._budget_usd is not None and self._registry is not None:
            estimated = self.estimate_cost(run)
            total_est = estimated.get("total", 0.0)
            if total_est > self._budget_usd:
                raise ValueError(
                    f"Estimated cost ${total_est:.2f} exceeds budget "
                    f"${self._budget_usd:.2f}. Reduce configs, probes, "
                    f"models, or trials."
                )

        # Record start time
        if "start_time" not in run.metadata:
            run.metadata["start_time"] = datetime.now(timezone.utc).isoformat()

        # Pre-assemble system prompts (avoid repeated assembly)
        prompt_cache: dict[str, str] = {}
        for config in phase_configs:
            if config.id not in prompt_cache:
                prompt_cache[config.id] = config.assemble_prompt(corpus)

        semaphore = asyncio.Semaphore(concurrency)

        async def _execute_one(
            config: AblationConfig,
            probe: Probe,
            model_id: str,
            trial: int,
        ) -> ProbeResult:
            async with semaphore:
                system_prompt = prompt_cache[config.id]
                loop = asyncio.get_event_loop()

                # Make the LLM call with proper system/user separation
                with ThreadPoolExecutor(max_workers=1) as pool:
                    raw_response = await loop.run_in_executor(
                        pool,
                        lambda: self._caller._call_llm_with_system(
                            system_prompt,
                            probe.user_message,
                            temperature=run.temperature,
                        ),
                    )

                # Score the response
                if probe.scoring_method == "llm_judge":
                    # Build judge prompt and run through caller
                    judge_prompt = probe.build_judge_prompt(raw_response)
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        judge_response = await loop.run_in_executor(
                            pool,
                            lambda: self._caller._call_llm(judge_prompt),
                        )
                    score = Probe.parse_judge_score(judge_response)
                    judge_resp_text = judge_response
                else:
                    score = probe.score(raw_response)
                    judge_resp_text = None

                return ProbeResult(
                    config_id=config.id,
                    probe_id=probe.id,
                    model_id=model_id,
                    trial=trial,
                    raw_response=raw_response,
                    score=score,
                    judge_response=judge_resp_text,
                )

        # Execute all work items concurrently
        tasks = [
            _execute_one(config, probe, model_id, trial)
            for config, probe, model_id, trial in work_items
        ]

        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                run.results.append(result)
                self._consecutive_errors = 0
                done += 1
                if progress_callback:
                    progress_callback(done, total)
            except Exception as exc:
                consecutive_errors = getattr(self, "_consecutive_errors", 0) + 1
                self._consecutive_errors = consecutive_errors
                print(
                    f"  warning: ablation probe failed: {exc}",
                    file=sys.stderr,
                )
                done += 1
                if progress_callback:
                    progress_callback(done, total)
                # Fail-stop if all calls are failing (e.g., bad model ID)
                if consecutive_errors >= 5 and done <= consecutive_errors + len(completed):
                    raise RuntimeError(
                        f"First {consecutive_errors} calls all failed. "
                        f"Last error: {exc}"
                    ) from exc

        run.metadata["end_time"] = datetime.now(timezone.utc).isoformat()
        return run

    def estimate_cost(self, run: AblationRun) -> dict[str, float]:
        """Estimate API costs per model and total.

        Uses ModelRegistry cost profiles. Returns dict with per-model
        and total estimates. Unknown-cost models are estimated at $0.03
        per call (conservative upper bound from design doc).

        Args:
            run: The ablation run to estimate costs for.

        Returns:
            Dict mapping model_id -> estimated cost, plus "total" key.
        """
        default_cost_per_call = 0.03  # Conservative upper bound

        n_calls_per_model = (
            len(run.configs) * len(run.battery.probes) * run.trials_per_probe
        )

        # For llm_judge probes, each call requires an additional judge call
        n_judge_probes = sum(
            1 for p in run.battery.probes if p.scoring_method == "llm_judge"
        )
        n_judge_calls_per_model = (
            len(run.configs) * n_judge_probes * run.trials_per_probe
        )

        costs: dict[str, float] = {}

        for model_id in run.models:
            cost_per_call = default_cost_per_call

            if self._registry is not None:
                try:
                    profile = self._registry.get(model_id)
                    estimated = profile.estimated_cost_per_call()
                    if estimated is not None:
                        cost_per_call = estimated
                except KeyError:
                    pass

            model_cost = (
                n_calls_per_model * cost_per_call
                + n_judge_calls_per_model * cost_per_call
            )
            costs[model_id] = model_cost

        costs["total"] = sum(v for k, v in costs.items() if k != "total")
        return costs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_chat_prompt(system_prompt: str, user_message: str) -> str:
    """Build a prompt string that includes the system prompt context.

    The LLMCaller._call_llm takes a single prompt string and sends it
    as a user message. We embed the system prompt as context.

    Note: For production use, the runner should be extended to use
    proper system message API parameters. This is a pragmatic approach
    that works with the existing LLMCaller interface.
    """
    return (
        f"<system>\n{system_prompt}\n</system>\n\n"
        f"<user>\n{user_message}\n</user>"
    )


def save_run(run: AblationRun, path: str | None = None) -> str:
    """Save an ablation run to JSON.

    Args:
        run: The run to save.
        path: Output path. If None, generates from run.id.

    Returns:
        The path where the run was saved.
    """
    from pathlib import Path as _Path

    if path is None:
        path = f"data/ablation/run_{run.id}.json"

    p = _Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        f.write(run.model_dump_json(indent=2))
        f.write("\n")

    return str(p)


def load_run(path: str) -> AblationRun:
    """Load an ablation run from JSON.

    Args:
        path: Path to the JSON file.

    Returns:
        An AblationRun instance.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    import json
    from pathlib import Path as _Path

    p = _Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Run file not found: {path}")

    with open(p) as f:
        data = json.load(f)

    return AblationRun.model_validate(data)
