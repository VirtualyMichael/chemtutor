"""Generate original practice problems with computed answers and worked steps.

Every answer is calculated here from the same constants and atomic masses the cheat sheet shows, so the tutor
never has to do arithmetic. Deterministic: each template has its own seed, so ids/problems are stable.
Run:  python scripts/generate_problems.py     (writes data/problems/generated.json)
"""
from __future__ import annotations
import json, math, random, sys
from math import gcd, log10, sqrt, exp, log
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import chem  # noqa: E402
from app.chem import molar_mass as MM, pretty as pf, parse  # noqa: E402

OUT = ROOT / "data" / "problems" / "generated.json"
R_ATM, R_J, NA, H, C, F, RH = 0.08206, 8.314, 6.022e23, 6.626e-34, 3.00e8, 96485.0, 2.178e-18
SUPT = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


# ---------------- helpers ----------------
def sig(x: float, n: int = 3) -> str:
    """Format to n significant figures; scientific as '3.01 x 10^23' when very large/small."""
    if x == 0:
        return "0"
    d = n - 1 - math.floor(log10(abs(x)))
    r = round(x, d)
    if abs(r) >= 1e7 or abs(r) < 1e-3:
        e = math.floor(log10(abs(r)))
        return f"{r / 10 ** e:.{n - 1}f} x 10^{e}"
    return f"{r:.{max(0, d)}f}"


def nice(rng, a, b, dp):
    v = round(rng.uniform(a, b), dp)
    return int(v) if dp == 0 else v


def prob(topic, level, q, ans, unit, steps, rel=0.01, abs_=0.0, sci=False, n=3):
    shown = str(int(round(ans))) if float(ans).is_integer() and abs(ans) < 1e5 and rel == 0 else sig(ans, n)
    return {"topic": topic, "level": level,
            "question": q + (" Give your answer in scientific notation (e.g. 3.2e-5)." if sci else ""),
            "answer": float(f"{ans:.6g}"), "answer_text": shown + (f" {unit}" if unit else ""),
            "tolerance_rel": rel, "tolerance_abs": abs_, "units": [], "steps": steps,
            "source": "generated (original); atomic masses from the cheat sheet"}


def ion(sym, ch):
    return sym + ch.translate(SUPT)


def term(c, f):
    return (f"{c} " if c != 1 else "") + pf(f)


def eq_text(rx):
    return " + ".join(term(c, f) for c, f in rx[0]) + " → " + " + ".join(term(c, f) for c, f in rx[1])


# ---------------- Foundations (level 1) ----------------
SIGS = [("0.00450", 3), ("100.0", 4), ("0.0820", 3), ("3.0200", 5), ("5.60 x 10^3", 3), ("4001", 4),
        ("0.000230", 3), ("12.040", 5)]


def t_sigfigs(rng, k):
    x, n = SIGS[k % len(SIGS)]
    return prob("Foundations", 1, f"How many significant figures are in the measurement {x}?", n, "",
                ["Leading zeros are never significant.",
                 "Zeros between nonzero digits, and trailing zeros after a decimal point, are significant.",
                 f"Count the significant digits in {x}: {n}."], rel=0, abs_=0)


CONV = [("km", "m", 1000, "1 km = 1000 m"), ("mL", "L", 0.001, "1 mL = 0.001 L"), ("g", "kg", 0.001, "1 kg = 1000 g"),
        ("hours", "seconds", 3600, "1 h = 3600 s"), ("inches", "cm", 2.54, "1 in = 2.54 cm"),
        ("lb", "kg", 0.4536, "1 lb = 0.4536 kg"), ("miles", "km", 1.609, "1 mi = 1.609 km"),
        ("gallons", "L", 3.785, "1 gal = 3.785 L"), ("cm", "mm", 10, "1 cm = 10 mm"), ("minutes", "seconds", 60, "1 min = 60 s")]


def t_unitconv(rng, k):
    a, b, f, rule = CONV[k % len(CONV)]
    v = nice(rng, 1.5, 95, 1)
    return prob("Foundations", 1, f"Convert {v} {a} to {b}.", v * f, b,
                [f"Write the conversion factor: {rule}.", f"Multiply: {v} {a} x ({sig(f, 4)} {b} per {a}) .",
                 f"= {sig(v * f, 3)} {b}."])


def t_speed(rng, k):
    v = [36, 54, 72, 90, 108, 126][k % 6]
    return prob("Foundations", 1, f"A car travels at {v} km/h. Express its speed in m/s.", v / 3.6, "m/s",
                ["Use 1 km = 1000 m and 1 h = 3600 s.", f"{v} km/h x (1000 m / 1 km) x (1 h / 3600 s).",
                 f"= {v * 1000} / 3600 = {sig(v / 3.6)} m/s."])


def t_sci(rng, k):
    e = [-6, -5, -4, -3, 3, 4, 5, 6][k % 8]
    c = nice(rng, 1.1, 9.9, 1)
    N = c * 10 ** e
    s = f"{N:.{abs(e) + 1}f}" if e < 0 else f"{round(N):,}"
    return prob("Foundations", 1, f"When {s} is written in scientific notation (a x 10^n, 1 ≤ a < 10), what is n?", e, "",
                ["Move the decimal point until there is one nonzero digit to its left.",
                 "Count the places moved: left = positive exponent, right = negative.",
                 f"{s} = {c} x 10^{e}, so n = {e}."], rel=0)


MATS = [("aluminum", 2.70), ("iron", 7.87), ("copper", 8.96), ("lead", 11.3), ("gold", 19.3), ("silver", 10.5),
        ("ethanol", 0.789), ("mercury", 13.6)]


def t_density(rng, k):
    name, d = MATS[k % len(MATS)]
    v = k % 3
    if v == 0:
        V = nice(rng, 5, 60, 1)
        m = round(d * V, 1)
        return prob("Foundations", 1, f"A sample of {name} has a mass of {m} g and a volume of {V} cm³. What is its density in g/cm³?",
                    m / V, "g/cm³", ["Density = mass / volume.", f"{m} g / {V} cm³ = {sig(m / V)} g/cm³."])
    if v == 1:
        m = nice(rng, 20, 300, 0)
        return prob("Foundations", 1, f"The density of {name} is {d} g/cm³. What volume (cm³) does {m} g of it occupy?",
                    m / d, "cm³", ["Rearrange density = m/V to V = m / density.", f"V = {m} g / {d} g/cm³ = {sig(m / d)} cm³."])
    V = nice(rng, 5, 80, 1)
    return prob("Foundations", 1, f"The density of {name} is {d} g/cm³. What is the mass (g) of {V} cm³ of it?",
                d * V, "g", ["Rearrange density = m/V to m = density x V.", f"m = {d} g/cm³ x {V} cm³ = {sig(d * V)} g."])


def t_temp(rng, k):
    v = k % 3
    if v == 0:
        c = nice(rng, -30, 95, 0)
        return prob("Foundations", 1, f"Convert {c} °C to kelvin.", c + 273.15, "K", ["K = °C + 273.15.", f"{c} + 273.15 = {sig(c + 273.15, 4)} K."], rel=0, abs_=0.6)
    if v == 1:
        c = nice(rng, 5, 95, 0)
        return prob("Foundations", 1, f"Convert {c} °C to degrees Fahrenheit.", 1.8 * c + 32, "°F",
                    ["°F = (9/5) x °C + 32.", f"1.8 x {c} + 32 = {sig(1.8 * c + 32, 4)} °F."], rel=0, abs_=0.6)
    f = rng.choice([50, 68, 86, 104, 122, 140, 176, 212])
    return prob("Foundations", 1, f"Convert {f} °F to degrees Celsius.", (f - 32) / 1.8, "°C",
                ["°C = (5/9)(°F − 32).", f"({f} − 32) / 1.8 = {sig((f - 32) / 1.8, 3)} °C."], rel=0, abs_=0.6)


# ---------------- Atoms, molecules & ions (level 2) ----------------
NEUT = [("C", 14), ("Cl", 37), ("U", 235), ("Fe", 56), ("K", 40), ("Cu", 65), ("Br", 81), ("Sr", 90)]
IONS = [("Fe", "3+", 3), ("S", "2-", -2), ("Al", "3+", 3), ("Cl", "-", -1), ("Mg", "2+", 2), ("N", "3-", -3), ("Cu", "2+", 2), ("Br", "-", -1)]
ISO = [("chlorine", [(34.969, 75.78), (36.966, 24.22)]), ("copper", [(62.930, 69.15), (64.928, 30.85)]),
       ("boron", [(10.013, 19.9), (11.009, 80.1)]), ("lithium", [(6.015, 7.59), (7.016, 92.41)]),
       ("bromine", [(78.918, 50.69), (80.916, 49.31)]), ("gallium", [(68.926, 60.11), (70.925, 39.89)])]


def t_neutrons(rng, k):
    s, A = NEUT[k % len(NEUT)]
    z = chem.Z[s]
    return prob("Atoms, Molecules & Ions", 2, f"How many neutrons are in an atom of {chem.NAME[s].lower()}-{A}?", A - z, "",
                [f"Find the atomic number Z of {s} on the periodic table: Z = {z}.", "neutrons = mass number − atomic number.", f"{A} − {z} = {A - z}."], rel=0)


def t_ions(rng, k):
    s, ch, q = IONS[k % len(IONS)]
    z = chem.Z[s]
    return prob("Atoms, Molecules & Ions", 2, f"How many electrons are in one {ion(s, ch)} ion?", z - q, "",
                [f"{s} has Z = {z}, so a neutral atom has {z} electrons.",
                 "Electrons in an ion = Z − charge (a cation lost electrons, an anion gained them).", f"{z} − ({q:+d}) = {z - q}."], rel=0)


def t_avgmass(rng, k):
    name, iso = ISO[k % len(ISO)]
    avg = sum(m * a / 100 for m, a in iso)
    lst = " and ".join(f"{m} amu ({a}%)" for m, a in iso)
    return prob("Atoms, Molecules & Ions", 2, f"Naturally occurring {name} has two isotopes with masses and abundances of {lst}. What is the average atomic mass of {name} in amu?",
                avg, "amu", ["Convert each percent to a fraction (÷ 100).", "Multiply each isotope mass by its fractional abundance.",
                             "Add: " + " + ".join(f"{m} x {a / 100:.4f}" for m, a in iso) + f" = {sig(avg, 4)} amu."], rel=0.002)


# ---------------- Moles ----------------
FORMS = ["NaCl", "H2O", "CO2", "CaCO3", "H2SO4", "NaOH", "Mg(OH)2", "C6H12O6", "(NH4)2SO4", "Al2(SO4)3", "Ca(NO3)2",
         "KMnO4", "C2H5OH", "NH3", "Fe2O3", "C3H8", "HCl", "NaHCO3"]


def mm_steps(f):
    return "Molar mass of " + pf(f) + " = " + " + ".join(f"{n} x {chem.MASS[e]}" for e, n in parse(f).items()) + f" = {sig(MM(f), 4)} g/mol."


