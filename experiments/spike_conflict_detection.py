"""
Spike: Three-tier conflict detection vs flat prompt.

Hypothesis: When an LLM receives contradictory domain facts in a flat prompt,
it silently confabulates a reconciliation. When the same contradictions are
presented through a tiered architecture (system rules + domain consistency
check), the conflicts can be detected and reported.

Usage:  ANTHROPIC_API_KEY=sk-... python experiments/spike_conflict_detection.py
Domain: Database query generation for a file indexing system (Indaleko).
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from dataclasses import dataclass, field

import anthropic

MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 1024

# --- System layer (the constitution) ---

SYSTEM_RULES = textwrap.dedent("""\
    You are an evaluation engine operating under strict rules.
    RULE 1: Before answering any query, check whether the domain facts
    provided to you are internally consistent. If two or more domain facts
    contradict each other, you MUST report the contradiction explicitly.
    Do NOT silently choose one interpretation over another.
    RULE 2: When reporting a contradiction, state which facts conflict,
    what the conflict is, and what information would be needed to resolve it.
    RULE 3: If the domain facts are consistent, proceed to answer the query.
    RULE 4: Never fabricate domain knowledge. Use only the facts provided.
""")

# --- Test Case 1: Contradictory domain ---

CONTRADICTORY_DOMAIN = [
    "The 'modified_time' field in the Objects collection stores timestamps "
    "as ISO 8601 strings in UTC (e.g., '2025-03-15T14:30:00Z'). All time "
    "comparisons should use UTC.",
    "The 'modified_time' field in the Objects collection stores timestamps "
    "as ISO 8601 strings in local time with timezone offset "
    "(e.g., '2025-03-15T07:30:00-07:00'). Time comparisons must account "
    "for the timezone offset in each record.",
]

CONTRADICTORY_QUERY = (
    "Generate an AQL query that finds all files in the Objects collection "
    "modified between 2025-03-01 and 2025-03-31. The user is in the "
    "US Pacific timezone (UTC-7 in March)."
)

# --- Test Case 2: Clean domain (control) ---

CLEAN_DOMAIN = [
    "The 'Objects' collection stores file metadata: _key (string), "
    "file_name (string), file_path (string), file_size (integer, bytes), "
    "modified_time (string, ISO 8601 UTC).",
    "The 'Objects' collection has a persistent index on modified_time.",
    "AQL date functions: DATE_ISO8601() converts to ISO string, "
    "DATE_TIMESTAMP() converts to milliseconds. Both accept ISO 8601 input.",
]

CLEAN_QUERY = (
    "Generate an AQL query that finds the 10 largest files modified "
    "in the last 30 days, returning file_name, file_size, and modified_time, "
    "sorted by file_size descending."
)


@dataclass
class EvalResult:
    path: str           # "flat" or "tiered"
    test_case: str      # "contradictory" or "clean"
    conflict_detected: bool
    response_text: str
    conflict_details: str = ""
    notes: str = ""


@dataclass
class SpikeReport:
    results: list[EvalResult] = field(default_factory=list)

    def add(self, r: EvalResult) -> None:
        self.results.append(r)

    def print_report(self) -> None:
        print("\n" + "=" * 72)
        print("SPIKE RESULTS: Three-Tier Conflict Detection")
        print("=" * 72)
        for r in self.results:
            print(f"\n--- {r.test_case.upper()} / {r.path.upper()} ---")
            print(f"Conflict detected: {r.conflict_detected}")
            if r.conflict_details:
                print(f"Details: {r.conflict_details}")
            if r.notes:
                print(f"Notes: {r.notes}")
            print("Response (first 400 chars):")
            print(textwrap.indent(r.response_text[:400], "  "))
        self._analyze()

    def _get(self, path: str, case: str) -> EvalResult | None:
        return next((r for r in self.results
                     if r.path == path and r.test_case == case), None)

    def _analyze(self) -> None:
        print("\n" + "=" * 72)
        print("ANALYSIS")
        print("=" * 72)
        fc, tc = self._get("flat", "contradictory"), self._get("tiered", "contradictory")
        if fc and tc:
            if not fc.conflict_detected and tc.conflict_detected:
                print("HYPOTHESIS SUPPORTED: Flat path silently resolved the "
                      "contradiction. Tiered path detected it.")
            elif fc.conflict_detected and tc.conflict_detected:
                print("BOTH DETECTED: The model caught the contradiction even "
                      "in flat mode. The contradiction may be too obvious. "
                      "Subtler conflicts may behave differently.")
            elif not fc.conflict_detected and not tc.conflict_detected:
                print("NEITHER DETECTED: Both paths missed the contradiction. "
                      "System rules may need strengthening.")
            else:
                print("UNEXPECTED: Flat detected but tiered did not.")
        fk, tk = self._get("flat", "clean"), self._get("tiered", "clean")
        if fk and tk:
            if not fk.conflict_detected and not tk.conflict_detected:
                print("CONTROL PASSED: No false positives on clean domain.")
            else:
                who = [p for p, r in [("flat", fk), ("tiered", tk)]
                       if r.conflict_detected]
                print(f"CONTROL FAILED: False positive from {', '.join(who)}.")


def call_llm(client: anthropic.Anthropic, system: str, user_msg: str) -> str:
    """Single LLM call. Returns concatenated text blocks."""
    resp = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return "\n".join(b.text for b in resp.content if b.type == "text")


CONFLICT_SIGNALS = [
    "contradict", "conflict", "inconsistent", "incompatible",
    "cannot determine which", "ambiguity between",
    "these facts disagree", "mutually exclusive",
]


def detect_conflict_heuristic(text: str) -> tuple[bool, str]:
    """Keyword heuristic -- does the response mention a contradiction?"""
    lower = text.lower()
    found = [s for s in CONFLICT_SIGNALS if s in lower]
    if not found:
        return False, ""
    for line in text.split("\n"):
        for s in found:
            if s in line.lower():
                return True, line.strip()
    return True, f"Signals: {', '.join(found)}"


def eval_flat(client: anthropic.Anthropic, domain: list[str],
              query: str, case: str) -> EvalResult:
    """Flat: system rules + domain + query all in one user message."""
    prompt = (
        "You are a helpful database query assistant.\n\n"
        "RULES:\n" + SYSTEM_RULES + "\n"
        "DOMAIN KNOWLEDGE:\n"
        + "\n".join(f"- {f}" for f in domain)
        + "\n\nQUERY:\n" + query
    )
    response = call_llm(client, "You are a helpful assistant.", prompt)
    detected, details = detect_conflict_heuristic(response)
    return EvalResult("flat", case, detected, response, details,
                      "All layers in single user message.")


def parse_consistency_json(raw: str) -> tuple[bool, str]:
    """Try to parse the tiered consistency check as JSON."""
    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(l for l in text.split("\n")
                         if not l.strip().startswith("```"))
    parsed = json.loads(text)
    consistent = parsed.get("consistent", True)
    conflicts = parsed.get("conflicts", [])
    if conflicts:
        return consistent, "; ".join(conflicts)
    if not consistent:
        return False, parsed.get("details", "No details")
    return True, ""


def eval_tiered(client: anthropic.Anthropic, domain: list[str],
                query: str, case: str) -> EvalResult:
    """Tiered: Step 1 checks domain consistency. Step 2 evaluates query."""
    # Step 1: domain consistency check (system rules in system prompt)
    check_prompt = (
        "Analyze these domain facts for internal consistency. "
        "Do any contradict each other?\n\n"
        "DOMAIN FACTS:\n"
        + "\n".join(f"{i+1}. {f}" for i, f in enumerate(domain))
        + '\n\nRespond with JSON only: '
        '{"consistent": true/false, "conflicts": [...], "details": "..."}'
    )
    raw = call_llm(client, SYSTEM_RULES, check_prompt)

    consistent, conflict_details = True, ""
    try:
        consistent, conflict_details = parse_consistency_json(raw)
    except (json.JSONDecodeError, AttributeError):
        detected, details = detect_conflict_heuristic(raw)
        if detected:
            consistent, conflict_details = False, details

    if not consistent:
        return EvalResult("tiered", case, True, raw, conflict_details,
                          "Conflict caught at domain check. Query skipped.")

    # Step 2: evaluate query with verified domain
    q_prompt = (
        "Using these verified domain facts, answer the query.\n\n"
        "DOMAIN FACTS:\n" + "\n".join(f"- {f}" for f in domain)
        + "\n\nQUERY:\n" + query
    )
    q_resp = call_llm(client, SYSTEM_RULES, q_prompt)
    detected, details = detect_conflict_heuristic(q_resp)
    return EvalResult("tiered", case, detected, q_resp, details,
                      "Domain consistent. Query evaluated.")


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    report = SpikeReport()
    print(f"Spike: three-tier conflict detection | Model: {MODEL}\n")

    for i, (label, domain, query, case) in enumerate([
        ("Flat,  contradictory", CONTRADICTORY_DOMAIN, CONTRADICTORY_QUERY, "contradictory"),
        ("Tiered, contradictory", CONTRADICTORY_DOMAIN, CONTRADICTORY_QUERY, "contradictory"),
        ("Flat,  clean",         CLEAN_DOMAIN,         CLEAN_QUERY,         "clean"),
        ("Tiered, clean",        CLEAN_DOMAIN,         CLEAN_QUERY,         "clean"),
    ], 1):
        print(f"[{i}/4] {label}...")
        fn = eval_flat if "Flat" in label else eval_tiered
        report.add(fn(client, domain, query, case))

    report.print_report()


if __name__ == "__main__":
    main()
