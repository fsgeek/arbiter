"""Scourer — undirected exploration of system prompts for interference.

The scourer is the discovery front-end of Arbiter. Rather than checking
directed rules against block pairs, it asks an LLM to wander through a
system prompt and report what it finds interesting, contradictory,
redundant, ambiguous, or structurally surprising.

Key design principle: vagueness is a feature. The scourer prompt avoids
telling the LLM what to look for. It asks what's there, what's interesting,
and — critically — what it *didn't* explore. This enables composition:
send the map from pass N as input to pass N+1, which goes where the
previous pass didn't.

The diminishing-returns signal is built in: when a pass reports nothing
new, stop.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Something the scourer found interesting."""

    description: str = Field(description="What's interesting here")
    location: str = Field(description="Where in the prompt (quote or describe)")
    category: str = Field(description="Scourer's own categorization (freeform)")
    severity_guess: str = Field(
        description="Scourer's gut: 'curious', 'notable', 'concerning', 'alarming'"
    )


class UnexploredTerritory(BaseModel):
    """Something the scourer noticed but didn't dig into."""

    description: str = Field(description="What wasn't explored")
    why_interesting: str = Field(description="Why it might be worth exploring")


class ScourerReport(BaseModel):
    """Output of a single scourer pass."""

    pass_number: int
    model: str | None = Field(
        default=None,
        description="Model that produced this report (for provenance)",
    )
    findings: list[Finding] = Field(default_factory=list)
    unexplored: list[UnexploredTerritory] = Field(default_factory=list)
    should_send_another: bool = Field(
        description="Scourer's judgment: would another pass find more?"
    )
    rationale_for_continuation: str | None = Field(
        default=None,
        description="Why another pass would or wouldn't help",
    )


class ScourerStack(BaseModel):
    """The accumulated exploration record across multiple passes."""

    reports: list[ScourerReport] = Field(default_factory=list)

    def all_findings(self) -> list[Finding]:
        findings = []
        for r in self.reports:
            findings.extend(r.findings)
        return findings

    def all_unexplored(self) -> list[UnexploredTerritory]:
        """Unexplored territory from the latest pass only (earlier passes'
        unexplored areas were presumably covered by later passes)."""
        if not self.reports:
            return []
        return list(self.reports[-1].unexplored)

    def should_continue(self) -> bool:
        if not self.reports:
            return True
        return self.reports[-1].should_send_another

    def finding_count(self) -> int:
        return sum(len(r.findings) for r in self.reports)

    def remove_pass(self, index: int) -> ScourerReport:
        """Remove a report by index and renumber remaining passes."""
        removed = self.reports.pop(index)
        for i, r in enumerate(self.reports):
            r.pass_number = i + 1
        return removed

    def models_used(self) -> list[str]:
        """List models used across all passes (for provenance)."""
        return [r.model or "unknown" for r in self.reports]


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_FIRST_PASS_PROMPT = """\
You are exploring a system prompt. Not auditing it, not checking it against \
rules — just reading it carefully and noting what you find interesting.

"Interesting" is deliberately vague. Trust your judgment. You might notice:
- Instructions that seem to contradict each other
- Rules that are stated multiple times in different places
- Implicit assumptions that aren't declared
- Surprising structural choices
- Scope ambiguities (when does a rule apply?)
- Things that would confuse a model trying to follow all instructions simultaneously
- Interactions between distant parts of the prompt
- Anything else that catches your attention

Be thorough but honest. If something is boring and straightforward, don't \
manufacture interest. If something is genuinely surprising, say why.

IMPORTANT: After documenting what you found, document what you DIDN'T explore. \
What areas did you skim? What questions occurred to you that you didn't pursue? \
What would you look at if you had more time? This is as valuable as your findings.

Finally: should we send another explorer after you? Would another pass, \
armed with your map, find things you missed? Be honest — if you think \
you covered it, say so.

## System Prompt to Explore

{prompt_text}

## Output Format

Respond with JSON only.

{{
  "pass_number": 1,
  "findings": [
    {{
      "description": "<what's interesting>",
      "location": "<where in the prompt — quote key phrases>",
      "category": "<your own label for what kind of thing this is>",
      "severity_guess": "<curious|notable|concerning|alarming>"
    }}
  ],
  "unexplored": [
    {{
      "description": "<what you didn't dig into>",
      "why_interesting": "<why it might be worth exploring>"
    }}
  ],
  "should_send_another": <true|false>,
  "rationale_for_continuation": "<why or why not>"
}}"""