def t_molarmass(rng, k):
    f = FORMS[k % len(FORMS)]
    return prob("Moles & Stoichiometry", 2, f"What is the molar mass of {pf(f)} in g/mol? (Use the periodic table in the cheat sheet.)",
                MM(f), "g/mol", ["Count the atoms of each element in the formula (expand any parentheses).",
                                 "Multiply each count by the atomic mass from the periodic table.", mm_steps(f)], rel=0.005)


def t_gtomol(rng, k):
    f = FORMS[(k * 5 + 2) % len(FORMS)]
    m = nice(rng, 5, 200, 1)
    return prob("Moles & Stoichiometry", 2, f"How many moles are in {m} g of {pf(f)}?", m / MM(f), "mol",
                [mm_steps(f), "moles = mass / molar mass.", f"{m} g / {sig(MM(f), 4)} g/mol = {sig(m / MM(f))} mol."])


def t_moltog(rng, k):
    f = FORMS[(k * 7 + 3) % len(FORMS)]
    n = nice(rng, 0.1, 5, 2)
    return prob("Moles & Stoichiometry", 2, f"What is the mass in grams of {n} mol of {pf(f)}?", n * MM(f), "g",
                [mm_steps(f), "mass = moles x molar mass.", f"{n} mol x {sig(MM(f), 4)} g/mol = {sig(n * MM(f))} g."])


PART = [("H2O", "H"), ("CO2", "O"), ("C6H12O6", "C"), ("H2SO4", "O"), ("NH3", "H"), ("CaCO3", "O")]


