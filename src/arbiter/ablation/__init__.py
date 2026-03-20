"""Ablation evaluation framework — systematic measurement of block-level behavioral effects.

Removes or modifies blocks from a decomposed system prompt, runs behavioral
probes against each configuration, and assembles the results into an
interference tensor that reveals which blocks interact, which are dead,
which are load-bearing, and which actively suppress other blocks.

Usage:
    from arbiter.ablation import (
        # Covering arrays
        generate_covering_array, verify_coverage,
        # Configuration
        AblationConfig, build_phase0_configs, build_phase1_configs,
        build_phase2_configs, build_phase3_configs,
        # Probes
        Probe, ProbeResult, ProbeBattery,
        # Probe generation
        build_generation_prompt, parse_generated_probe,
        # Execution
        AblationRun, AblationRunner,
        # Tensor
        AblationScore, AblationTensor,
        # Analysis
        BlockClassification, CompetitionPattern,
        classify_blocks, detect_competition_patterns,
        detect_suppression, generate_report,
    )
"""

from .analysis import (
    BlockClassification,
    CompetitionPattern,
    classify_blocks,
    detect_competition_patterns,
    detect_suppression,
    generate_report,
)
from .battery import ProbeBattery, load_battery, save_battery
from .configuration import (
    AblationConfig,
    build_baseline_config,
    build_phase0_configs,
    build_phase1_configs,
    build_phase2_configs,
    build_phase3_configs,
)
from .covering_array import (
    generate_covering_array,
    load_covering_array,
    save_covering_array,
    verify_coverage,
)
from .probe import Probe, ProbeResult
from .probe_generator import build_generation_prompt, parse_generated_probe
from .runner import AblationRun, AblationRunner, load_run, save_run
from .tensor import AblationScore, AblationTensor