_SUBSEQUENT_PASS_PROMPT = """\
You are exploring a system prompt. Previous explorers have already been \
through it and left you their map. Your job is to go where they didn't.

DO NOT repeat their findings. They found what they found. You are looking \
for what they missed, what they flagged as unexplored, and anything their \
framing caused them to overlook.

Previous explorers noted these areas as unexplored:

{unexplored_summary}

Their cumulative findings ({finding_count} total across {pass_count} passes):

{findings_summary}

Go where they didn't. Look at what they skimmed. Question their \
categorizations if they seem wrong. Find the things that their framing \
made invisible.

## When to Stop

Be honest about diminishing returns. Set should_send_another to FALSE if:
- Most of your findings are refinements or restatements of existing ones
- The unexplored territory is mostly about runtime behavior that can't \
  be determined from the text alone
- You found fewer than 3 genuinely new findings (not sharpened versions \
  of existing ones)
- The prior passes have already covered the major structural, security, \
  operational, and semantic categories

It is better to say "enough" than to pad findings. Saying "stop" is a \
finding in itself — it means the exploration was thorough.
{language_instruction}
## System Prompt to Explore

{prompt_text}

## Output Format

Respond with JSON only. The severity_guess values must be lowercase.

{{
  "pass_number": {pass_number},
  "findings": [
    {{
      "description": "<what's interesting>",
      "location": "<where in the prompt — quote key phrases>",
      "category": "<your own label for what kind of thing this is>",
      "severity_guess": "<curious|notable|concerning|alarming>"
    }}
  ],
  "unexplored": [
    {{
      "description": "<what you didn't dig into>",
      "why_interesting": "<why it might be worth exploring>"
    }}
  ],
  "should_send_another": <true|false>,
  "rationale_for_continuation": "<why or why not>"
}}"""


def _language_preamble(language: str) -> str:
    """Instruction preamble for multilingual scouring."""
    return (
        f"IMPORTANT: Conduct your entire analysis in {language}. "
        f"Write all finding descriptions, categories, severity rationale, "
        f"and unexplored territory descriptions in {language}. "
        f"Use {language}'s conceptual categories and terminology where they "
        f"capture nuances that English misses. "
        f"JSON structure keys (description, location, category, etc.) must "
        f"remain in English. Only the VALUES should be in {language}."
    )


def _extract_json(text: str) -> str:
    """Extract JSON from a response that may be wrapped in markdown code fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class Scourer:
    """Undirected prompt explorer.

    Usage:
        scourer = Scourer()

        # Build first pass prompt
        prompt = scourer.build_prompt(system_prompt_text)
        # Caller runs this through their LLM backend
        raw_response = llm.complete(prompt)
        # Parse the response
        report = scourer.parse_response(raw_response, model="claude-opus-4-6")
        scourer.add_report(report)

        # Build subsequent pass (if warranted)
        if scourer.stack.should_continue():
            prompt = scourer.build_prompt(system_prompt_text)
            # ... repeat
    """

    def __init__(self) -> None:
        self._stack = ScourerStack()

    @property
    def stack(self) -> ScourerStack:
        return self._stack

    def build_prompt(
        self, prompt_text: str, *, language: str | None = None
    ) -> str:
        """Build the scourer prompt for the next pass.

        Args:
            prompt_text: The system prompt to explore.
            language: Optional language for the analysis (e.g. "Hindi",
                "French", "Chinese"). The model will conduct its analysis
                and write findings in that language. JSON keys stay English.
        """
        pass_number = len(self._stack.reports) + 1

        if pass_number == 1:
            prompt = _FIRST_PASS_PROMPT.format(prompt_text=prompt_text)
            if language:
                prompt = _language_preamble(language) + "\n\n" + prompt
            return prompt

        # Subsequent passes get the map from previous passes
        findings_lines = []
        for r in self._stack.reports:
            model_tag = f" ({r.model})" if r.model else ""
            for f in r.findings:
                findings_lines.append(
                    f"- [{f.category}]{model_tag} {f.description}"
                )

        unexplored_lines = []
        for r in self._stack.reports:
            for u in r.unexplored:
                unexplored_lines.append(
                    f"- {u.description}: {u.why_interesting}"
                )

        language_instruction = ""
        if language:
            language_instruction = (
                f"\n\n## Language\n\n"
                f"Conduct your analysis and write all finding descriptions, "
                f"categories, and rationale in {language}. Use {language}'s "
                f"conceptual categories where they capture something English "
                f"doesn't. JSON keys must remain in English."
            )

        return _SUBSEQUENT_PASS_PROMPT.format(
            prompt_text=prompt_text,
            pass_number=pass_number,
            finding_count=self._stack.finding_count(),
            pass_count=len(self._stack.reports),
            findings_summary="\n".join(findings_lines) or "(none recorded)",
            unexplored_summary=(
                "\n".join(unexplored_lines) or "(none recorded)"
            ),
            language_instruction=language_instruction,
        )

    def parse_response(
        self, raw: str, *, model: str | None = None
    ) -> ScourerReport:
        """Parse a scourer LLM response into a ScourerReport.

        Pass number is assigned from stack position, not the model's claim.
        """
        extracted = _extract_json(raw)

        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Scourer returned unparseable response.\n"
                f"Raw: {raw[:500]!r}\nError: {e}"
            ) from e

        # Always assign pass_number from stack position, not model's claim
        correct_pass = len(self._stack.reports) + 1

        findings = [
            Finding(
                description=f["description"],
                location=f.get("location", ""),
                category=f.get("category", "uncategorized"),
                severity_guess=f.get("severity_guess", "curious").lower(),
            )
            for f in data.get("findings", [])
        ]

        unexplored = [
            UnexploredTerritory(
                description=u["description"],
                why_interesting=u.get("why_interesting", ""),
            )
            for u in data.get("unexplored", [])
        ]

        return ScourerReport(
            pass_number=correct_pass,
            model=model,
            findings=findings,
            unexplored=unexplored,
            should_send_another=data.get("should_send_another", False),
            rationale_for_continuation=data.get("rationale_for_continuation"),
        )

    def add_report(self, report: ScourerReport) -> None:
        """Add a completed report to the stack."""
        self._stack.reports.append(report)
