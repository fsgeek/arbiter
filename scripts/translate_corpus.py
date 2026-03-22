#!/usr/bin/env python3
"""Translate the block corpus into target languages for cross-linguistic ablation.

Uses Gemini Flash via OpenRouter to avoid circularity (translating Claude's
instructions with a non-Anthropic model). Translates ALL blocks — constrained
and free — because the experiment tests whether the whole system prompt's
language affects behavioral adherence.

Probes stay in English. The user speaks English. Only the system prompt changes.

Usage:
    python scripts/translate_corpus.py --lang zh    # Mandarin
    python scripts/translate_corpus.py --lang fr    # French
    python scripts/translate_corpus.py --lang es    # Spanish
    python scripts/translate_corpus.py --lang all   # All three
    python scripts/translate_corpus.py --dry-run    # Show what would be translated
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent

LANG_NAMES = {
    "zh": "Mandarin Chinese (简体中文)",
    "fr": "French (français)",
    "es": "Spanish (español)",
}

TRANSLATOR_MODEL = "google/gemini-2.0-flash-001"


def translate_block_text(client, text: str, lang_code: str, block_id: str) -> str:
    """Translate a single block's text, preserving technical structure.

    The translation prompt is carefully designed to preserve:
    - Markdown formatting (headers, lists, code blocks)
    - Technical terms that shouldn't be translated (tool names, API names)
    - The imperative/instructional tone
    - Structural markers (IMPORTANT:, WARNING:, etc.)
    """
    lang_name = LANG_NAMES[lang_code]

    prompt = f"""Translate the following system prompt instruction into {lang_name}.

Rules:
1. Preserve ALL markdown formatting exactly (headers, bullet points, code blocks, tables)
2. Do NOT translate: tool names, API names, model names, file paths, code snippets, URLs, JSON keys
3. Keep structural markers like "IMPORTANT:" in their translated equivalent (e.g., "重要：" for Chinese)
4. Maintain the imperative/instructional tone — these are instructions to an AI
5. Translate naturally, not word-for-word. A native speaker should find it fluent.
6. If the text contains example code or commands, keep the code in English but translate surrounding explanation
7. Return ONLY the translated text, no commentary

Block ID (for context, do not include in output): {block_id}

Text to translate:
{text}"""

    response = client.chat.completions.create(
        model=TRANSLATOR_MODEL,
        max_tokens=4096,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Translate block corpus")
    parser.add_argument(
        "--lang",
        required=True,
        choices=list(LANG_NAMES.keys()) + ["all"],
        help="Target language code or 'all'",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    parser.add_argument(
        "--corpus",
        default="data/prompts/claude-code/v2.1.50_blocks.json",
        help="Source corpus path (relative to project root)",
    )
    args = parser.parse_args()

    corpus_path = project_root / args.corpus
    with open(corpus_path) as f:
        corpus = json.load(f)

    languages = list(LANG_NAMES.keys()) if args.lang == "all" else [args.lang]

    print(f"Source corpus: {corpus_path}")
    print(f"  {len(corpus['blocks'])} blocks, ~{sum(len(b['text']) for b in corpus['blocks'])} chars")
    print(f"Target languages: {', '.join(f'{l} ({LANG_NAMES[l]})' for l in languages)}")
    print(f"Translator: {TRANSLATOR_MODEL}")

    if args.dry_run:
        print("\n--dry-run: would translate these blocks:")
        for b in corpus["blocks"]:
            print(f"  {b['id']:50s} ({len(b['text']):5d} chars)")
        n_calls = len(corpus["blocks"]) * len(languages)
        print(f"\n{n_calls} translation calls total")
        print(f"Estimated cost: ~${n_calls * 0.0003:.2f} (Gemini Flash)")
        return

    # Set up client
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    import openai

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-cross-linguistic-translation",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )

    for lang in languages:
        print(f"\n{'='*60}")
        print(f"Translating to {lang} ({LANG_NAMES[lang]})")
        print(f"{'='*60}")

        translated = json.loads(json.dumps(corpus))  # deep copy
        translated["name"] = f"{corpus['name']}-{lang}"
        translated["metadata"] = {
            "source_corpus": corpus["name"],
            "language": lang,
            "language_name": LANG_NAMES[lang],
            "translator_model": TRANSLATOR_MODEL,
        }

        for i, block in enumerate(translated["blocks"]):
            block_id = block["id"]
            original_text = block["text"]

            print(f"  [{i+1}/{len(translated['blocks'])}] {block_id} ", end="", flush=True)

            try:
                translated_text = translate_block_text(
                    client, original_text, lang, block_id
                )
                block["text"] = translated_text
                block["original_text"] = original_text
                block["translation_lang"] = lang
                print(f"({len(original_text)} → {len(translated_text)} chars)")
            except Exception as e:
                print(f"FAILED: {e}")
                print(f"    Keeping original English text for this block")
                block["translation_lang"] = "en-fallback"

            # Gentle rate limiting
            time.sleep(0.2)

        # Save translated corpus
        output_path = corpus_path.parent / f"v2.1.50_blocks_{lang}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, indent=2, ensure_ascii=False)

        print(f"\nSaved: {output_path}")

        # Summary
        total_orig = sum(len(b.get("original_text", b["text"])) for b in translated["blocks"])
        total_trans = sum(len(b["text"]) for b in translated["blocks"])
        print(f"  Original: {total_orig} chars")
        print(f"  Translated: {total_trans} chars ({total_trans/total_orig:.1%} of original)")

    print("\nDone. Run cross-linguistic baseline with:")
    print("  python scripts/run_cross_linguistic.py --model haiku --dry-run")


if __name__ == "__main__":
    main()
