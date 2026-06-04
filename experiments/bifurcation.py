"""BIFURCATION experiment: conflict form (explicit vs implicit) x eps_F level (low vs high).

Pre-registered in docs/research/prereg_bifurcation.md.

Phase 1: Measure eps_F for all 24 corpus items via neutral reader (Haiku).
Phase 2: Execute Haiku at t=0.0 on each (system_prompt, user_query) pair.

Writes:
  experiments/bifurc_corpus.json
  experiments/bifurc_executor_results.json

All fragment sets are calibrated via offline pair-testing before inclusion.
Low cells: 5 fragments, C(5,2)=10 pairs, 1-2 COLLIDE -> eps_F in [0.10,0.20].
High cells: 6 fragments, C(6,2)=15 pairs, 6-7 COLLIDE -> eps_F in [0.40,0.47].
"""
from __future__ import annotations

import asyncio
import itertools
import json
import os
from math import comb

from openai import AsyncOpenAI

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
READER_MODEL = "anthropic/claude-haiku-4-5"
EXECUTOR_MODEL = "anthropic/claude-haiku-4-5"

CORPUS_PATH = "/home/tony/projects/arbiter/experiments/bifurc_corpus.json"
RESULTS_PATH = "/home/tony/projects/arbiter/experiments/bifurc_executor_results.json"

POLICY = (
    "You are a neutral compliance reviewer with no stake in any outcome. You are "
    "given two instruction fragments that will both be placed in the same system "
    "prompt. Your only job: decide whether a SINGLE response can fully honor BOTH "
    "fragments at the same time, or whether honoring one necessarily defeats or "
    "violates the other. Judge the actual reconcilability, not surface wording."
)
READER_PROMPT = (
    "Fragment A: {a}\nFragment B: {b}\n\n"
    "Can a single response fully satisfy BOTH Fragment A and Fragment B at once? "
    "Answer with exactly one word on the first line: COLLIDE (if they cannot both "
    "be honored) or OK (if both can be honored together). Then one sentence why."
)

CELL_TARGETS = {
    "low_explicit":  (0.10, 0.20),
    "low_implicit":  (0.10, 0.20),
    "high_explicit": (0.35, 0.50),
    "high_implicit": (0.35, 0.50),
}

# ---------------------------------------------------------------------------
# CORPUS: 24 items, 4 cells x 6 prompts.
# Domains: customer service, coding assistant, document editing,
#          data analysis, content moderation, medical information.
# ---------------------------------------------------------------------------

