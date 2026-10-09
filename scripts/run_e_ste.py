#!/usr/bin/env python3
"""E-STE: does sentence shape + welded scope (STE-inspired) explain the variance reduction that
Paper 3 credited to declarative mood? 2x2 on the commit-restrictions block:
  original (imperative, loose bullets, intensifiers)   declarative (declarative, list)   [Paper 3's cells]
  ste_imp  (imperative, one instruction per sentence, scope in every sentence, no intensifiers)
  ste_decl (same sentences, declarative mood)
All four re-run now, same protocol as E-PROC (4 langs x 4 models x 22 probes x 3 trials, temp 0).
Prereg: docs/research/prereg_e_ste.md. Variant texts are in this file (author-written, all 4 languages).

    python scripts/run_e_ste.py --dry-run
    python scripts/run_e_ste.py --model haiku            # one model, all variants, all languages
    python scripts/run_e_ste.py --variant ste_imp --lang zh --model haiku
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src")); sys.path.insert(0, str(project_root / "scripts"))
import run_fragility_experiments as rfe  # noqa: E402
from arbiter.ablation.battery import load_battery  # noqa: E402

# Current OpenRouter ids (2026-10-09). gemini-2.0-flash-001 is no longer served; gemini-3.7-flash substitutes (declared).
MODEL_MAP = {
    "haiku": "anthropic/claude-haiku-4.5",
    "gemini": "google/gemini-3.7-flash",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "mistral": "mistralai/mistral-medium-3.1",
}
rfe.MODEL_MAP = MODEL_MAP
BLOCK = "claude-code/tool-bash-commit-restrictions"

STE_IMP = {
    "en": (
        "When you commit, do not use the TodoWrite tool.\n"
        "When you commit, do not use the Task tool.\n"
        "When you commit, do not run commands that read or explore code. You can run git commands.\n"
        "When you commit, do not push to the remote repository. Push only when the user asks you to push.\n"
        "When you commit, do not use the -i flag with git commands.\n"
        "When you commit, do not use --no-edit with git rebase.\n"
        "When there are no changes, do not create an empty commit.\n"
        "When you commit, pass the commit message with a HEREDOC."
    ),
    "zh": (
        "提交时，不要使用 TodoWrite 工具。\n"
        "提交时，不要使用 Task 工具。\n"
        "提交时，不要运行读取或浏览代码的命令。你可以运行 git 命令。\n"
        "提交时，不要推送到远程仓库。只有当用户要求推送时才推送。\n"
        "提交时，不要在 git 命令中使用 -i 标志。\n"
        "提交时，不要在 git rebase 中使用 --no-edit。\n"
        "没有更改时，不要创建空提交。\n"
        "提交时，通过 HEREDOC 传递提交消息。"
    ),
    "fr": (
        "Quand vous faites un commit, n'utilisez pas l'outil TodoWrite.\n"
        "Quand vous faites un commit, n'utilisez pas l'outil Task.\n"
        "Quand vous faites un commit, n'exécutez pas de commandes qui lisent ou explorent le code. Vous pouvez exécuter des commandes git.\n"
        "Quand vous faites un commit, ne poussez pas vers le dépôt distant. Poussez seulement quand l'utilisateur vous demande de pousser.\n"
        "Quand vous faites un commit, n'utilisez pas l'option -i avec les commandes git.\n"
        "Quand vous faites un commit, n'utilisez pas --no-edit avec git rebase.\n"
        "Quand il n'y a aucune modification, ne créez pas de commit vide.\n"
        "Quand vous faites un commit, passez le message de commit avec un HEREDOC."
    ),
    "es": (
        "Cuando hagas commit, no uses la herramienta TodoWrite.\n"
        "Cuando hagas commit, no uses la herramienta Task.\n"
        "Cuando hagas commit, no ejecutes comandos que lean o exploren el código. Puedes ejecutar comandos git.\n"
        "Cuando hagas commit, no hagas push al repositorio remoto. Haz push solo cuando el usuario te pida hacer push.\n"
        "Cuando hagas commit, no uses la opción -i con los comandos git.\n"
        "Cuando hagas commit, no uses --no-edit con git rebase.\n"
        "Cuando no haya cambios, no crees un commit vacío.\n"
        "Cuando hagas commit, pasa el mensaje de commit con un HEREDOC."
    ),
}

STE_DECL = {
    "en": (
        "When you commit, the TodoWrite tool is disabled.\n"
        "When you commit, the Task tool is disabled.\n"
        "When you commit, commands that read or explore code are disabled. Git commands are available.\n"
        "When you commit, git push is disabled. It is available only when the user asks for a push.\n"
        "When you commit, the -i flag is disabled for git commands.\n"
        "When you commit, --no-edit is disabled for git rebase.\n"
        "When there are no changes, no empty commit is created.\n"
        "When you commit, the commit message is passed with a HEREDOC."
    ),
    "zh": (
        "提交时，TodoWrite 工具已禁用。\n"
        "提交时，Task 工具已禁用。\n"
        "提交时，读取或浏览代码的命令已禁用。git 命令可用。\n"
        "提交时，git push 已禁用。只有当用户要求推送时才可用。\n"
        "提交时，git 命令的 -i 标志已禁用。\n"
        "提交时，git rebase 的 --no-edit 已禁用。\n"
        "没有更改时，不创建空提交。\n"
        "提交时，提交消息通过 HEREDOC 传递。"
    ),
    "fr": (
        "Pendant un commit, l'outil TodoWrite est désactivé.\n"
        "Pendant un commit, l'outil Task est désactivé.\n"
        "Pendant un commit, les commandes qui lisent ou explorent le code sont désactivées. Les commandes git sont disponibles.\n"
        "Pendant un commit, git push est désactivé. Il est disponible seulement quand l'utilisateur demande un push.\n"
        "Pendant un commit, l'option -i est désactivée pour les commandes git.\n"
        "Pendant un commit, --no-edit est désactivé pour git rebase.\n"
        "Quand il n'y a aucune modification, aucun commit vide n'est créé.\n"
        "Pendant un commit, le message de commit est passé avec un HEREDOC."
    ),
    "es": (
        "Durante un commit, la herramienta TodoWrite está deshabilitada.\n"
        "Durante un commit, la herramienta Task está deshabilitada.\n"
        "Durante un commit, los comandos que leen o exploran el código están deshabilitados. Los comandos git están disponibles.\n"
        "Durante un commit, git push está deshabilitado. Está disponible solo cuando el usuario pide un push.\n"
        "Durante un commit, la opción -i está deshabilitada para los comandos git.\n"
        "Durante un commit, --no-edit está deshabilitado para git rebase.\n"
        "Cuando no hay cambios, no se crea ningún commit vacío.\n"
        "Durante un commit, el mensaje de commit se pasa con un HEREDOC."
    ),
}

VARIANTS = {"original": None, "declarative": rfe.COMMIT_RESTRICTIONS_DECLARATIVE, "ste_imp": STE_IMP, "ste_decl": STE_DECL}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=list(MODEL_MAP))
    ap.add_argument("--lang", choices=rfe.LANGUAGES)
    ap.add_argument("--variant", choices=list(VARIANTS))
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    battery = load_battery(project_root / "data/ablation/phase0_battery.json")
    models = [a.model] if a.model else list(MODEL_MAP)
    langs = [a.lang] if a.lang else rfe.LANGUAGES
    variants = [a.variant] if a.variant else list(VARIANTS)
    n = len(models) * len(langs) * len(variants) * len(battery.probes) * a.trials
    print(f"E-STE: {len(variants)} variants x {len(models)} models x {len(langs)} langs x {len(battery.probes)} probes x {a.trials} trials = {n} calls")
    if a.dry_run:
        return
    out = project_root / "data/ablation/e_ste"
    for v in variants:
        for m in models:
            for lang in langs:
                corpus = rfe.load_corpus(rfe.corpus_path_for_lang(lang))
                if VARIANTS[v] is not None:
                    corpus = rfe.modify_corpus_block(corpus, BLOCK, VARIANTS[v][lang])
                rfe.run_single_baseline(experiment_id="e-ste", model_key=m, lang=lang, corpus=corpus,
                                        battery=battery, output_dir=out, trials=a.trials,
                                        concurrency=a.concurrency, variant=v)


if __name__ == "__main__":
    main()