def t_particles(rng, k):
    v = k % 3
    if v == 0:
        f = FORMS[(k * 3) % len(FORMS)]
        n = nice(rng, 0.2, 4, 2)
        return prob("Moles & Stoichiometry", 3, f"How many molecules (or formula units) are in {n} mol of {pf(f)}?", n * NA, "particles",
                    ["Particles = moles x Avogadro's number (6.022 x 10²³ per mol).", f"{n} x 6.022e23 = {sig(n * NA)}."], sci=True)
    if v == 1:
        f = FORMS[(k * 3 + 1) % len(FORMS)]
        m = nice(rng, 2, 60, 1)
        ans = m / MM(f) * NA
        return prob("Moles & Stoichiometry", 3, f"How many molecules (or formula units) are in {m} g of {pf(f)}?", ans, "particles",
                    [mm_steps(f), f"moles = {m} / {sig(MM(f), 4)} = {sig(m / MM(f))} mol.", f"Particles = {sig(m / MM(f))} x 6.022e23 = {sig(ans)}."], sci=True)
    f, el = PART[(k // 3) % len(PART)]
    m = nice(rng, 2, 60, 1)
    cnt = parse(f)[el]
    ans = m / MM(f) * NA * cnt
    return prob("Moles & Stoichiometry", 3, f"How many atoms of {chem.NAME[el].lower()} are in {m} g of {pf(f)}?", ans, "atoms",
                [mm_steps(f), f"moles of {pf(f)} = {m} / {sig(MM(f), 4)} = {sig(m / MM(f))} mol.", f"Molecules = {sig(m / MM(f))} x 6.022e23.",
                 f"Each molecule has {cnt} {el} atom(s): multiply by {cnt} → {sig(ans)} atoms."], sci=True)


PC = [("H2O", "O"), ("CO2", "C"), ("CaCO3", "Ca"), ("NaCl", "Na"), ("Fe2O3", "Fe"), ("C6H12O6", "C"), ("NH4NO3", "N"),
      ("H2SO4", "S"), ("Al2O3", "Al"), ("Mg(OH)2", "Mg")]


def t_percomp(rng, k):
    f, el = PC[k % len(PC)]
    cnt = parse(f)[el]
    ans = 100 * cnt * chem.MASS[el] / MM(f)
    return prob("Moles & Stoichiometry", 2, f"What is the mass percent of {chem.NAME[el].lower()} in {pf(f)}?", ans, "%",
                [mm_steps(f), f"Mass of {el} in one mole = {cnt} x {chem.MASS[el]} = {sig(cnt * chem.MASS[el], 4)} g.",
                 f"% = {sig(cnt * chem.MASS[el], 4)} / {sig(MM(f), 4)} x 100 = {sig(ans)}%."])


EMP = [("H2O2", "H"), ("C2H4", "C"), ("C6H6", "H"), ("C4H10", "C"), ("N2O4", "O"), ("C8H18", "H"), ("C6H12O6", "C"), ("C2H4O2", "H")]


def t_empirical(rng, k):
    f, target = EMP[k % len(EMP)]
    comp = parse(f)
    g = 0
    for n in comp.values():
        g = gcd(g, n)
    pcts = {e: round(100 * n * chem.MASS[e] / MM(f), 2) for e, n in comp.items()}
    desc = ", ".join(f"{p}% {chem.NAME[e].lower()}" for e, p in pcts.items())
    moles = {e: pcts[e] / chem.MASS[e] for e in comp}
    small = min(moles.values())
    return prob("Moles & Stoichiometry", 3, f"A compound is {desc} by mass. What is the subscript of {chem.NAME[target].lower()} in its empirical formula?",
                comp[target] // g, "", ["Assume 100 g, so each percent is that many grams.",
                                        "Moles: " + ", ".join(f"{e} = {pcts[e]}/{chem.MASS[e]} = {moles[e]:.3f}" for e in comp),
                                        f"Divide by the smallest ({small:.3f}): " + ", ".join(f"{e} {moles[e] / small:.2f}" for e in comp) +
                                        "; multiply to reach whole numbers.",
                                        f"Empirical formula subscript of {target} = {comp[target] // g}."], rel=0)


# ---------------- Stoichiometry ----------------
RXN = [([(2, "H2"), (1, "O2")], [(2, "H2O")]), ([(1, "N2"), (3, "H2")], [(2, "NH3")]),
       ([(1, "CH4"), (2, "O2")], [(1, "CO2"), (2, "H2O")]), ([(2, "Na"), (1, "Cl2")], [(2, "NaCl")]),
       ([(1, "CaCO3")], [(1, "CaO"), (1, "CO2")]), ([(2, "Al"), (3, "Cl2")], [(2, "AlCl3")]),
       ([(2, "KClO3")], [(2, "KCl"), (3, "O2")]), ([(1, "Zn"), (2, "HCl")], [(1, "ZnCl2"), (1, "H2")]),
       ([(1, "C3H8"), (5, "O2")], [(3, "CO2"), (4, "H2O")]), ([(4, "Fe"), (3, "O2")], [(2, "Fe2O3")]),
       ([(1, "Mg"), (2, "HCl")], [(1, "MgCl2"), (1, "H2")]), ([(2, "H2O2")], [(2, "H2O"), (1, "O2")]),
       ([(2, "Mg"), (1, "O2")], [(2, "MgO")]), ([(1, "Fe2O3"), (3, "CO")], [(2, "Fe"), (3, "CO2")])]


def t_massmass(rng, k):
    rx = RXN[k % len(RXN)]
    cr, r = rx[0][(k // len(RXN)) % len(rx[0])]
    cp, p = rx[1][0]
    m = nice(rng, 5, 120, 1)
    n_r = m / MM(r)
    ans = n_r * cp / cr * MM(p)
    extra = " Assume all other reactants are in excess." if len(rx[0]) > 1 else ""
    return prob("Moles & Stoichiometry", 3, f"For the reaction {eq_text(rx)}, how many grams of {pf(p)} form from {m} g of {pf(r)}?{extra}", ans, "g",
                [f"Moles of {pf(r)}: {m} g / {sig(MM(r), 4)} g/mol = {sig(n_r)} mol.", f"Mole ratio {pf(p)} : {pf(r)} = {cp} : {cr}.",
                 f"Moles of {pf(p)} = {sig(n_r)} x {cp}/{cr} = {sig(n_r * cp / cr)} mol.", f"Mass = {sig(n_r * cp / cr)} x {sig(MM(p), 4)} g/mol = {sig(ans)} g."])


def t_limiting(rng, k):
    two = [rx for rx in RXN if len(rx[0]) == 2]
    for _ in range(50):
        rx = two[(k + rng.randrange(len(two))) % len(two)]
        (c1, r1), (c2, r2) = rx[0]
        m1 = nice(rng, 8, 60, 1)
        fac = rng.choice([0.4, 0.5, 0.6, 0.7, 1.3, 1.5, 1.8, 2.2])
        m2 = round(m1 / MM(r1) / c1 * c2 * MM(r2) * fac, 1)
        n1, n2 = m1 / MM(r1) / c1, m2 / MM(r2) / c2
        if abs(n1 - n2) / max(n1, n2) < 0.15 or m2 < 1:
            continue
        lim, exc = ((r1, c1, m1, n1), (r2, c2, m2, n2)) if n1 < n2 else ((r2, c2, m2, n2), (r1, c1, m1, n1))
        cp, p = rx[1][0]
        base = [f"Moles ÷ coefficient: {pf(r1)}: {sig(n1)}, {pf(r2)}: {sig(n2)}; the smaller is limiting → {pf(lim[0])}."]
        if k % 2 == 0:
            ans = lim[3] * cp * MM(p)
            return prob("Moles & Stoichiometry", 4, f"For {eq_text(rx)}, {m1} g of {pf(r1)} reacts with {m2} g of {pf(r2)}. What mass (g) of {pf(p)} can form?",
                        ans, "g", base + [f"Product moles = {sig(lim[3])} x {cp} = {sig(lim[3] * cp)} mol.", f"Mass = {sig(lim[3] * cp)} mol x {sig(MM(p), 4)} g/mol = {sig(ans)} g."])
        used = lim[3] * exc[1] * MM(exc[0])
        ans = exc[2] - used
        return prob("Moles & Stoichiometry", 4, f"For {eq_text(rx)}, {m1} g of {pf(r1)} reacts with {m2} g of {pf(r2)}. How many grams of the excess reactant remain after the reaction?",
                    ans, "g", base + [f"{pf(exc[0])} consumed = {sig(lim[3])} x {exc[1]} x {sig(MM(exc[0]), 4)} g/mol = {sig(used)} g.", f"Remaining = {exc[2]} − {sig(used)} = {sig(ans)} g."])
    return None


def t_yield(rng, k):
    rx = RXN[(k * 3 + 1) % len(RXN)]
    cr, r = rx[0][0]
    cp, p = rx[1][0]
    m = nice(rng, 10, 100, 1)
    theo = m / MM(r) * cp / cr * MM(p)
    act = round(theo * rng.uniform(0.55, 0.95), 1)
    extra = " (other reactants in excess)" if len(rx[0]) > 1 else ""
    return prob("Moles & Stoichiometry", 3, f"For {eq_text(rx)}, {m} g of {pf(r)} reacts{extra} and {act} g of {pf(p)} is collected. What is the percent yield?",
                act / theo * 100, "%", [f"Theoretical yield: {m} / {sig(MM(r), 4)} x {cp}/{cr} x {sig(MM(p), 4)} = {sig(theo)} g.",
                                        f"% yield = actual / theoretical x 100 = {act} / {sig(theo)} x 100 = {sig(act / theo * 100)}%."], rel=0.015)


# ---------------- Solutions ----------------
SOL = ["NaCl", "KCl", "NaOH", "C6H12O6", "CaCl2", "KNO3"]


def t_molarity(rng, k):
    f = SOL[k % len(SOL)]
    v = k % 3
    if v == 0:
        m, V = nice(rng, 2, 60, 1), nice(rng, 100, 1000, 0)
        M = m / MM(f) / (V / 1000)
        return prob("Solutions", 3, f"{m} g of {pf(f)} is dissolved in water to make {V} mL of solution. What is the molarity?", M, "M",
                    [mm_steps(f), f"moles = {m} / {sig(MM(f), 4)} = {sig(m / MM(f))} mol.", f"Volume = {V} mL = {V / 1000:.6g} L.", f"M = {sig(m / MM(f))} / {V / 1000:.6g} = {sig(M)} M."])
    if v == 1:
        M0, V = nice(rng, 0.1, 2, 2), nice(rng, 100, 1000, 0)
        ans = M0 * V / 1000 * MM(f)
        return prob("Solutions", 3, f"How many grams of {pf(f)} are needed to make {V} mL of a {M0} M solution?", ans, "g",
                    [f"moles = M x V = {M0} x {V / 1000:.6g} L = {sig(M0 * V / 1000)} mol.", mm_steps(f), f"mass = {sig(M0 * V / 1000)} x {sig(MM(f), 4)} = {sig(ans)} g."])
    M0, m = nice(rng, 0.1, 2, 2), nice(rng, 2, 40, 1)
    ans = m / MM(f) / M0 * 1000
    return prob("Solutions", 3, f"What volume (mL) of a {M0} M {pf(f)} solution contains {m} g of {pf(f)}?", ans, "mL",
                [mm_steps(f), f"moles = {m} / {sig(MM(f), 4)} = {sig(m / MM(f))} mol.", f"V = moles / M = {sig(m / MM(f))} / {M0} = {sig(m / MM(f) / M0, 4)} L = {sig(ans)} mL."])


def t_dilution(rng, k):
    v = k % 3
    if v == 0:
        M1, M2, V2 = rng.choice([12.0, 6.0, 3.0, 18.0, 2.0]), nice(rng, 0.1, 1.0, 2), nice(rng, 100, 1000, 0)
        ans = M2 * V2 / M1
        return prob("Solutions", 3, f"How many mL of {M1} M stock solution are needed to prepare {V2} mL of {M2} M solution?", ans, "mL",
                    ["Use M₁V₁ = M₂V₂ and solve for V₁ = M₂V₂ / M₁.", f"V₁ = ({M2} x {V2}) / {M1} = {sig(ans)} mL."])
    if v == 1:
        M1, V1, V2 = rng.choice([6.00, 3.00, 12.0, 2.00]), nice(rng, 5, 50, 0), nice(rng, 100, 500, 0)
        ans = M1 * V1 / V2
        return prob("Solutions", 3, f"{V1} mL of {M1} M HCl is diluted with water to a final volume of {V2} mL. What is the new molarity?", ans, "M",
                    ["Moles of solute are unchanged: M₁V₁ = M₂V₂.", f"M₂ = ({M1} x {V1}) / {V2} = {sig(ans)} M."])
    M1, M2, V1 = rng.choice([6.00, 3.00, 2.00, 1.00]), rng.choice([0.100, 0.250, 0.500]), nice(rng, 10, 50, 0)
    ans = M1 * V1 / M2
    return prob("Solutions", 3, f"{V1} mL of {M1} M solution is diluted to {M2} M. What is the final volume in mL?", ans, "mL",
                ["M₁V₁ = M₂V₂, so V₂ = M₁V₁ / M₂.", f"V₂ = ({M1} x {V1}) / {M2} = {sig(ans)} mL."])


TIT = [("HCl", "NaOH", 1, 1), ("H2SO4", "NaOH", 1, 2), ("HCl", "Ba(OH)2", 2, 1), ("HNO3", "KOH", 1, 1), ("H3PO4", "NaOH", 1, 3)]


def t_titration(rng, k):
    a, b, na, nb = TIT[k % len(TIT)]
    Ma, Va, Mb = nice(rng, 0.05, 0.5, 3), nice(rng, 10, 50, 1), nice(rng, 0.05, 0.5, 3)
    n_a = Ma * Va / 1000
    n_b = n_a * nb / na
    ratio = f"{na} {pf(a)} : {nb} {pf(b)}"
    if k % 2 == 0:
        ans = n_b / Mb * 1000
        return prob("Solutions", 4, f"What volume (mL) of {Mb} M {pf(b)} is needed to completely neutralize {Va} mL of {Ma} M {pf(a)}?", ans, "mL",
                    [f"Moles of {pf(a)} = {Ma} x {Va / 1000:.6g} L = {sig(n_a)} mol.", f"Neutralization ratio is {ratio}, so moles {pf(b)} = {sig(n_a)} x {nb}/{na} = {sig(n_b)} mol.",
                     f"Volume = {sig(n_b)} / {Mb} = {sig(n_b / Mb, 4)} L = {sig(ans)} mL."])
    Vb = nice(rng, 10, 60, 1)
    n_b = Mb * Vb / 1000
    n_a = n_b * na / nb
    ans = n_a / (Va / 1000)
    return prob("Solutions", 4, f"{Va} mL of {pf(a)} solution is neutralized by {Vb} mL of {Mb} M {pf(b)}. What is the molarity of the {pf(a)}?", ans, "M",
                [f"Moles of {pf(b)} = {Mb} x {Vb / 1000:.6g} L = {sig(n_b)} mol.", f"Ratio is {ratio}, so moles {pf(a)} = {sig(n_b)} x {na}/{nb} = {sig(n_a)} mol.",
                 f"M = {sig(n_a)} / {Va / 1000:.6g} L = {sig(ans)} M."])


def t_massmolal(rng, k):
    f = SOL[(k + 1) % len(SOL)]
    if k % 2 == 0:
        ms, mv = nice(rng, 5, 40, 1), nice(rng, 100, 400, 0)
        return prob("Solutions", 4, f"{ms} g of {pf(f)} is dissolved in {mv} g of water. What is the mass percent of {pf(f)} in the solution?",
                    ms / (ms + mv) * 100, "%", [f"Mass of solution = {ms} + {mv} = {ms + mv} g.", f"% = {ms} / {ms + mv} x 100 = {sig(ms / (ms + mv) * 100)}%."])
    ms, mv = nice(rng, 5, 60, 1), nice(rng, 100, 500, 0)
    ans = ms / MM(f) / (mv / 1000)
    return prob("Solutions", 4, f"{ms} g of {pf(f)} is dissolved in {mv} g of water. What is the molality (mol/kg)?", ans, "m",
                [mm_steps(f), f"moles = {ms} / {sig(MM(f), 4)} = {sig(ms / MM(f))} mol.", f"kg solvent = {mv / 1000:.6g}.", f"m = {sig(ms / MM(f))} / {mv / 1000:.6g} = {sig(ans)} mol/kg."])


COLL = [("NaCl", 2), ("C6H12O6", 1), ("CaCl2", 3), ("C12H22O11", 1), ("KBr", 2)]


def t_colligative(rng, k):
    f, i = COLL[k % len(COLL)]
    ms, mw = nice(rng, 5, 40, 1), nice(rng, 100, 500, 0)
    molal = ms / MM(f) / (mw / 1000)
    if k % 2 == 0:
        ans = i * 1.86 * molal
        return prob("Solutions", 4, f"{ms} g of {pf(f)} (van't Hoff factor i = {i}) is dissolved in {mw} g of water (K_f = 1.86 °C·kg/mol). By how many °C is the freezing point lowered?",
                    ans, "°C", [mm_steps(f), f"molality = ({ms}/{sig(MM(f), 4)}) / {mw / 1000:.6g} kg = {sig(molal)} m.", f"ΔT_f = i K_f m = {i} x 1.86 x {sig(molal)} = {sig(ans)} °C."])
    ans = 100 + i * 0.512 * molal
    return prob("Solutions", 4, f"{ms} g of {pf(f)} (i = {i}) is dissolved in {mw} g of water (K_b = 0.512 °C·kg/mol). What is the boiling point of the solution in °C?",
                ans, "°C", [mm_steps(f), f"molality = ({ms}/{sig(MM(f), 4)}) / {mw / 1000:.6g} kg = {sig(molal)} m.", f"ΔT_b = {i} x 0.512 x {sig(molal)} = {sig(i * 0.512 * molal)} °C; boiling point = 100 + ΔT_b = {sig(ans, 4)} °C."], rel=0.002)


def t_osmotic(rng, k):
    M, Tc = nice(rng, 0.05, 0.5, 2), nice(rng, 5, 40, 0)
    ans = M * R_ATM * (Tc + 273.15)
    return prob("Solutions", 4, f"What is the osmotic pressure (atm) of a {M} M glucose solution (a nonelectrolyte) at {Tc} °C?", ans, "atm",
                ["π = i M R T with i = 1, R = 0.08206 L·atm/(mol·K).", f"T = {Tc} + 273.15 = {sig(Tc + 273.15, 4)} K.", f"π = {M} x 0.08206 x {sig(Tc + 273.15, 4)} = {sig(ans)} atm."])


# ---------------- Gases ----------------
def t_idealgas(rng, k):
    v = k % 4
    n, Tc, P, V = nice(rng, 0.2, 3, 2), nice(rng, 0, 100, 0), nice(rng, 0.5, 3, 2), nice(rng, 1, 30, 1)
    T = Tc + 273.15
    K = f"T = {Tc} + 273.15 = {sig(T, 4)} K."
    if v == 0:
        a = n * R_ATM * T / P
        return prob("Gases", 3, f"What volume (L) does {n} mol of an ideal gas occupy at {P} atm and {Tc} °C?", a, "L", [K, "V = nRT / P.", f"V = ({n})(0.08206)({sig(T, 4)}) / {P} = {sig(a)} L."])
    if v == 1:
        a = n * R_ATM * T / V
        return prob("Gases", 3, f"What is the pressure (atm) of {n} mol of an ideal gas in a {V} L container at {Tc} °C?", a, "atm", [K, "P = nRT / V.", f"P = ({n})(0.08206)({sig(T, 4)}) / {V} = {sig(a)} atm."])
    if v == 2:
        a = P * V / (R_ATM * T)
        return prob("Gases", 3, f"How many moles of an ideal gas are in {V} L at {P} atm and {Tc} °C?", a, "mol", [K, "n = PV / RT.", f"n = ({P})({V}) / ((0.08206)({sig(T, 4)})) = {sig(a)} mol."])
    a = P * V / (n * R_ATM)
    return prob("Gases", 3, f"{n} mol of an ideal gas occupies {V} L at {P} atm. What is its temperature in kelvin?", a, "K", ["T = PV / nR.", f"T = ({P})({V}) / (({n})(0.08206)) = {sig(a, 4)} K."])


def t_gaslaws(rng, k):
    v = k % 4
    if v == 0:
        P1, V1, P2 = nice(rng, 0.8, 3, 2), nice(rng, 2, 12, 1), nice(rng, 0.4, 6, 2)
        a = P1 * V1 / P2
        return prob("Gases", 3, f"A gas occupies {V1} L at {P1} atm. What is its volume (L) at {P2} atm if temperature and amount are constant?", a, "L", ["Boyle's law: P₁V₁ = P₂V₂.", f"V₂ = ({P1})({V1}) / {P2} = {sig(a)} L."])
    if v == 1:
        V1, T1, T2 = nice(rng, 1, 10, 1), nice(rng, 0, 40, 0), nice(rng, 50, 200, 0)
        a = V1 * (T2 + 273.15) / (T1 + 273.15)
        return prob("Gases", 3, f"A gas occupies {V1} L at {T1} °C. What is its volume (L) at {T2} °C at constant pressure?", a, "L",
                    ["Charles's law (kelvin!): V₁/T₁ = V₂/T₂.", f"T₁ = {sig(T1 + 273.15, 4)} K, T₂ = {sig(T2 + 273.15, 4)} K.", f"V₂ = {V1} x {sig(T2 + 273.15, 4)} / {sig(T1 + 273.15, 4)} = {sig(a)} L."])
    if v == 2:
        P1, V1, T1, P2, T2 = nice(rng, 0.8, 2, 2), nice(rng, 2, 12, 1), nice(rng, 0, 40, 0), nice(rng, 1, 4, 2), nice(rng, 20, 120, 0)
        a = P1 * V1 * (T2 + 273.15) / ((T1 + 273.15) * P2)
        return prob("Gases", 3, f"A gas occupies {V1} L at {P1} atm and {T1} °C. What is its volume (L) at {P2} atm and {T2} °C?", a, "L",
                    ["Combined gas law: P₁V₁/T₁ = P₂V₂/T₂ (kelvin).", f"T₁ = {sig(T1 + 273.15, 4)} K, T₂ = {sig(T2 + 273.15, 4)} K.", f"V₂ = ({P1})({V1})({sig(T2 + 273.15, 4)}) / (({sig(T1 + 273.15, 4)})({P2})) = {sig(a)} L."])
    P1, T1, T2 = nice(rng, 1, 3, 2), nice(rng, 0, 30, 0), nice(rng, 50, 150, 0)
    a = P1 * (T2 + 273.15) / (T1 + 273.15)
    return prob("Gases", 3, f"A sealed rigid container holds gas at {P1} atm and {T1} °C. What is the pressure (atm) after heating to {T2} °C?", a, "atm",
                ["Gay-Lussac: P₁/T₁ = P₂/T₂ (kelvin).", f"P₂ = {P1} x {sig(T2 + 273.15, 4)} / {sig(T1 + 273.15, 4)} = {sig(a)} atm."])


GASES = ["He", "Ne", "N2", "O2", "CO2", "Ar"]


def t_dalton(rng, k):
    sel = rng.sample(GASES, 3 if k % 2 else 2)
    ns = [nice(rng, 0.5, 4, 2) for _ in sel]
    Pt = nice(rng, 1, 5, 2)
    tot = sum(ns)
    lst = ", ".join(f"{n} mol {pf(g)}" for n, g in zip(ns, sel))
    a = ns[0] / tot * Pt
    return prob("Gases", 3, f"A mixture contains {lst}, with a total pressure of {Pt} atm. What is the partial pressure (atm) of {pf(sel[0])}?", a, "atm",
                [f"Total moles = {sig(tot)} mol.", f"Mole fraction of {pf(sel[0])} = {ns[0]} / {sig(tot)} = {sig(ns[0] / tot, 4)}.", f"P = X x P_total = {sig(ns[0] / tot, 4)} x {Pt} = {sig(a)} atm."])


DG = ["N2", "O2", "CO2", "CH4", "NH3", "He"]


def t_gasdensity(rng, k):
    g = DG[k % len(DG)]
    P, Tc = nice(rng, 0.8, 2, 2), nice(rng, 0, 100, 0)
    T = Tc + 273.15
    d = P * MM(g) / (R_ATM * T)
    if k % 2 == 0:
        return prob("Gases", 4, f"What is the density (g/L) of {pf(g)} gas at {P} atm and {Tc} °C?", d, "g/L",
                    [mm_steps(g), f"T = {sig(T, 4)} K.", f"d = PM / RT = ({P})({sig(MM(g), 4)}) / ((0.08206)({sig(T, 4)})) = {sig(d)} g/L."])
    d3 = float(f"{d:.3g}")
    return prob("Gases", 4, f"A gas has a density of {d3} g/L at {P} atm and {Tc} °C. What is its molar mass (g/mol)?", d3 * R_ATM * T / P, "g/mol",
                ["Rearrange d = PM/RT to M = dRT / P.", f"T = {sig(T, 4)} K.", f"M = ({d3})(0.08206)({sig(T, 4)}) / {P} = {sig(d3 * R_ATM * T / P)} g/mol."], rel=0.015)


GR = [("H2", "O2"), ("He", "CH4"), ("NH3", "HCl"), ("H2", "CO2"), ("He", "Ar"), ("CH4", "SO2"), ("N2", "Cl2")]


def t_graham(rng, k):
    a, b = GR[k % len(GR)]
    ans = sqrt(MM(b) / MM(a))
    return prob("Gases", 4, f"How many times faster does {pf(a)} effuse than {pf(b)} under the same conditions?", ans, "times",
                ["Graham's law: rate₁/rate₂ = √(M₂/M₁).", f"M({pf(a)}) = {sig(MM(a), 4)}, M({pf(b)}) = {sig(MM(b), 4)} g/mol.", f"√({sig(MM(b), 4)}/{sig(MM(a), 4)}) = {sig(ans)}."])


# ---------------- Thermochemistry ----------------
METALS = [("iron", 0.449), ("aluminum", 0.897), ("copper", 0.385), ("lead", 0.129)]


def t_calorimetry(rng, k):
    v = k % 4
    m, T1 = nice(rng, 50, 500, 0), nice(rng, 10, 30, 0)
    T2 = T1 + nice(rng, 10, 60, 0)
    if v == 0:
        q = m * 4.184 * (T2 - T1) / 1000
        return prob("Thermochemistry", 3, f"How much heat (kJ) is needed to warm {m} g of water from {T1} °C to {T2} °C? (c = 4.184 J/g·°C)", q, "kJ",
                    ["q = m c ΔT.", f"ΔT = {T2} − {T1} = {T2 - T1} °C.", f"q = {m} x 4.184 x {T2 - T1} = {sig(q * 1000)} J = {sig(q)} kJ."])
    if v == 1:
        q = nice(rng, 5, 60, 1)
        ans = T1 + q * 1000 / (m * 4.184)
        return prob("Thermochemistry", 3, f"{q} kJ of heat is added to {m} g of water at {T1} °C. What is the final temperature (°C)? (c = 4.184 J/g·°C)", ans, "°C",
                    ["ΔT = q / (m c) with q in joules.", f"ΔT = {q * 1000} / ({m} x 4.184) = {sig(q * 1000 / (m * 4.184))} °C.", f"T_final = {T1} + {sig(q * 1000 / (m * 4.184))} = {sig(ans, 4)} °C."], rel=0.005)
    if v == 2:
        q = nice(rng, 5, 60, 1)
        dT = T2 - T1
        ans = q * 1000 / (4.184 * dT)
        return prob("Thermochemistry", 3, f"What mass (g) of water absorbs {q} kJ when its temperature rises by {dT} °C? (c = 4.184 J/g·°C)", ans, "g",
                    ["m = q / (c ΔT) with q in joules.", f"m = {q * 1000} / (4.184 x {dT}) = {sig(ans)} g."])
    name, c = METALS[(k // 4) % len(METALS)]
    q = m * c * (T2 - T1)
    return prob("Thermochemistry", 3, f"How much heat (J) is needed to warm {m} g of {name} (c = {c} J/g·°C) from {T1} °C to {T2} °C?", q, "J",
                ["q = m c ΔT.", f"q = {m} x {c} x {T2 - T1} = {sig(q)} J."])


def t_phase(rng, k):
    m = nice(rng, 10, 300, 0)
    n = m / chem.molar_mass("H2O")
    if k % 2 == 0:
        return prob("Thermochemistry", 3, f"How much heat (kJ) is needed to melt {m} g of ice at 0 °C? (ΔH_fus = 6.01 kJ/mol)", n * 6.01, "kJ",
                    [mm_steps("H2O"), f"moles = {m} / {sig(MM('H2O'), 4)} = {sig(n)} mol.", f"q = n ΔH_fus = {sig(n)} x 6.01 = {sig(n * 6.01)} kJ."])
    return prob("Thermochemistry", 3, f"How much heat (kJ) is needed to vaporize {m} g of water at 100 °C? (ΔH_vap = 40.7 kJ/mol)", n * 40.7, "kJ",
                [mm_steps("H2O"), f"moles = {m} / {sig(MM('H2O'), 4)} = {sig(n)} mol.", f"q = n ΔH_vap = {sig(n)} x 40.7 = {sig(n * 40.7)} kJ."])


HF = [("CH4(g) + 2 O₂(g) → CO₂(g) + 2 H₂O(l)", {"CH4": -74.8, "CO2": -393.5, "H2O": -285.8}, [(1, "CH4"), (2, "O2")], [(1, "CO2"), (2, "H2O")], "ΔH°f (kJ/mol): CH₄ −74.8, CO₂ −393.5, H₂O(l) −285.8"),
      ("C₃H₈(g) + 5 O₂(g) → 3 CO₂(g) + 4 H₂O(l)", {"C3H8": -103.8, "CO2": -393.5, "H2O": -285.8}, [(1, "C3H8"), (5, "O2")], [(3, "CO2"), (4, "H2O")], "ΔH°f (kJ/mol): C₃H₈ −103.8, CO₂ −393.5, H₂O(l) −285.8"),
      ("CaCO₃(s) → CaO(s) + CO₂(g)", {"CaCO3": -1206.9, "CaO": -635.1, "CO2": -393.5}, [(1, "CaCO3")], [(1, "CaO"), (1, "CO2")], "ΔH°f (kJ/mol): CaCO₃ −1206.9, CaO −635.1, CO₂ −393.5"),
      ("N₂(g) + 3 H₂(g) → 2 NH₃(g)", {"NH3": -46.1}, [(1, "N2"), (3, "H2")], [(2, "NH3")], "ΔH°f (kJ/mol): NH₃ −46.1 (elements in standard state are 0)"),
      ("C₂H₄(g) + H₂(g) → C₂H₆(g)", {"C2H4": 52.4, "C2H6": -84.7}, [(1, "C2H4"), (1, "H2")], [(1, "C2H6")], "ΔH°f (kJ/mol): C₂H₄ +52.4, C₂H₆ −84.7"),
      ("2 SO₂(g) + O₂(g) → 2 SO₃(g)", {"SO2": -296.8, "SO3": -395.7}, [(2, "SO2"), (1, "O2")], [(2, "SO3")], "ΔH°f (kJ/mol): SO₂ −296.8, SO₃ −395.7")]


def t_formation(rng, k):
    text, d, rs, ps, data = HF[k % len(HF)]
    prod = sum(c * d.get(f, 0.0) for c, f in ps)
    reac = sum(c * d.get(f, 0.0) for c, f in rs)
    ans = prod - reac
    return prob("Thermochemistry", 4, f"Calculate ΔH°rxn (kJ) for {text}. {data}.", ans, "kJ",
                ["ΔH°rxn = Σ n ΔH°f(products) − Σ n ΔH°f(reactants); elements in their standard state are 0.",
                 f"Products: {sig(prod, 5)} kJ.   Reactants: {sig(reac, 5)} kJ.", f"ΔH°rxn = {sig(prod, 5)} − ({sig(reac, 5)}) = {sig(ans, 5)} kJ."], rel=0.005, n=4)


HESS = [("C(s) + O₂(g) → CO₂(g), ΔH = −393.5 kJ; CO(g) + ½ O₂(g) → CO₂(g), ΔH = −283.0 kJ. Find ΔH for C(s) + ½ O₂(g) → CO(g).", -393.5 + 283.0,
         "Keep reaction 1; reverse reaction 2 (sign flips to +283.0), then add: −393.5 + 283.0."),
        ("N₂(g) + O₂(g) → 2 NO(g), ΔH = +180.5 kJ; 2 NO(g) + O₂(g) → 2 NO₂(g), ΔH = −114.1 kJ. Find ΔH for N₂(g) + 2 O₂(g) → 2 NO₂(g).", 180.5 - 114.1,
         "The two reactions add directly (2 NO cancels): 180.5 + (−114.1)."),
        ("2 H₂(g) + O₂(g) → 2 H₂O(g), ΔH = −483.6 kJ; H₂O(l) → H₂O(g), ΔH = +44.0 kJ. Find ΔH for 2 H₂(g) + O₂(g) → 2 H₂O(l).", -483.6 - 2 * 44.0,
         "Reverse the second reaction and double it (ΔH = −88.0), then add to the first: −483.6 − 88.0."),
        ("C(graphite) + O₂(g) → CO₂(g), ΔH = −393.5 kJ; C(diamond) + O₂(g) → CO₂(g), ΔH = −395.4 kJ. Find ΔH for C(graphite) → C(diamond).", -393.5 + 395.4,
         "Keep reaction 1, reverse reaction 2 (+395.4), add: −393.5 + 395.4.")]


def t_hess(rng, k):
    text, ans, how = HESS[k % len(HESS)]
    return prob("Thermochemistry", 4, f"Use Hess's law: {text}", ans, "kJ", ["Arrange the given reactions so they sum to the target.", how, f"ΔH = {sig(ans, 4)} kJ."], rel=0.005, abs_=0.05, n=4)


# ---------------- Electronic structure ----------------
def t_light(rng, k):
    v = k % 4
    if v == 0:
        lam = rng.choice([400, 450, 520, 589, 650, 700])
        nu = C / (lam * 1e-9)
        return prob("Electronic Structure & Periodicity", 3, f"What is the frequency (Hz) of light with a wavelength of {lam} nm?", nu, "Hz",
                    ["c = λν, so ν = c / λ.", f"λ = {lam} nm = {lam}e-9 m.", f"ν = 3.00e8 / {lam}e-9 = {sig(nu)} Hz."], sci=True)
    if v == 1:
        lam = rng.choice([400, 450, 520, 589, 650, 700])
        E = H * C / (lam * 1e-9)
        return prob("Electronic Structure & Periodicity", 3, f"What is the energy (J) of one photon of light with a wavelength of {lam} nm?", E, "J",
                    ["E = hc / λ with h = 6.626e-34 J·s and c = 3.00e8 m/s.", f"E = (6.626e-34)(3.00e8) / ({lam}e-9) = {sig(E)} J."], sci=True)
    if v == 2:
        nu = rng.choice([4.5, 5.0, 6.0, 7.0, 7.5]) * 1e14
        lam = C / nu * 1e9
        return prob("Electronic Structure & Periodicity", 3, f"What is the wavelength (nm) of light with a frequency of {nu:.1e} Hz?", lam, "nm",
                    ["λ = c / ν.", f"λ = 3.00e8 / {nu:.1e} = {sig(C / nu)} m = {sig(lam)} nm."])
    nu = rng.choice([4.5, 5.0, 6.0, 7.0, 7.5]) * 1e14
    return prob("Electronic Structure & Periodicity", 3, f"What is the energy (J) of a photon with a frequency of {nu:.1e} Hz?", H * nu, "J",
                ["E = hν with h = 6.626e-34 J·s.", f"E = (6.626e-34)({nu:.1e}) = {sig(H * nu)} J."], sci=True)


BOHR = [(3, 2), (4, 2), (5, 2), (4, 3), (2, 1), (6, 2)]


def t_bohr(rng, k):
    if k % 3 == 0:
        n = [1, 2, 3, 4, 5][(k // 3) % 5]
        return prob("Electronic Structure & Periodicity", 3, f"What is the energy (J) of the electron in the n = {n} level of a hydrogen atom?", -RH / n ** 2, "J",
                    ["Eₙ = −2.178e-18 J / n².", f"E = −2.178e-18 / {n}² = {sig(-RH / n ** 2)} J."], sci=True)
    ni, nf = BOHR[(k // 3 * 2 + k % 3) % len(BOHR)]
    dE = RH * (1 / nf ** 2 - 1 / ni ** 2)
    lam = H * C / dE * 1e9
    if k % 3 == 1:
        return prob("Electronic Structure & Periodicity", 3, f"An electron in a hydrogen atom falls from n = {ni} to n = {nf}. What is the energy (J) of the emitted photon?", dE, "J",
                    ["ΔE = 2.178e-18 (1/n_f² − 1/n_i²), take the magnitude for the photon.", f"= 2.178e-18 x (1/{nf ** 2} − 1/{ni ** 2}) = {sig(dE)} J."], sci=True)
    return prob("Electronic Structure & Periodicity", 4, f"An electron in a hydrogen atom falls from n = {ni} to n = {nf}. What is the wavelength (nm) of the emitted photon?", lam, "nm",
                [f"ΔE = 2.178e-18 (1/{nf ** 2} − 1/{ni ** 2}) = {sig(dE)} J.", "λ = hc / ΔE.", f"λ = (6.626e-34)(3.00e8) / {sig(dE)} = {sig(lam / 1e9)} m = {sig(lam)} nm."], rel=0.015)


UNP = [("N", 3), ("O", 2), ("Fe", 4), ("Cu", 1), ("Cr", 6), ("Mn", 5), ("Ne", 0), ("Cl", 1), ("S", 2), ("Zn", 0), ("Ni", 2), ("Co", 3), ("V", 3), ("Ti", 2), ("Si", 2), ("P", 3), ("Al", 1)]
VAL = [("Na", 1), ("Mg", 2), ("Al", 3), ("Si", 4), ("P", 5), ("S", 6), ("Cl", 7), ("Ar", 8), ("Ca", 2), ("Br", 7), ("Se", 6), ("Sr", 2)]
D3 = [("Fe", 6), ("Zn", 10), ("Cu", 10), ("Cr", 5), ("Mn", 5), ("Ni", 8), ("Co", 7), ("V", 3)]


def t_econfig(rng, k):
    v = k % 3
    if v == 0:
        s, n = UNP[(k // 3) % len(UNP)]
        return prob("Electronic Structure & Periodicity", 3, f"How many unpaired electrons are in a ground-state {chem.NAME[s].lower()} atom?", n, "",
                    ["Write the ground-state electron configuration (Aufbau order; note exceptions Cr and Cu).", "Apply Hund's rule: fill degenerate orbitals singly before pairing.", f"Unpaired electrons: {n}."], rel=0)
    if v == 1:
        s, n = VAL[(k // 3) % len(VAL)]
        return prob("Electronic Structure & Periodicity", 2, f"How many valence electrons does a {chem.NAME[s].lower()} atom have?", n, "",
                    ["For main-group elements, valence electrons = group number (groups 1–2) or group number − 10 (groups 13–18).", f"{s}: {n}."], rel=0)
    s, n = D3[(k // 3) % len(D3)]
    return prob("Electronic Structure & Periodicity", 3, f"How many electrons are in the 3d subshell of a ground-state {chem.NAME[s].lower()} atom?", n, "",
                ["Write the configuration [Ar] 4s² 3d^x (with Cr and Cu exceptions).", f"3d electrons for {s}: {n}."], rel=0)


# ---------------- Bonding ----------------
LP = [("H2O", 2), ("NH3", 1), ("CH4", 0), ("CO2", 0), ("SF4", 1), ("XeF4", 2), ("ClF3", 2), ("BF3", 0), ("PCl5", 0), ("SF6", 0), ("SO2", 1), ("BrF5", 1)]
ANG = [("CH4", 109.5), ("BF3", 120), ("CO2", 180), ("SF6", 90), ("BeCl2", 180), ("C2H4", 120)]


def t_vsepr(rng, k):
    if k % 4 != 3:
        f, n = LP[(k * 2 // 1) % len(LP)] if k < 6 else LP[k % len(LP)]
        return prob("Bonding & Geometry", 3, f"How many lone pairs are on the central atom of {pf(f)}?", n, "",
                    ["Count valence electrons and draw the Lewis structure.", "Lone pairs on the central atom = leftover electron pairs after bonding.", f"{pf(f)}: {n} lone pair(s)."], rel=0)
    f, a = ANG[(k // 4) % len(ANG)]
    return prob("Bonding & Geometry", 3, f"What is the ideal bond angle (degrees) around the central atom in {pf(f)}?", a, "°",
                ["Count electron groups around the central atom.", "Match to the VSEPR geometry: 2 → 180°, 3 → 120°, 4 → 109.5°, 6 → 90°.", f"{pf(f)}: {a}°."], rel=0, abs_=0.6, n=4)


FC = [(5, 0, 8), (6, 6, 2), (6, 4, 4), (7, 6, 2), (5, 2, 6), (6, 2, 6), (4, 0, 8), (7, 8, 0), (6, 4, 4), (5, 4, 4)]


def t_formal(rng, k):
    V, N, B = FC[k % len(FC)]
    fc = V - N - B // 2
    return prob("Bonding & Geometry", 3, f"An atom has {V} valence electrons, {N} nonbonding (lone-pair) electrons and shares {B} electrons in its bonds. What is its formal charge?", fc, "",
                ["Formal charge = V − N − B/2.", f"= {V} − {N} − {B}/2 = {fc}."], rel=0, abs_=0)


SP = [("C2H4", 5, 1), ("C2H2", 3, 2), ("CO2", 2, 2), ("HCN", 2, 2), ("N2", 1, 2), ("H2CO", 3, 1), ("C2H6", 7, 0), ("CH3CN", 5, 2)]


def t_sigmapi(rng, k):
    f, s, p = SP[k % len(SP)]
    which = "sigma (σ)" if (k // len(SP) + k) % 2 == 0 else "pi (π)"
    n = s if which.startswith("sigma") else p
    return prob("Bonding & Geometry", 4, f"How many {which} bonds are in a molecule of {pf(f)}?", n, "",
                ["Draw the Lewis structure; every bond has one σ bond.", "A double bond adds one π; a triple bond adds two π.", f"{pf(f)}: {s} σ and {p} π."], rel=0)


# ---------------- Kinetics ----------------
def t_firstorder(rng, k):
    v = k % 4
    if v == 0:
        kk = rng.choice([0.0231, 0.0462, 0.00693, 0.0139, 0.0990, 0.173])
        return prob("Kinetics", 4, f"A first-order reaction has k = {kk} s⁻¹. What is its half-life in seconds?", log(2) / kk, "s",
                    ["For first order, t½ = ln 2 / k = 0.693 / k.", f"t½ = 0.693 / {kk} = {sig(log(2) / kk)} s."])
    A0, kk, t = nice(rng, 0.1, 1.0, 2), rng.choice([0.005, 0.010, 0.020, 0.040]), nice(rng, 10, 120, 0)
    if v == 1:
        a = A0 * exp(-kk * t)
        return prob("Kinetics", 4, f"A first-order reaction has k = {kk} s⁻¹ and an initial concentration of {A0} M. What is [A] (M) after {t} s?", a, "M",
                    ["Integrated first-order law: [A] = [A]₀ e^(−kt).", f"kt = {kk} x {t} = {sig(kk * t)}.", f"[A] = {A0} x e^(−{sig(kk * t)}) = {sig(a)} M."])
    frac = rng.choice([0.5, 0.25, 0.10, 0.20, 0.05])
    if v == 2:
        tt = log(1 / frac) / kk
        return prob("Kinetics", 4, f"A first-order reaction has k = {kk} s⁻¹. How long (s) until the concentration falls to {frac} of its initial value?", tt, "s",
                    ["ln([A]₀/[A]) = kt, so t = ln(1/fraction) / k.", f"t = ln({1 / frac:.3g}) / {kk} = {sig(tt)} s."])
    a = A0 * exp(-kk * t)
    a3 = float(f"{a:.3g}")
    ans = log(A0 / a3) / t
    return prob("Kinetics", 4, f"A first-order reaction goes from {A0} M to {a3} M in {t} s. What is the rate constant k (s⁻¹)?", ans, "s⁻¹",
                ["ln([A]₀/[A]) = kt, so k = ln([A]₀/[A]) / t.", f"k = ln({A0}/{a3}) / {t} = {sig(ans)} s⁻¹."], rel=0.03)


ORD = [(1, 1), (2, 1), (1, 0), (0, 1), (2, 0), (1, 2)]


def t_rate(rng, k):
    m, n = ORD[k % len(ORD)]
    k0 = rng.choice([0.50, 1.2, 0.035, 2.5, 0.80])
    exps = [(0.10, 0.10), (0.20, 0.10), (0.10, 0.20), (0.20, 0.20)]
    rates = [k0 * a ** m * b ** n for a, b in exps]
    rows = "\n".join(f"Exp {i + 1}: [A] = {a:.2f} M, [B] = {b:.2f} M, initial rate = {r:.3e} M/s" for i, ((a, b), r) in enumerate(zip(exps, rates)))
    if k < 6:
        which = "A" if k % 2 == 0 else "B"
        order = m if which == "A" else n
        return prob("Kinetics", 4, f"Initial-rate data for A + B → products:\n{rows}\nWhat is the reaction order with respect to {which}?", order, "",
                    [f"Compare two experiments where only [{which}] changes (Exp {'1 and 2' if which == 'A' else '1 and 3'}).", f"Rate ratio = concentration ratio ^ order: {rates[1 if which == 'A' else 2] / rates[0]:.3g} = 2^x.",
                     f"x = {order}."], rel=0)
    return prob("Kinetics", 4, f"Initial-rate data for A + B → products (the rate law is rate = k[A]^{m}[B]^{n}):\n{rows}\nWhat is the rate constant k? (Give the number only.)", k0, "",
                ["Use any experiment: k = rate / ([A]^m [B]^n).", f"Exp 1: k = {rates[0]:.3e} / (0.10^{m} x 0.10^{n}) = {sig(k0)}."], rel=0.02)


def t_arrhenius(rng, k):
    T1 = nice(rng, 290, 320, 0)
    T2 = T1 + nice(rng, 15, 40, 0)
    Ea = nice(rng, 40, 120, 0)
    k1 = float(f"{10 ** rng.uniform(-5, -2):.3g}")
    k2 = float(f"{k1 * exp(Ea * 1000 / R_J * (1 / T1 - 1 / T2)):.3g}")
    ans = R_J * log(k2 / k1) / (1 / T1 - 1 / T2) / 1000
    return prob("Kinetics", 5, f"A reaction has rate constant {k1:.2e} s⁻¹ at {T1} K and {k2:.2e} s⁻¹ at {T2} K. What is the activation energy in kJ/mol?", ans, "kJ/mol",
                ["Use ln(k₂/k₁) = (Ea/R)(1/T₁ − 1/T₂) with R = 8.314 J/(mol·K).", f"ln({k2:.2e}/{k1:.2e}) = {sig(log(k2 / k1))}; (1/{T1} − 1/{T2}) = {sig(1 / T1 - 1 / T2)}.",
                 f"Ea = 8.314 x {sig(log(k2 / k1))} / {sig(1 / T1 - 1 / T2)} = {sig(ans * 1000)} J/mol = {sig(ans)} kJ/mol."], rel=0.03)


# ---------------- Equilibrium ----------------
KC = [("N2 + 3 H2 ⇌ 2 NH3", [("N2", 1), ("H2", 3)], [("NH3", 2)]), ("2 SO2 + O2 ⇌ 2 SO3", [("SO2", 2), ("O2", 1)], [("SO3", 2)]),
      ("H2 + I2 ⇌ 2 HI", [("H2", 1), ("I2", 1)], [("HI", 2)]), ("N2O4 ⇌ 2 NO2", [("N2O4", 1)], [("NO2", 2)]),
      ("PCl5 ⇌ PCl3 + Cl2", [("PCl5", 1)], [("PCl3", 1), ("Cl2", 1)])]


def t_kc(rng, k):
    text, rs, ps = KC[k % len(KC)]
    conc = {f: nice(rng, 0.05, 0.8, 2) for f, _ in rs + ps}
    num = math.prod(conc[f] ** c for f, c in ps)
    den = math.prod(conc[f] ** c for f, c in rs)
    K = num / den
    given = ", ".join(f"[{pf(f)}] = {conc[f]} M" for f, _ in rs + ps)
    return prob("Equilibrium", 4, f"For {pf(text)} at equilibrium: {given}. Calculate Kc.", K, "",
                ["Kc = [products]^coefficients / [reactants]^coefficients.", "Kc = " + "".join(f"[{pf(f)}]^{c} " if c > 1 else f"[{pf(f)}] " for f, c in ps).strip() + " / (" + "".join(f"[{pf(f)}]^{c} " if c > 1 else f"[{pf(f)}] " for f, c in rs).strip() + ")",
                 f"Kc = {sig(num, 4)} / {sig(den, 4)} = {sig(K)}."], sci=not 0.01 <= K < 1e4)


KP = [("N2 + 3 H2 ⇌ 2 NH3", -2), ("PCl5 ⇌ PCl3 + Cl2", 1), ("2 SO2 + O2 ⇌ 2 SO3", -1), ("N2O4 ⇌ 2 NO2", 1), ("H2 + I2 ⇌ 2 HI", 0)]


def t_kp(rng, k):
    text, dn = KP[k % len(KP)]
    Kc, T = nice(rng, 0.5, 50, 1), nice(rng, 300, 900, 0)
    Kp = Kc * (R_ATM * T) ** dn
    return prob("Equilibrium", 4, f"For {pf(text)}, Kc = {Kc} at {T} K. Calculate Kp.", Kp, "",
                ["Kp = Kc (RT)^Δn with R = 0.08206 and T in kelvin.", f"Δn = (moles gas products) − (moles gas reactants) = {dn}.", f"Kp = {Kc} x (0.08206 x {T})^{dn} = {sig(Kp)}."], sci=not 0.01 <= Kp < 1e4)


def t_ice(rng, k):
    if k % 2 == 0:
        K, c0 = rng.choice([25.0, 36.0, 49.0, 54.0, 16.0, 64.0]), rng.choice([0.10, 0.20, 0.50, 1.00])
        s = sqrt(K)
        x = c0 * s / (2 + s)
        return prob("Equilibrium", 5, f"H₂(g) + I₂(g) ⇌ 2 HI(g) has Kc = {K}. If a vessel starts with [H₂] = [I₂] = {c0} M and no HI, what is [HI] at equilibrium (M)?", 2 * x, "M",
                    ["ICE table: [H₂] = [I₂] = c₀ − x, [HI] = 2x.", f"K = (2x)² / (c₀ − x)² → 2x/(c₀ − x) = √K = {sig(s, 4)}.", f"x = c₀√K / (2 + √K) = {sig(x, 4)} M; [HI] = 2x = {sig(2 * x)} M."])
    K, c0 = rng.choice([0.0046, 0.010, 0.020, 0.050, 0.10, 0.20]), rng.choice([0.10, 0.20, 0.50, 1.00])
    x = (-K + sqrt(K * K + 16 * K * c0)) / 8
    return prob("Equilibrium", 5, f"N₂O₄(g) ⇌ 2 NO₂(g) has Kc = {K}. Starting with {c0} M N₂O₄ only, what is [NO₂] at equilibrium (M)?", 2 * x, "M",
                ["ICE: [N₂O₄] = c₀ − x, [NO₂] = 2x.", "K = (2x)² / (c₀ − x) → 4x² + Kx − K c₀ = 0.", f"x = (−K + √(K² + 16 K c₀)) / 8 = {sig(x, 4)} M; [NO₂] = 2x = {sig(2 * x)} M."], rel=0.02)


KSP = [("AgCl", 1.8e-10, 1, 1), ("Ca(OH)2", 5.5e-6, 1, 2), ("PbI2", 9.8e-9, 1, 2), ("BaSO4", 1.1e-10, 1, 1), ("Ag2CrO4", 1.1e-12, 2, 1), ("MgF2", 5.2e-11, 1, 2)]


def t_ksp(rng, k):
    f, ksp, m, n = KSP[k % len(KSP)]
    s = (ksp / (m ** m * n ** n)) ** (1 / (m + n))
    return prob("Equilibrium", 5, f"The Ksp of {pf(f)} is {ksp:.1e}. What is its molar solubility (mol/L) in pure water?", s, "mol/L",
                [f"Dissolution: {pf(f)}(s) ⇌ {m} cation + {n} anion; Ksp = ({m}s)^{m} ({n}s)^{n} = {m ** m * n ** n} s^{m + n}.", f"s = ({ksp:.1e} / {m ** m * n ** n})^(1/{m + n}) = {sig(s)} mol/L."], sci=True, rel=0.02)


# ---------------- Acids & bases ----------------
def t_ph_strong(rng, k):
    v = k % 3
    if v == 0:
        c, a = rng.choice([0.0010, 0.0050, 0.020, 0.050, 0.10, 0.25, 0.0025]), rng.choice(["HCl", "HNO3", "HBr"])
        return prob("Acids & Bases", 4, f"What is the pH of a {c} M {pf(a)} solution?", -log10(c), "", ["Strong acid: [H₃O⁺] = acid concentration.", f"pH = −log({c}) = {sig(-log10(c), 3)}."], rel=0, abs_=0.02)
    if v == 1:
        c, b, n = rng.choice([0.0010, 0.010, 0.050, 0.10]), rng.choice([("NaOH", 1), ("KOH", 1), ("Ba(OH)2", 2)]), None
        name, nOH = b
        oh = c * nOH
        ph = 14 - (-log10(oh))
        return prob("Acids & Bases", 4, f"What is the pH of a {c} M {pf(name)} solution?", ph, "", [f"[OH⁻] = {nOH} x {c} = {sig(oh)} M.", f"pOH = −log({sig(oh)}) = {sig(-log10(oh), 3)}.", f"pH = 14.00 − pOH = {sig(ph, 3)}."], rel=0, abs_=0.02)
    ph = nice(rng, 1.0, 6.0, 2)
    return prob("Acids & Bases", 4, f"A solution has a pH of {ph}. What is [H₃O⁺] in mol/L?", 10 ** -ph, "M", ["[H₃O⁺] = 10^(−pH).", f"= 10^(−{ph}) = {sig(10 ** -ph)} M."], sci=True, rel=0.02)


WEAK = [("acetic acid", 1.8e-5), ("formic acid", 1.8e-4), ("hydrofluoric acid", 6.8e-4), ("benzoic acid", 6.3e-5), ("nitrous acid", 4.5e-4)]


def t_weak(rng, k):
    name, Ka = WEAK[k % len(WEAK)]
    C0 = nice(rng, 0.05, 0.5, 3)
    x = (-Ka + sqrt(Ka * Ka + 4 * Ka * C0)) / 2
    if k % 2 == 0:
        return prob("Acids & Bases", 4, f"What is the pH of a {C0} M solution of {name} (Ka = {Ka:.1e})?", -log10(x), "",
                    ["HA ⇌ H⁺ + A⁻;  Ka = x² / (C − x).", f"Check the approximation: x ≈ √(Ka C) = {sig(sqrt(Ka * C0))} (use the quadratic x² + Ka x − Ka C = 0 if this is over 5% of C).", f"x = {sig(x)} M, so pH = −log x = {sig(-log10(x), 3)}."], rel=0, abs_=0.05)
    return prob("Acids & Bases", 5, f"What is the percent ionization of a {C0} M solution of {name} (Ka = {Ka:.1e})?", x / C0 * 100, "%",
                ["Find [H⁺] = x from Ka = x² / (C − x).", f"x = {sig(x)} M.", f"% ionization = x / C x 100 = {sig(x / C0 * 100)}%."], rel=0.05)


BUF = [("acetic acid / acetate", 4.74), ("formic acid / formate", 3.75), ("hydrofluoric acid / fluoride", 3.17), ("benzoic acid / benzoate", 4.20), ("ammonium / ammonia", 9.25)]


def t_hh(rng, k):
    name, pka = BUF[k % len(BUF)]
    a, b = nice(rng, 0.05, 0.5, 2), nice(rng, 0.05, 0.5, 2)
    ph = pka + log10(b / a)
    return prob("Acids & Bases", 5, f"A buffer contains {a} M of the acid and {b} M of the conjugate base ({name}, pKa = {pka}). What is its pH?", ph, "",
                ["Henderson–Hasselbalch: pH = pKa + log([base]/[acid]).", f"pH = {pka} + log({b}/{a}) = {sig(ph, 3)}."], rel=0, abs_=0.03)


def t_mixing(rng, k):
    for _ in range(50):
        Ma, Va, Mb, Vb = nice(rng, 0.05, 0.5, 2), nice(rng, 10, 100, 0), nice(rng, 0.05, 0.5, 2), nice(rng, 10, 100, 0)
        na, nb = Ma * Va / 1000, Mb * Vb / 1000
        if abs(na - nb) / max(na, nb) < 0.15:
            continue
        V = (Va + Vb) / 1000
        if na > nb:
            c = (na - nb) / V
            ph = -log10(c)
            steps = f"Excess H⁺ = {sig(na)} − {sig(nb)} = {sig(na - nb)} mol; [H⁺] = {sig(c)} M; pH = {sig(ph, 3)}."
        else:
            c = (nb - na) / V
            ph = 14 + log10(c)
            steps = f"Excess OH⁻ = {sig(nb)} − {sig(na)} = {sig(nb - na)} mol; [OH⁻] = {sig(c)} M; pOH = {sig(-log10(c), 3)}; pH = {sig(ph, 3)}."
        return prob("Acids & Bases", 5, f"{Va} mL of {Ma} M HCl is mixed with {Vb} mL of {Mb} M NaOH. What is the pH of the resulting solution?", ph, "",
                    [f"Moles H⁺ = {Ma} x {Va / 1000:.6g} = {sig(na)} mol; moles OH⁻ = {Mb} x {Vb / 1000:.6g} = {sig(nb)} mol.", f"Total volume = {Va + Vb} mL = {V} L.", steps], rel=0, abs_=0.05)
    return None


def t_kw(rng, k):
    v = k % 3
    if v == 0:
        name, Ka = WEAK[k % len(WEAK)]
        return prob("Acids & Bases", 4, f"The Ka of {name} is {Ka:.1e}. What is Kb of its conjugate base?", 1e-14 / Ka, "", ["Ka x Kb = K_w = 1.0 x 10⁻¹⁴.", f"Kb = 1.0e-14 / {Ka:.1e} = {sig(1e-14 / Ka)}."], sci=True, rel=0.02)
    if v == 1:
        ph = nice(rng, 2.0, 12.0, 2)
        return prob("Acids & Bases", 4, f"A solution has pH {ph}. What is its pOH?", 14 - ph, "", ["pH + pOH = 14.00.", f"pOH = 14.00 − {ph} = {sig(14 - ph, 3)}."], rel=0, abs_=0.02)
    h = rng.choice([1e-3, 2.5e-5, 4.0e-9, 6.3e-11, 1.0e-2, 3.2e-4])
    return prob("Acids & Bases", 4, f"[H₃O⁺] = {h:.1e} M. What is [OH⁻] in mol/L?", 1e-14 / h, "M", ["K_w = [H₃O⁺][OH⁻] = 1.0 x 10⁻¹⁴.", f"[OH⁻] = 1.0e-14 / {h:.1e} = {sig(1e-14 / h)} M."], sci=True, rel=0.02)


# ---------------- Thermodynamics ----------------
def t_gibbs(rng, k):
    v = k % 4
    if v == 0:
        dH, dS, T = nice(rng, -250, 150, 1), nice(rng, -200, 250, 0), rng.choice([298, 350, 400, 500, 600])
        dG = dH - T * dS / 1000
        return prob("Thermodynamics", 5, f"For a reaction ΔH = {dH} kJ and ΔS = {dS} J/K. Calculate ΔG (kJ) at {T} K.", dG, "kJ",
                    ["ΔG = ΔH − TΔS; convert ΔS to kJ/K.", f"TΔS = {T} x {dS} / 1000 = {sig(T * dS / 1000)} kJ.", f"ΔG = {dH} − ({sig(T * dS / 1000)}) = {sig(dG)} kJ."], rel=0.01, abs_=0.3)
    if v == 1:
        dH, dS = nice(rng, 20, 180, 0), nice(rng, 60, 300, 0)
        return prob("Thermodynamics", 5, f"A reaction has ΔH = +{dH} kJ and ΔS = +{dS} J/K. Above what temperature (K) does it become spontaneous?", dH * 1000 / dS, "K",
                    ["Spontaneous when ΔG < 0; at the crossover ΔG = 0, so T = ΔH / ΔS.", f"T = ({dH} x 1000 J) / {dS} J/K = {sig(dH * 1000 / dS)} K."])
    if v == 2:
        dG = nice(rng, -30, 30, 1)
        K = exp(-dG * 1000 / (R_J * 298))
        return prob("Thermodynamics", 5, f"A reaction has ΔG° = {dG} kJ/mol at 298 K. What is the equilibrium constant K?", K, "", ["ΔG° = −RT ln K → K = e^(−ΔG°/RT) (ΔG° in J).", f"K = exp(−({dG} x 1000) / (8.314 x 298)) = {sig(K)}."], sci=True, rel=0.03)
    K = float(f"{10 ** rng.uniform(-6, 6):.2g}")
    dG = -R_J * 298 * log(K) / 1000
    return prob("Thermodynamics", 5, f"A reaction has K = {K:.1e} at 298 K. What is ΔG° in kJ/mol?", dG, "kJ/mol", ["ΔG° = −RT ln K.", f"ΔG° = −(8.314)(298) ln({K:.1e}) / 1000 = {sig(dG)} kJ/mol."], rel=0.01, abs_=0.3)


SENT = [("N₂(g) + 3 H₂(g) → 2 NH₃(g)", {"N2": 191.6, "H2": 130.7, "NH3": 192.5}, [(1, "N2"), (3, "H2")], [(2, "NH3")], "S° (J/mol·K): N₂ 191.6, H₂ 130.7, NH₃ 192.5"),
        ("2 SO₂(g) + O₂(g) → 2 SO₃(g)", {"SO2": 248.2, "O2": 205.1, "SO3": 256.8}, [(2, "SO2"), (1, "O2")], [(2, "SO3")], "S° (J/mol·K): SO₂ 248.2, O₂ 205.1, SO₃ 256.8"),
        ("CaCO₃(s) → CaO(s) + CO₂(g)", {"CaCO3": 92.9, "CaO": 39.8, "CO2": 213.8}, [(1, "CaCO3")], [(1, "CaO"), (1, "CO2")], "S° (J/mol·K): CaCO₃ 92.9, CaO 39.8, CO₂ 213.8"),
        ("2 H₂(g) + O₂(g) → 2 H₂O(l)", {"H2": 130.7, "O2": 205.1, "H2O": 70.0}, [(2, "H2"), (1, "O2")], [(2, "H2O")], "S° (J/mol·K): H₂ 130.7, O₂ 205.1, H₂O(l) 70.0")]


def t_entropy(rng, k):
    text, d, rs, ps, data = SENT[k % len(SENT)]
    sp, sr = sum(c * d[f] for c, f in ps), sum(c * d[f] for c, f in rs)
    return prob("Thermodynamics", 5, f"Calculate ΔS°rxn (J/K) for {text}. {data}.", sp - sr, "J/K",
                ["ΔS°rxn = Σ n S°(products) − Σ n S°(reactants).", f"Products: {sig(sp, 4)}; reactants: {sig(sr, 4)}.", f"ΔS° = {sig(sp, 4)} − {sig(sr, 4)} = {sig(sp - sr, 4)} J/K."], rel=0.005, abs_=0.1, n=4)


# ---------------- Electrochemistry ----------------
HALF = {"Zn": (-0.76, 2), "Cu": (0.34, 2), "Ag": (0.80, 1), "Fe": (-0.44, 2), "Ni": (-0.25, 2), "Mg": (-2.37, 2), "Al": (-1.66, 3), "Pb": (-0.13, 2)}
CELLS = [("Zn", "Cu"), ("Cu", "Ag"), ("Fe", "Cu"), ("Zn", "Ag"), ("Ni", "Ag"), ("Mg", "Cu"), ("Al", "Pb")]


def t_ecell(rng, k):
    an, ca = CELLS[k % len(CELLS)]
    (ea, na), (ec, nc) = HALF[an], HALF[ca]
    E = ec - ea
    if k % 2 == 0:
        return prob("Electrochemistry", 5, f"A galvanic cell uses the half-reactions {ion(ca, str(nc) + '+')} + {nc}e⁻ → {ca} (E° = {ec:+.2f} V) and {ion(an, str(na) + '+')} + {na}e⁻ → {an} (E° = {ea:+.2f} V). What is E°cell (V)?",
                    E, "V", ["The half-reaction with the larger (more positive) E° is the cathode.", f"E°cell = E°cathode − E°anode = {ec:+.2f} − ({ea:+.2f}) = {E:.2f} V."], rel=0, abs_=0.02)
    n = na * nc // gcd(na, nc)
    dG = -n * F * E / 1000
    return prob("Electrochemistry", 5, f"A cell made from {an} and {ca} half-cells has E°cell = {E:.2f} V and transfers n = {n} electrons. What is ΔG° (kJ)?", dG, "kJ",
                ["ΔG° = −n F E° with F = 96,485 C/mol.", f"ΔG° = −({n})(96485)({E:.2f}) = {sig(dG * 1000)} J = {sig(dG)} kJ."], rel=0.015)


def t_nernst(rng, k):
    if k % 2 == 0:
        a, b = rng.choice([0.010, 0.050, 0.10, 0.50]), rng.choice([0.50, 1.0, 1.5, 2.0])
        E = 1.10 - 0.0592 / 2 * log10(a / b)
        return prob("Electrochemistry", 5, f"A Zn/Cu cell (Zn + Cu²⁺ → Zn²⁺ + Cu, E° = 1.10 V) has [Zn²⁺] = {a} M and [Cu²⁺] = {b} M at 25 °C. What is the cell potential (V)?", E, "V",
                    [f"Q = [Zn²⁺]/[Cu²⁺] = {a}/{b} = {sig(a / b, 4)}.", "Nernst: E = E° − (0.0592/n) log Q with n = 2.", f"E = 1.10 − 0.0296 x log({sig(a / b, 4)}) = {sig(E, 4)} V."], rel=0, abs_=0.01)
    c, d = rng.choice([0.010, 0.10, 0.50, 1.0]), rng.choice([0.10, 0.50, 1.0, 2.0])
    E = 0.46 - 0.0592 / 2 * log10(c / d ** 2)
    return prob("Electrochemistry", 5, f"A Cu/Ag cell (Cu + 2 Ag⁺ → Cu²⁺ + 2 Ag, E° = 0.46 V) has [Cu²⁺] = {c} M and [Ag⁺] = {d} M at 25 °C. What is the cell potential (V)?", E, "V",
                [f"Q = [Cu²⁺]/[Ag⁺]² = {c}/{d}² = {sig(c / d ** 2, 4)}.", "E = E° − (0.0592/2) log Q.", f"E = 0.46 − 0.0296 x log({sig(c / d ** 2, 4)}) = {sig(E, 4)} V."], rel=0, abs_=0.01)


ELEC = [("copper", "Cu", 63.546, 2), ("silver", "Ag", 107.87, 1), ("zinc", "Zn", 65.38, 2), ("nickel", "Ni", 58.693, 2), ("aluminum", "Al", 26.982, 3)]


def t_electrolysis(rng, k):
    name, sym, M, n = ELEC[k % len(ELEC)]
    I, t = nice(rng, 0.5, 10, 1), nice(rng, 10, 120, 0)
    mol_e = I * t * 60 / F
    if k % 2 == 0:
        m = mol_e / n * M
        return prob("Electrochemistry", 5, f"A current of {I} A flows for {t} minutes through a solution of {sym}{'⁺' if n == 1 else str(n) + '+'} ions. What mass (g) of {name} is deposited?", m, "g",
                    [f"Charge = I t = {I} x {t * 60} s = {sig(I * t * 60)} C.", f"Moles e⁻ = {sig(I * t * 60)} / 96485 = {sig(mol_e)} mol; moles {sym} = {sig(mol_e)} / {n}.", f"Mass = {sig(mol_e / n)} x {M} g/mol = {sig(m)} g."])
    m, I = nice(rng, 0.2, 2.0, 2), nice(rng, 1, 10, 1)
    tt = m / M * n * F / I / 60
    return prob("Electrochemistry", 5, f"How long (minutes) must a {I} A current flow to deposit {m} g of {name} from {sym}{'⁺' if n == 1 else str(n) + '+'} ions?", tt, "min",
                [f"Moles {sym} = {m} / {M} = {sig(m / M)} mol; moles e⁻ = x {n} = {sig(m / M * n)} mol.", f"Charge = {sig(m / M * n)} x 96485 = {sig(m / M * n * F)} C.", f"t = Q / I = {sig(m / M * n * F / I)} s = {sig(tt)} min."])


# ---------------- Nuclear ----------------
ISOT = [("iodine-131", 8.02, "days"), ("carbon-14", 5730, "years"), ("cobalt-60", 5.27, "years"), ("phosphorus-32", 14.3, "days"),
        ("strontium-90", 28.8, "years"), ("technetium-99m", 6.0, "hours")]


def t_decay(rng, k):
    name, th, unit = ISOT[k % len(ISOT)]
    v = (k // len(ISOT) + k) % 3
    if v == 0:
        m0, fac = nice(rng, 5, 200, 1), rng.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
        t = round(th * fac, 2)
        a = m0 * 0.5 ** (t / th)
        return prob("Nuclear", 3, f"{name.capitalize()} has a half-life of {th} {unit}. How many grams remain from a {m0} g sample after {t} {unit}?", a, "g",
                    [f"Number of half-lives = {t} / {th} = {sig(t / th)}.", "N = N₀ (1/2)^(t/t½).", f"N = {m0} x 0.5^{sig(t / th)} = {sig(a)} g."], rel=0.015)
    if v == 1:
        frac = rng.choice([0.5, 0.25, 0.125, 0.10, 0.05, 0.01])
        t = th * log(1 / frac) / log(2)
        return prob("Nuclear", 3, f"{name.capitalize()} has a half-life of {th} {unit}. How long does it take for its activity to fall to {frac} of the original?", t, unit,
                    ["N/N₀ = (1/2)^(t/t½) → t = t½ x log₂(N₀/N).", f"t = {th} x log₂({1 / frac:.3g}) = {sig(t)} {unit}."], rel=0.015)
    f = rng.choice([2, 3, 4, 5])
    return prob("Nuclear", 3, f"After {f} half-lives, what percent of a radioactive sample remains?", 100 * 0.5 ** f, "%", ["Each half-life halves the amount.", f"Remaining = (1/2)^{f} = {sig(0.5 ** f, 4)} = {sig(100 * 0.5 ** f, 4)}%."], rel=0.005)


TEMPLATES = [
    ("sigfigs", t_sigfigs, 8), ("unitconv", t_unitconv, 8), ("speed", t_speed, 3), ("sci", t_sci, 4), ("density", t_density, 6), ("temp", t_temp, 6),
    ("neutrons", t_neutrons, 8), ("ions", t_ions, 7), ("avgmass", t_avgmass, 6),
    ("molarmass", t_molarmass, 8), ("gtomol", t_gtomol, 6), ("moltog", t_moltog, 5), ("particles", t_particles, 6), ("percomp", t_percomp, 8), ("empirical", t_empirical, 6),
    ("massmass", t_massmass, 8), ("limiting", t_limiting, 6), ("yield", t_yield, 4),
    ("molarity", t_molarity, 6), ("dilution", t_dilution, 6), ("titration", t_titration, 6), ("massmolal", t_massmolal, 4), ("colligative", t_colligative, 5), ("osmotic", t_osmotic, 3),
    ("idealgas", t_idealgas, 8), ("gaslaws", t_gaslaws, 8), ("dalton", t_dalton, 4), ("gasdensity", t_gasdensity, 6), ("graham", t_graham, 4),
    ("calorimetry", t_calorimetry, 8), ("phase", t_phase, 4), ("formation", t_formation, 6), ("hess", t_hess, 4),
    ("light", t_light, 8), ("bohr", t_bohr, 9), ("econfig", t_econfig, 9),
    ("vsepr", t_vsepr, 8), ("formal", t_formal, 6), ("sigmapi", t_sigmapi, 6),
    ("firstorder", t_firstorder, 6), ("rate", t_rate, 8), ("arrhenius", t_arrhenius, 3),
    ("kc", t_kc, 5), ("kp", t_kp, 5), ("ice", t_ice, 6), ("ksp", t_ksp, 5),
    ("phstrong", t_ph_strong, 6), ("weak", t_weak, 6), ("hh", t_hh, 4), ("mixing", t_mixing, 4), ("kw", t_kw, 6),
    ("gibbs", t_gibbs, 8), ("entropy", t_entropy, 4),
    ("ecell", t_ecell, 6), ("nernst", t_nernst, 4), ("electrolysis", t_electrolysis, 6),
    ("decay", t_decay, 6),
]


def build() -> list[dict]:
    out, seen = [], set()
    for tid, fn, count in TEMPLATES:
        rng = random.Random(tid)
        made = tries = 0
        while made < count and tries < count * 40:
            tries += 1
            p = fn(rng, made)
            if p is None or p["question"] in seen:
                continue
            seen.add(p["question"])
            made += 1
            p["id"] = f"gen-{tid}-{made:02d}"
            out.append(p)
        if made < count:
            print(f"warning: {tid} produced {made}/{count}", file=sys.stderr)
    return out


if __name__ == "__main__":
    probs = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(probs, indent=1, ensure_ascii=False), encoding="utf-8")
    by: dict[str, int] = {}
    for p in probs:
        by[p["topic"]] = by.get(p["topic"], 0) + 1
    print(f"wrote {len(probs)} problems to {OUT.relative_to(ROOT)}")
    for t, c in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {c:3d}  {t}")