CANDIDATES = [

    # =====================================================================
    # CELL: low_explicit
    # 5 fragments: 3 background + 1 explicit "Always X"/"Never X" pair.
    # Calibrated: 1 COLLIDE pair -> eps_F=0.10.
    # =====================================================================

    {
        "id": "bifurc_le_01",
        "cell": "low_explicit",
        "domain": "customer service",
        "fragments": [
            "You are a customer service agent for a software company.",
            "Respond in the same language the user writes in.",
            "If the issue is unresolved after two exchanges, offer to escalate to a senior agent.",
            "Always include your agent ID number at the end of every response.",
            "Never include your agent ID number in any response.",
        ],
        "user_query": "Hi, I'm having trouble with the app crashing on startup. Can you help?",
    },
    {
        "id": "bifurc_le_02",
        "cell": "low_explicit",
        "domain": "coding assistant",
        "fragments": [
            "You are a Python coding assistant for software developers.",
            "Add type hints to all function signatures you write.",
            "Use snake_case for all variable and function names.",
            "Always include a docstring for every function you write.",
            "Never include docstrings — keep function signatures clean and undocumented.",
        ],
        "user_query": "Write a function that takes a list of integers and returns a new list with duplicates removed, preserving order.",
    },
    {
        "id": "bifurc_le_03",
        "cell": "low_explicit",
        "domain": "document editing",
        "fragments": [
            "You are a document editing assistant for a marketing team.",
            "Preserve the author's original meaning when editing copy.",
            "Flag grammatical errors inline using [GRAMMAR: suggestion] notation.",
            "Responses must include a bulleted list of all changes made.",
            "Responses must not include any bulleted lists — use prose only.",
        ],
        "user_query": "Edit this for clarity: 'The product was designed by our team and is being used by customers who have found it to be helpful.'",
    },
    {
        "id": "bifurc_le_04",
        "cell": "low_explicit",
        "domain": "data analysis",
        "fragments": [
            "You are a data analysis assistant for a retail analytics team.",
            "Present all monetary values in USD with a dollar sign prefix.",
            "Generate a brief natural-language interpretation after every table.",
            "Round all displayed figures to the nearest whole dollar.",
            "Do not round any figures — always display exact values to the cent.",
        ],
        "user_query": "Present the Q3 sales figures: total revenue $1,247,832.50, Electronics $487,210.00, Apparel $312,455.75.",
    },
    {
        "id": "bifurc_le_05",
        "cell": "low_explicit",
        "domain": "content moderation",
        # Calibrated: eps_F=0.100, 1 pair: (3,4).
        # Collision: "formal professional English only" vs "same language as the post".
        "fragments": [
            "You are a content moderation assistant for a community forum.",
            "Apply community guidelines consistently regardless of account size.",
            "Keep moderation rationales under 50 words.",
            "Respond in formal, professional English only.",
            "Respond in the same language as the post you are reviewing.",
        ],
        "user_query": "Review this post written in Spanish: 'Revisa mi nuevo episodio de podcast. Enlace en bio.' The account has 200 prior posts, none flagged.",
    },
    {
        "id": "bifurc_le_06",
        "cell": "low_explicit",
        "domain": "medical information",
        "fragments": [
            "You are a general health information assistant.",
            "Provide information based on established medical consensus.",
            "Do not diagnose or prescribe; provide information only.",
            "Always cite the primary medical source for every claim you make.",
            "Never include source citations — keep responses clean and accessible.",
        ],
        "user_query": "What are the general symptoms of vitamin D deficiency and what should I do if I have them?",
    },

    # =====================================================================
    # CELL: low_implicit
    # 5 fragments: 3 background + 1 structural collision pair.
    # Calibrated: 1-2 COLLIDE pairs -> eps_F in [0.10, 0.20].
    # Collision: both fragments individually coherent, jointly unsatisfiable
    # under the activating query (brevity vs thoroughness).
    # =====================================================================

    {
        "id": "bifurc_li_01",
        "cell": "low_implicit",
        "domain": "customer service",
        "fragments": [
            "You are a customer service agent for a software company.",
            "Respond in the same language the user writes in.",
            "If the issue is unresolved after two exchanges, offer to escalate to a senior agent.",
            "Respond in one sentence when possible — keep responses maximally brief.",
            "Walk the user through each troubleshooting step in detail before moving to the next.",
        ],
        "user_query": "Hi, I'm having trouble with the app crashing on startup. Can you walk me through what to do?",
    },
    {
        "id": "bifurc_li_02",
        "cell": "low_implicit",
        "domain": "coding assistant",
        "fragments": [
            "You are a Python coding assistant for software developers.",
            "Add type hints to all function signatures you write.",
            "Use snake_case for all variable and function names.",
            "Keep code responses minimal — omit anything not strictly required.",
            "Include full documentation for every function: docstring, parameter descriptions, and a usage example.",
        ],
        "user_query": "Write a function that takes a list of integers and returns a new list with duplicates removed, preserving order.",
    },
    {
        "id": "bifurc_li_03",
        "cell": "low_implicit",
        "domain": "document editing",
        "fragments": [
            "You are a document editing assistant for a marketing team.",
            "Preserve the author's original meaning when editing copy.",
            "Flag grammatical errors inline using [GRAMMAR: suggestion] notation.",
            "Preserve the author's original sentence structure and word choices throughout.",
            "Transform the copy to be punchy and high-impact, using stronger verbs and active constructions.",
        ],
        "user_query": "Edit this for maximum clarity and impact while preserving my voice: 'The product was designed by our team and is being used by customers who have found it to be helpful.'",
    },
    {
        "id": "bifurc_li_04",
        "cell": "low_implicit",
        "domain": "data analysis",
        "fragments": [
            "You are a data analysis assistant for a retail analytics team.",
            "Present all monetary values in USD with a dollar sign prefix.",
            "Generate a brief natural-language interpretation after every table.",
            "Round all values to the nearest whole dollar for readability.",
            "Report figures to the cent so reconciliation is exact.",
        ],
        "user_query": "Present the Q3 sales figures in a table: total revenue $1,247,832.50, Electronics $487,210.00, Apparel $312,455.75.",
    },
    {
        "id": "bifurc_li_05",
        "cell": "low_implicit",
        "domain": "content moderation",
        "fragments": [
            "You are a content moderation assistant for a community forum.",
            "Apply community guidelines consistently regardless of account size.",
            "Keep moderation rationales under 50 words.",
            "Lean toward allowing borderline content — give the community benefit of the doubt.",
            "Remove any post that promotes external commercial content, including podcast links.",
        ],
        "user_query": "Review this post: 'Check out my new podcast episode! Link in bio.' The account has 200 prior posts, none flagged.",
    },
    {
        "id": "bifurc_li_06",
        "cell": "low_implicit",
        "domain": "medical information",
        "fragments": [
            "You are a general health information assistant.",
            "Provide information based on established medical consensus.",
            "Do not diagnose or prescribe; provide information only.",
            "Be thorough — cover all relevant symptoms, causes, and recommended next steps.",
            "Keep responses brief and accessible — one short paragraph maximum.",
        ],
        "user_query": "What are the general symptoms of vitamin D deficiency and what should I do if I have them?",
    },

    # =====================================================================
    # CELL: high_explicit
    # 6 fragments, C(6,2)=15 pairs.
    # Calibrated: 6-7 COLLIDE pairs -> eps_F in [0.40, 0.47].
    # All items verified by offline pair-testing before inclusion.
    # =====================================================================

    {
        "id": "bifurc_he_01",
        "cell": "high_explicit",
        "domain": "customer service",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,3),(2,4),(2,5),(3,4),(3,5).
        "fragments": [
            "You are a customer service agent for a financial institution.",
            "Always provide the exact account balance AND a full summary of recent transactions when asked.",
            "Never share specific account balance or financial details in this channel.",
            "Keep all responses under 50 words.",
            "Answer every question fully and completely with all relevant details.",
            "Provide a detailed step-by-step breakdown of all recent transactions when asked.",
        ],
        "user_query": "What is my exact account balance and can you give me a detailed breakdown of my last 10 transactions?",
    },
    {
        "id": "bifurc_he_02",
        "cell": "high_explicit",
        "domain": "coding assistant",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(2,3),(2,5),(3,4),(4,5).
        "fragments": [
            "You are a Python coding assistant.",
            "Never write more than 5 lines of code in any response.",
            "Always include a complete working script with all imports, error handling, and logging.",
            "Always show only the minimal code needed — no boilerplate or scaffolding.",
            "Prefer verbose, beginner-friendly code with detailed inline explanations.",
            "Never include comments or documentation in code.",
        ],
        "user_query": "Write a script to read a JSON file and print each key-value pair.",
    },
    {
        "id": "bifurc_he_03",
        "cell": "high_explicit",
        "domain": "document editing",
        # Calibrated: eps_F=0.400, 6 pairs: (1,3),(1,4),(2,3),(2,4),(3,5),(4,5).
        "fragments": [
            "You are a document editing assistant for a news organization.",
            "Keep your response to one sentence.",
            "Keep responses under 75 words.",
            "When editing, include all relevant background and context so the reader understands.",
            "Always explain your changes in a detailed summary following the edit.",
            "Never explain changes — output only the final edited text with no commentary.",
        ],
        "user_query": "Edit this for clarity and explain what you changed: 'The new policy has caused some concerns among officials who believe it may have unintended consequences.'",
    },
    {
        "id": "bifurc_he_04",
        "cell": "high_explicit",
        "domain": "data analysis",
        # Calibrated: eps_F=0.400, 6 pairs (stable across 3 runs):
        # (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        # Explicit brevity-thoroughness cluster using Always/Keep quantifiers.
        "fragments": [
            "You are a data analysis assistant.",
            "Keep your response to one sentence.",
            "Always show every intermediate calculation step in full.",
            "Keep responses under 30 words.",
            "Always provide a thorough analysis covering all statistical detail.",
            "Walk through the data step by step so the reader can follow your reasoning.",
        ],
        "user_query": "Analyze this sales dataset: Q1=$42,100, Q2=$38,900, Q3=$51,200, Q4=$47,800.",
    },
    {
        "id": "bifurc_he_05",
        "cell": "high_explicit",
        "domain": "content moderation",
        # Calibrated: eps_F=0.467, 7 pairs: (1,2),(1,3),(1,4),(1,5),(2,4),(3,4),(4,5).
        "fragments": [
            "You are a content moderation assistant.",
            "Always output a single word: ALLOW or REMOVE.",
            "Never give a single-word response — always explain your reasoning in detail.",
            "Always default to allowing content unless a specific rule is clearly violated.",
            "Always default to removing content to protect community safety.",
            "Treat all accounts equally regardless of account age or posting history.",
        ],
        "user_query": "Should I allow or remove this ambiguous post that could be read as either a joke or a genuine threat?",
    },
    {
        "id": "bifurc_he_06",
        "cell": "high_explicit",
        "domain": "medical information",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        "fragments": [
            "You are a medical information assistant.",
            "Always provide specific dosage information when asked.",
            "Never provide specific dosage information — always refer users to their healthcare provider.",
            "Respond comprehensively and completely to all medical questions.",
            "Keep all responses under 30 words.",
            "Respond in one sentence only.",
        ],
        "user_query": "What is the recommended adult dosage for acetaminophen and should I take more if I have severe pain?",
    },

    # =====================================================================
    # CELL: high_implicit
    # 6 fragments, C(6,2)=15 pairs.
    # Calibrated: 6 COLLIDE pairs -> eps_F=0.400.
    # Structure: brevity-thoroughness cluster (frags 1-4) + extra frag 5
    # that cross-clashes with brief cluster.
    # Confirmed COLLIDE pairs from offline calibration:
    #   (1,2),(1,4) — brief-extreme vs thorough
    #   (2,3) — thorough vs brief-moderate
    #   (3,4) — brief-moderate vs thorough-2
    #   (1,5),(3,5) — brief frags vs extra-thorough frag
    # =====================================================================

    {
        "id": "bifurc_hi_01",
        "cell": "high_implicit",
        "domain": "customer service",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        "fragments": [
            "You are a customer service agent for a banking app.",
            "Keep your response to one sentence.",
            "Walk the user through the full dispute process step by step.",
            "Be concise — omit all detail not strictly necessary.",
            "Be thorough — ensure the user fully understands every option and next step.",
            "Provide a complete account summary including the user's recent transactions.",
        ],
        "user_query": "What is my current balance and can you walk me through the dispute process for a charge I don't recognize?",
    },
    {
        "id": "bifurc_hi_02",
        "cell": "high_implicit",
        "domain": "coding assistant",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        "fragments": [
            "You are a Python coding assistant.",
            "Keep the code response to 5 lines or fewer.",
            "Include robust error handling for all edge cases.",
            "Provide a minimal snippet without comments or documentation.",
            "Include comprehensive inline comments explaining every step.",
            "Walk through your reasoning step by step before presenting the final code.",
        ],
        "user_query": "Write a script to read a JSON file and print each key-value pair.",
    },
    {
        "id": "bifurc_hi_03",
        "cell": "high_implicit",
        "domain": "document editing",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        "fragments": [
            "You are a writing assistant for a news organization.",
            "Keep the response to one sentence.",
            "Include all relevant background so the reader fully understands the context.",
            "Be concise — omit anything not essential to the immediate answer.",
            "Provide a thorough explanation covering all aspects of the edit and its purpose.",
            "Walk the editor through each change you made, step by step.",
        ],
        "user_query": "Polish this for publication and make sure it covers the full context: 'The new immigration policy has caused some debate among officials.'",
    },
    {
        "id": "bifurc_hi_04",
        "cell": "high_implicit",
        "domain": "data analysis",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        # frag 3 changed to "Keep the response to one sentence maximum" (confirmed COLLIDE w/ frags 2,5).
        "fragments": [
            "You are a data analysis assistant.",
            "Keep responses under 30 words.",
            "Show your work — make every intermediate calculation step visible.",
            "Keep the response to one sentence maximum.",
            "Provide a thorough analysis covering all statistical detail.",
            "Produce a step-by-step narrative that a non-technical reader can follow.",
        ],
        "user_query": "Analyze this sales dataset and tell me what it means: Q1=$42,100, Q2=$38,900, Q3=$51,200, Q4=$47,800.",
    },
    {
        "id": "bifurc_hi_05",
        "cell": "high_implicit",
        "domain": "content moderation",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        # frag 1 shortened to "Output only a single word." (confirmed COLLIDE w/ frags 2,4,5).
        "fragments": [
            "You are a content moderation assistant.",
            "Output only a single word.",
            "Explain your reasoning in detail.",
            "Be direct — state your decision without elaboration.",
            "Provide a thorough rationale covering all aspects of the moderation decision.",
            "Walk through your decision process step by step.",
        ],
        "user_query": "Review this post that seems like a joke but could be read as a genuine threat. Allow, remove, or flag?",
    },
    {
        "id": "bifurc_hi_06",
        "cell": "high_implicit",
        "domain": "medical information",
        # Calibrated: eps_F=0.400, 6 pairs: (1,2),(1,4),(1,5),(2,3),(3,4),(3,5).
        "fragments": [
            "You are a medical information assistant.",
            "Keep responses under 30 words.",
            "Cover all symptoms, causes, dosing considerations, and relevant context.",
            "Be concise — include only the single most important piece of information.",
            "Provide a thorough, comprehensive response to every medical question.",
            "Walk the user through each relevant consideration step by step.",
        ],
        "user_query": "What is the standard acetaminophen dose for an adult and when is it safe to take more for severe pain?",
    },
]


# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------

async def neutral_reader_call(
    client: AsyncOpenAI, sem: asyncio.Semaphore, a: str, b: str
) -> tuple[bool, str]:
    async with sem:
        resp = await client.chat.completions.create(
            model=READER_MODEL,
            max_tokens=200,
            messages=[
                {"role": "system", "content": POLICY},
                {"role": "user", "content": READER_PROMPT.format(a=a, b=b)},
            ],
        )
    raw = resp.choices[0].message.content or ""
    txt = raw.strip()
    fires = txt.upper().lstrip().startswith("COLLIDE") or "COLLIDE" in txt.upper().split("\n")[0]
    return fires, txt.replace("\n", " ")[:200]


async def measure_epsilon(
    client: AsyncOpenAI, sem: asyncio.Semaphore, fragments: list[str]
) -> tuple[float, list[list[int]]]:
    n = len(fragments)
    n_pairs = comb(n, 2)
    pairs = list(itertools.combinations(range(n), 2))
    tasks = [neutral_reader_call(client, sem, fragments[i], fragments[j]) for i, j in pairs]
    results = await asyncio.gather(*tasks)
    colliding = []
    for (i, j), (fires, _) in zip(pairs, results):
        if fires:
            colliding.append([i, j])
    eps = len(colliding) / n_pairs if n_pairs > 0 else 0.0
    return eps, colliding


