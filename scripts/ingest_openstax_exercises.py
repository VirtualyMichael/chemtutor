"""Turn OpenStax Chemistry 2e end-of-chapter exercises + odd-numbered answer key into problem JSON.

Keeps only problems we can grade in code: single-part, no figure/table dependence, and an
answer-key entry that is one clean number (optionally followed by a short unit string).
Run:  python scripts/ingest_openstax_exercises.py
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = next((ROOT / "library" / "text").iterdir())  # the single ingested source
OUT = ROOT / "data" / "problems" / "openstax.json"

CHAPTERS = {1: ("Essential Ideas", 1), 2: ("Atoms, Molecules & Ions", 1), 3: ("Composition of Substances & Solutions", 2),
            4: ("Moles & Stoichiometry", 2), 5: ("Thermochemistry", 3), 6: ("Electronic Structure & Periodicity", 3),
            7: ("Bonding & Geometry", 3), 8: ("Advanced Covalent Bonding", 4), 9: ("Gases", 3),
            10: ("Liquids & Solids", 4), 11: ("Solutions & Colloids", 4), 12: ("Kinetics", 4),
            13: ("Equilibrium", 4), 14: ("Acid-Base Equilibria", 5), 15: ("Other Equilibria", 5),
            16: ("Thermodynamics", 5), 17: ("Electrochemistry", 5)}
FOOTER = re.compile(r"(\d+)\s*•\s*Exercises|Access for free|^\d+\s{2,}\d+\s*•|Answer Key\s+\d+|^\d+\s+Answer Key")
ITEM = re.compile(r"^(\d{1,3}) \. (.*)")
SECTION = re.compile(r"^\d{1,2}\.\d{1,2} [A-Z]")
BAD_Q = re.compile(r"\(a\)|\(b\)|figure|drawing|diagram|shown|following (table|data|graph|structure|reaction)|"
                   r"table|graph|simulation|openstax|illustrat|image|picture|below|above|appendix|example|section \d", re.I)


LOST = re.compile(r"following|:\s*$|standard (state|enthalp|entropy|free|molar)|Δ|of\s+(of|and|\.)|(and|or)\s+(\.|,)", re.I)


# Reviewed by hand: need Appendix constants/Ksp/Kf not in the question, or have a non-numeric key.
DENY = {"ox-13-079", "ox-15-043", "ox-15-086", "ox-15-099", "ox-16-023", "ox-05-035", "ox-05-053"}


def page(n: int) -> str:
    f = TEXT_DIR / f"page-{n:04d}.txt"
    return f.read_text(encoding="utf-8", errors="ignore") if f.exists() else ""


def lines(n: int):
    return [l.rstrip() for l in page(n).splitlines()]


def parse_exercises():
    starts = [n for n in range(1, 1150) if re.search(r"^Exercises\s*$", page(n), re.M)]
    out = {}  # (chapter, number) -> (section, text)
    for ch, start in enumerate(starts, 1):
        items, cur, last, section = {}, None, 0, ""
        n, begun = start, False
        while n < start + 60:
            has_footer = bool(re.search(r"\d+\s*•\s*Exercises", page(n)))
            if n > start and not has_footer:
                break
            for l in lines(n):
                if not begun:
                    if l.strip() == "Exercises":
                        begun = True
                    continue
                if FOOTER.search(l):
                    continue
                if SECTION.match(l):
                    section = l.strip()
                    cur = None
                    continue
                m = ITEM.match(l)
                if m and int(m.group(1)) == last + 1:
                    last = int(m.group(1))
                    cur = last
                    items[cur] = [section, m.group(2)]
                elif cur is not None:
                    items[cur][1] += " " + l.strip()
            n += 1
        for k, (s, t) in items.items():
            out[(ch, k)] = (s, t.strip())
    return out


def parse_answers():
    start = next(n for n in range(1100, 1250) if page(n).startswith("ANSWER KEY"))
    ans, ch, cur, k = {}, 0, None, None
    for n in range(start, start + 70):
        for l in lines(n):
            if re.match(r"^Chapter (\d+)\s*$", l.strip()):
                ch = int(l.split()[1]); cur = None; continue
            if FOOTER.search(l) or "Access for free" in l:
                continue
            m = ITEM.match(l)
            if m and ch:
                k = (ch, int(m.group(1)))
                ans[k] = m.group(2)
                cur = k
            elif cur is not None and l.strip():
                ans[cur] += " " + l.strip()
    return {k: v.strip() for k, v in ans.items()}


NUM = re.compile(r"^\s*([-−+]?\d[\d,]*\.?\d*)\s*(?:×|x|\*)?\s*(?:10\^?\s*([-−]?\d+))?\s*(.*)$")


def clean_answer(a: str):
    """Return (value, unit_text, display) if `a` is a single clean number + short unit, else None."""
    if re.search(r"\s{2,}", a) or "(a)" in a or ";" in a or len(a) > 40:
        return None  # lost superscripts/symbols or multi-part
    m = re.match(r"^\s*([-−+]?\d[\d,]*\.?\d*)\s*([A-Za-z°%/ ·\^\-−0-9]{0,22})?\s*$", a)
    if not m:
        return None
    num, unit = m.group(1).replace(",", "").replace("−", "-"), (m.group(2) or "").strip()
    # a bare trailing digit group after letters is likely a lost exponent, e.g. "m 3"
    if re.search(r"\d", unit) or not num:
        return None
    try:
        return float(num), unit, a.strip()
    except ValueError:
        return None


def main():
    ex, key = parse_exercises(), parse_answers()
    problems, seen = [], {"ex": len(ex), "ans": len(key)}
    for (ch, n), (section, q) in sorted(ex.items()):
        if (ch, n) not in key or ch not in CHAPTERS:
            continue
        ca = clean_answer(key[(ch, n)])
        if not ca or re.search(r"\s{2,}", q) or LOST.search(q) or BAD_Q.search(q) or len(q) < 25 or len(q) > 600:
            continue
        val, unit, disp = ca
        if f"ox-{ch:02d}-{n:03d}" in DENY:
            continue
        topic, level = CHAPTERS[ch]
        problems.append({"id": f"ox-{ch:02d}-{n:03d}", "topic": topic, "level": level,
                         "source": f"OpenStax Chemistry 2e, Ch. {ch}, Exercise {n} (CC BY 4.0)",
                         "section": section, "question": q, "answer": val, "answer_text": disp,
                         "tolerance_rel": 0.02, "units": [], "steps": []})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(problems, indent=1, ensure_ascii=False), encoding="utf-8")
    by = {}
    for p in problems:
        by[p["topic"]] = by.get(p["topic"], 0) + 1
    print(f"parsed {seen['ex']} exercises, {seen['ans']} answers -> kept {len(problems)}")
    for t, c in by.items():
        print(f"  {c:4d}  {t}")


if __name__ == "__main__":
    sys.exit(main())
