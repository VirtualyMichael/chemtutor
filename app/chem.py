"""Shared chemistry data: periodic table (Z 1-54 + common heavier elements) and a formula parser.

One source of truth for the cheat sheet and the problem generator, so the masses a student looks up are
exactly the masses the answers were computed with.
"""
from __future__ import annotations
import re

# (Z, symbol, name, atomic mass, group-column 1-18, period row) - mass in g/mol
_ELEMENTS = [
    (1, "H", "Hydrogen", 1.008, 1, 1), (2, "He", "Helium", 4.0026, 18, 1),
    (3, "Li", "Lithium", 6.94, 1, 2), (4, "Be", "Beryllium", 9.0122, 2, 2), (5, "B", "Boron", 10.81, 13, 2),
    (6, "C", "Carbon", 12.011, 14, 2), (7, "N", "Nitrogen", 14.007, 15, 2), (8, "O", "Oxygen", 15.999, 16, 2),
    (9, "F", "Fluorine", 18.998, 17, 2), (10, "Ne", "Neon", 20.180, 18, 2),
    (11, "Na", "Sodium", 22.990, 1, 3), (12, "Mg", "Magnesium", 24.305, 2, 3), (13, "Al", "Aluminum", 26.982, 13, 3),
    (14, "Si", "Silicon", 28.085, 14, 3), (15, "P", "Phosphorus", 30.974, 15, 3), (16, "S", "Sulfur", 32.06, 16, 3),
    (17, "Cl", "Chlorine", 35.45, 17, 3), (18, "Ar", "Argon", 39.948, 18, 3),
    (19, "K", "Potassium", 39.098, 1, 4), (20, "Ca", "Calcium", 40.078, 2, 4), (21, "Sc", "Scandium", 44.956, 3, 4),
    (22, "Ti", "Titanium", 47.867, 4, 4), (23, "V", "Vanadium", 50.942, 5, 4), (24, "Cr", "Chromium", 51.996, 6, 4),
    (25, "Mn", "Manganese", 54.938, 7, 4), (26, "Fe", "Iron", 55.845, 8, 4), (27, "Co", "Cobalt", 58.933, 9, 4),
    (28, "Ni", "Nickel", 58.693, 10, 4), (29, "Cu", "Copper", 63.546, 11, 4), (30, "Zn", "Zinc", 65.38, 12, 4),
    (31, "Ga", "Gallium", 69.723, 13, 4), (32, "Ge", "Germanium", 72.630, 14, 4), (33, "As", "Arsenic", 74.922, 15, 4),
    (34, "Se", "Selenium", 78.971, 16, 4), (35, "Br", "Bromine", 79.904, 17, 4), (36, "Kr", "Krypton", 83.798, 18, 4),
    (37, "Rb", "Rubidium", 85.468, 1, 5), (38, "Sr", "Strontium", 87.62, 2, 5), (39, "Y", "Yttrium", 88.906, 3, 5),
    (40, "Zr", "Zirconium", 91.224, 4, 5), (41, "Nb", "Niobium", 92.906, 5, 5), (42, "Mo", "Molybdenum", 95.95, 6, 5),
    (43, "Tc", "Technetium", 98.0, 7, 5), (44, "Ru", "Ruthenium", 101.07, 8, 5), (45, "Rh", "Rhodium", 102.91, 9, 5),
    (46, "Pd", "Palladium", 106.42, 10, 5), (47, "Ag", "Silver", 107.87, 11, 5), (48, "Cd", "Cadmium", 112.41, 12, 5),
    (49, "In", "Indium", 114.82, 13, 5), (50, "Sn", "Tin", 118.71, 14, 5), (51, "Sb", "Antimony", 121.76, 15, 5),
    (52, "Te", "Tellurium", 127.60, 16, 5), (53, "I", "Iodine", 126.90, 17, 5), (54, "Xe", "Xenon", 131.29, 18, 5),
]
# common heavier elements listed separately (not laid out in the grid)
_HEAVY = [(55, "Cs", "Cesium", 132.91), (56, "Ba", "Barium", 137.33), (74, "W", "Tungsten", 183.84),
          (78, "Pt", "Platinum", 195.08), (79, "Au", "Gold", 196.97), (80, "Hg", "Mercury", 200.59),
          (82, "Pb", "Lead", 207.2), (83, "Bi", "Bismuth", 208.98), (88, "Ra", "Radium", 226.0), (92, "U", "Uranium", 238.03)]

MASS = {s: m for _, s, _, m, *_ in _ELEMENTS} | {s: m for _, s, _, m in _HEAVY}
NAME = {s: n for _, s, n, *_ in _ELEMENTS} | {s: n for _, s, n, _ in _HEAVY}
Z = {s: z for z, s, *_ in _ELEMENTS} | {s: z for z, s, *_ in _HEAVY}


def elements() -> list[dict]:
    """Grid elements (with column/row) for the periodic table, plus heavy ones without a position."""
    grid = [{"z": z, "sym": s, "name": n, "mass": m, "col": c, "row": r} for z, s, n, m, c, r in _ELEMENTS]
    heavy = [{"z": z, "sym": s, "name": n, "mass": m} for z, s, n, m in _HEAVY]
    return grid + heavy


def parse(formula: str) -> dict[str, int]:
    """'Al2(SO4)3' -> {'Al': 2, 'S': 3, 'O': 12}. Supports nested parentheses."""
    stack: list[dict[str, int]] = [{}]
    i = 0
    while i < len(formula):
        c = formula[i]
        if c == "(":
            stack.append({})
            i += 1
        elif c == ")":
            i += 1
            j = i
            while j < len(formula) and formula[j].isdigit():
                j += 1
            mult = int(formula[i:j] or 1)
            i = j
            top = stack.pop()
            for el, n in top.items():
                stack[-1][el] = stack[-1].get(el, 0) + n * mult
        else:
            m = re.match(r"[A-Z][a-z]?", formula[i:])
            if not m or m.group(0) not in MASS:
                raise ValueError(f"unknown element in {formula!r} at {i}")
            el = m.group(0)
            i += len(el)
            j = i
            while j < len(formula) and formula[j].isdigit():
                j += 1
            stack[-1][el] = stack[-1].get(el, 0) + int(formula[i:j] or 1)
            i = j
    return stack[0]


def molar_mass(formula: str) -> float:
    return sum(MASS[el] * n for el, n in parse(formula).items())


def pretty(formula: str) -> str:
    """'Al2(SO4)3' -> 'Al₂(SO₄)₃' for display."""
    sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return re.sub(r"(?<=[A-Za-z)])(\d+)", lambda m: m.group(1).translate(sub), formula)