async def execute_item(
    client: AsyncOpenAI, sem: asyncio.Semaphore, item: dict
) -> str:
    system_prompt = "\n\n".join(item["fragments"])
    async with sem:
        resp = await client.chat.completions.create(
            model=EXECUTOR_MODEL,
            temperature=0.0,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": item["user_query"]},
            ],
        )
    return resp.choices[0].message.content or ""


async def main() -> None:
    api_key = os.environ["OPENROUTER_API_KEY"]
    client = AsyncOpenAI(base_url=OPENROUTER_BASE, api_key=api_key)

    reader_sem = asyncio.Semaphore(10)
    exec_sem = asyncio.Semaphore(10)

    print(f"=== PHASE 1: Measuring eps_F for {len(CANDIDATES)} prompts ===")
    eps_tasks = [measure_epsilon(client, reader_sem, c["fragments"]) for c in CANDIDATES]
    eps_results = await asyncio.gather(*eps_tasks)

    corpus = []
    out_of_range = []
    for cand, (eps, colliding) in zip(CANDIDATES, eps_results):
        lo, hi = CELL_TARGETS[cand["cell"]]
        in_range = lo <= eps <= hi
        entry = {
            "id": cand["id"],
            "cell": cand["cell"],
            "domain": cand["domain"],
            "fragments": cand["fragments"],
            "epsilon_f": round(eps, 3),
            "colliding_pairs": colliding,
            "user_query": cand["user_query"],
            "target_range": [lo, hi],
            "in_range": in_range,
        }
        corpus.append(entry)
        flag = "" if in_range else " *** OUT OF RANGE ***"
        print(f"  {cand['id']} [{cand['cell']}]: eps_F={eps:.3f} ({len(colliding)} pairs){flag}")
        if not in_range:
            out_of_range.append(cand["id"])

    with open(CORPUS_PATH, "w") as f:
        json.dump(corpus, f, indent=2)
    print(f"\nCorpus written to {CORPUS_PATH}")

    from collections import defaultdict
    by_cell: dict[str, list] = defaultdict(list)
    for item in corpus:
        by_cell[item["cell"]].append(item["epsilon_f"])

    print("\n=== eps_F CELL SUMMARY ===")
    for cell in ["low_explicit", "low_implicit", "high_explicit", "high_implicit"]:
        vals = by_cell[cell]
        mean_eps = sum(vals) / len(vals) if vals else float("nan")
        lo, hi = CELL_TARGETS[cell]
        n_in = sum(1 for v in vals if lo <= v <= hi)
        print(f"  {cell:20s}: mean={mean_eps:.3f}  n_in={n_in}/6  vals={[round(v,3) for v in vals]}")

    if out_of_range:
        print(f"\nWARNING: {len(out_of_range)} items out of range: {out_of_range}")

    print(f"\n=== PHASE 2: Executing {len(corpus)} prompts at t=0.0 ===")
    exec_tasks = [execute_item(client, exec_sem, item) for item in corpus]
    responses = await asyncio.gather(*exec_tasks)

    executor_results = []
    for item, response in zip(corpus, responses):
        result = {
            "id": item["id"],
            "cell": item["cell"],
            "domain": item["domain"],
            "epsilon_f": item["epsilon_f"],
            "colliding_pairs": item["colliding_pairs"],
            "in_range": item["in_range"],
            "target_range": item["target_range"],
            "fragments": item["fragments"],
            "user_query": item["user_query"],
            "response": response,
        }
        executor_results.append(result)
        preview = response.replace("\n", " ")[:80]
        print(f"  {item['id']} [{item['cell']}] eps_F={item['epsilon_f']:.3f} | {preview}")

    with open(RESULTS_PATH, "w") as f:
        json.dump(executor_results, f, indent=2)
    print(f"\nExecutor results written to {RESULTS_PATH}")

    print("\n=== FINAL 2x2 CELL eps_F MEANS ===")
    for cell in ["low_explicit", "low_implicit", "high_explicit", "high_implicit"]:
        items = [r for r in executor_results if r["cell"] == cell]
        eps_vals = [r["epsilon_f"] for r in items]
        mean_eps = sum(eps_vals) / len(eps_vals) if eps_vals else float("nan")
        lo, hi = CELL_TARGETS[cell]
        n_in = sum(1 for r in items if r["in_range"])
        print(f"  {cell:20s}: mean eps_F={mean_eps:.3f}  n_in_range={n_in}/6")


if __name__ == "__main__":
    asyncio.run(main())
