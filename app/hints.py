"""Hint ladder with a code-enforced leak check.

The model only writes hint wording. Python decides whether a hint is allowed: it must not contain the final
answer, and on levels 1-2 it must not introduce any number that isn't already in the question. A rejected hint is
regenerated (with the reason); if it still leaks, a safe canned hint for that level is returned instead.
"""
from __future__ import annotations
import math, re

MAX_LEVEL = 4
LEVEL_RULES = {
    1: ("Level 1 (gentlest). Write NO formulas, equations or numbers. In 1-2 sentences say what the question is "
        "asking you to find and what kind of problem it is, then ask the student what information they are given."),
    2: ("Level 2. Name the key concept or relationship using symbols/words only (for example 'moles = mass / molar "
        "mass'). Do NOT substitute any numbers and do NOT calculate. Ask which given values go where."),
    3: ("Level 3. Describe how to set up the first calculation. You may mention numbers given in the problem, but do "
        "NOT do any arithmetic and do NOT give any result."),
    4: ("Level 4 (most specific). Carry out ONLY the first calculation step and show its result. Do NOT go further "
        "and do NOT state the final answer. Ask the student to do the next step."),
}
SAFE = {
    1: "Start by identifying exactly what quantity the question asks for, and list every value you are given, with units.",
    2: "Think about which relationship connects the quantities you were given to the one you want. Write that formula using symbols only, before plugging anything in.",
    3: "Substitute the given values into that relationship, converting units where needed. Set it up fully before doing any arithmetic.",
    4: "Work through the first calculation carefully, keeping units at every step, then use that result in the next step. What do you get for it?",
}
NUMBER = re.compile(r"(?<![A-Za-z\d.])\d+(?:,\d{3})*(?:\.\d+)?")


def numbers(text: str) -> list[float]:
    out = []
    for m in NUMBER.findall(text.replace("−", "-")):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def _is_trivial(x: float) -> bool:
    return x == int(x) and 0 <= x <= 10


def leak_reason(reply: str, problem: dict, level: int) -> str | None:
    """Return why this hint is not allowed, or None if it is fine."""
    key = float(problem["answer"])
    qnums = numbers(problem["question"])
    if re.search(r"\b(the )?(final )?answer (is|=|equals)\b|\bso the answer\b", reply, re.I):
        return "it states the answer"
    for x in numbers(reply):
        if _is_trivial(x) or any(math.isclose(x, q, rel_tol=1e-9) for q in qnums):
            continue
        if not _is_trivial(key) and math.isclose(x, key, rel_tol=0.01):
            return f"it contains the final answer ({x:g})"
        if level <= 2:
            return f"it introduces a new number ({x:g}) but level {level} hints may not"
    if _is_trivial(key) and key not in qnums and re.search(rf"(?<![\w.]){int(key)}(?![\w.])", reply):
        if re.search(rf"(=|is|equals|get|gives?)\s*{int(key)}\b", reply):
            return "it states the answer"
    return None


def build(problem: dict, level: int) -> list[dict]:
    level = max(1, min(level, MAX_LEVEL))
    steps = problem.get("steps") or []
    private = f"PRIVATE reference (never quote or reveal): final answer = {problem.get('answer_text') or problem['answer']}."
    if steps:
        private += " Intended solution steps: " + " | ".join(steps)
    sys = ("You are a patient chemistry tutor writing ONE hint for a beginner. Plain text only, no LaTeX. "
           "Maximum 50 words. Never state the final answer. Mention ONLY the single next step: never outline the "
           "whole method, never say 'then' or 'finally', and never describe a later step. "
           + LEVEL_RULES[level] + " " + private)
    return [{"role": "system", "content": sys},
            {"role": "user", "content": f"Problem: {problem['question']}\nWrite hint level {level}."}]


def generate(problem: dict, level: int, llm, tries: int = 3) -> dict:
    """llm(messages, max_tokens, temperature) -> str. Returns {'reply', 'fallback', 'rejected': [reasons]}."""
    level = max(1, min(level, MAX_LEVEL))
    msgs, rejected = build(problem, level), []
    for _ in range(tries):
        reply = llm(msgs, 160, 0.2).strip()
        why = "it was empty" if not reply else leak_reason(reply, problem, level)
        if not why:
            return {"reply": reply, "fallback": False, "rejected": rejected}
        rejected.append(why)
        msgs = msgs + [{"role": "assistant", "content": reply},
                       {"role": "user", "content": f"That hint is not allowed because {why}. Rewrite it so it follows "
                                                   f"the level {level} rules and reveals no result."}]
    return {"reply": SAFE[level], "fallback": True, "rejected": rejected}
