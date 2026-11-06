"""Build original AP-Chemistry-style free-response questions (multi-part, rubric-scored).

Numeric answers are computed here from the same constants as the cheat sheet; written parts carry a model
answer and a point-by-point rubric. These are NOT College Board questions (those are copyrighted); they imitate
the format: stem + lettered parts, each worth rubric points.
Run:  python scripts/build_frq.py       (writes data/frq/ap_frq.json)
"""
from __future__ import annotations
import json, sys
from math import exp, log10, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import chem  # noqa: E402

OUT = ROOT / "data" / "frq" / "ap_frq.json"
R, F = 0.08206, 96485.0
M = chem.MASS


def g(x, n=3):
    """n significant figures, plain notation unless tiny/huge."""
    from math import floor, log10 as l10
    if x == 0:
        return "0"
    d = n - 1 - floor(l10(abs(x)))
    r = round(x, d)
    if abs(r) >= 1e5 or abs(r) < 1e-3:
        e = floor(l10(abs(r)))
        return f"{r / 10 ** e:.{n - 1}f} x 10^{e}"
    return f"{r:.{max(0, d)}f}"


def num(label, prompt, ans, unit, rubric, solution, rel=0.01, abs_=0.0, n=3, ans_text=None):
    pts = sum(r["pts"] for r in rubric)
    return {"label": label, "type": "numeric", "prompt": prompt, "points": pts, "answer": float(f"{ans:.6g}"),
            "tolerance_rel": rel, "tolerance_abs": abs_, "answer_text": ans_text or ((str(int(ans)) if rel == 0 and float(ans).is_integer() else g(ans, n)) + (f" {unit}" if unit else "")),
            "rubric": rubric, "solution": solution}


def wr(label, prompt, rubric, model):
    return {"label": label, "type": "written", "prompt": prompt, "points": sum(r["pts"] for r in rubric),
            "rubric": rubric, "model_answer": model}


def R_(pts, text, auto=False):
    return {"pts": pts, "text": text, **({"auto": True} if auto else {})}


FRQS = []

# ---------------------------------------------------------------- 1 stoichiometry / limiting reagent
mAl, Pcl, Vcl, Tk = 5.40, 1.00, 9.00, 298.15
nAl = mAl / M["Al"]
nCl = Pcl * Vcl / (R * Tk)
need = nAl * 3 / 2
mmAlCl3 = chem.molar_mass("AlCl3")
mAlCl3 = nAl * mmAlCl3
actual = 22.1
FRQS.append({
    "id": "frq-01", "title": "Aluminum and chlorine", "kind": "long", "minutes": 18, "topics": ["Moles & Stoichiometry", "Gases"],
    "stem": f"2 Al(s) + 3 Cl₂(g) → 2 AlCl₃(s)\nA student places {mAl:.2f} g of Al(s) in a rigid vessel and adds {Vcl:.2f} L of Cl₂(g) measured at {Pcl:.2f} atm and 25 °C. "
            "The reaction goes to completion. (Use R = 0.08206 L·atm/(mol·K) and the periodic table on the cheat sheet.)",
    "parts": [
        num("(a)", f"Calculate the number of moles of Al in the {mAl:.2f} g sample.", nAl, "mol",
            [R_(1, "Correct number of moles of Al, with units", True)],
            [f"moles Al = {mAl:.2f} g / {M['Al']} g/mol = {g(nAl, 4)} mol."]),
        num("(b)", f"Calculate the number of moles of Cl₂(g) in the {Vcl:.2f} L sample.", nCl, "mol",
            [R_(1, "Uses PV = nRT with temperature converted to kelvin (298 K)"), R_(1, "Correct number of moles of Cl₂", True)],
            ["n = PV/RT, with T = 25 + 273.15 = 298.15 K.", f"n = ({Pcl:.2f})({Vcl:.2f}) / ((0.08206)(298.15)) = {g(nCl, 4)} mol."]),
        wr("(c)", "Identify the limiting reactant. Support your answer with a calculation.",
           [R_(1, f"Calculates the moles of Cl₂ needed for the Al (about {g(need)} mol) or the moles of Al needed for the Cl₂ (about {g(nCl * 2 / 3)} mol)"),
            R_(1, "Compares to the amount available and identifies Al as the limiting reactant")],
           f"Al needs {g(nAl, 3)} × 3/2 = {g(need)} mol Cl₂, but {g(nCl)} mol Cl₂ is available, so Cl₂ is in excess and Al is the limiting reactant."),
        num("(d)", "Calculate the maximum mass, in grams, of AlCl₃(s) that can form.", mAlCl3, "g",
            [R_(1, "Uses the limiting reactant (Al) and the 2:2 (1:1) mole ratio"), R_(1, "Correct mass of AlCl₃ with units", True)],
            [f"moles AlCl₃ = {g(nAl, 4)} mol Al x (2 AlCl₃ / 2 Al) = {g(nAl, 4)} mol.", f"molar mass AlCl₃ = {g(mmAlCl3, 4)} g/mol.", f"mass = {g(nAl, 4)} x {g(mmAlCl3, 4)} = {g(mAlCl3)} g."]),
        num("(e)", f"The student collects {actual:.1f} g of AlCl₃. Calculate the percent yield.", actual / mAlCl3 * 100, "%",
            [R_(1, "Correct percent yield (actual / theoretical x 100)", True)],
            [f"% yield = {actual:.1f} / {g(mAlCl3)} x 100 = {g(actual / mAlCl3 * 100)}%."], rel=0.015),
    ]})

# ---------------------------------------------------------------- 2 kinetics
k0 = 7.1e3
exps = [(0.010, 0.010), (0.020, 0.010), (0.020, 0.020)]
rates = [k0 * a ** 2 * b for a, b in exps]
tbl = "Experiment   [NO] (M)   [O₂] (M)   Initial rate (M/s)\n" + "\n".join(
    f"     {i + 1}        {a:.3f}      {b:.3f}      {r:.2e}" for i, ((a, b), r) in enumerate(zip(exps, rates)))
r_new = k0 * 0.015 ** 2 * 0.0050
FRQS.append({
    "id": "frq-02", "title": "Rate of NO oxidation", "kind": "short", "minutes": 14, "topics": ["Kinetics"],
    "stem": f"2 NO(g) + O₂(g) → 2 NO₂(g)\nThe initial rate of the reaction was measured at constant temperature:\n{tbl}",
    "parts": [
        num("(a)", "Determine the order of the reaction with respect to NO.", 2, "",
            [R_(1, "Order with respect to NO is 2 (doubling [NO] quadruples the rate: experiments 1 and 2)", True)],
            [f"Exps 1 and 2: [NO] doubles, rate increases by {rates[1] / rates[0]:.0f}x = 2² → second order in NO."], rel=0),
        num("(b)", "Determine the order of the reaction with respect to O₂.", 1, "",
            [R_(1, "Order with respect to O₂ is 1 (doubling [O₂] doubles the rate: experiments 2 and 3)", True)],
            [f"Exps 2 and 3: [O₂] doubles, rate increases by {rates[2] / rates[1]:.0f}x → first order in O₂."], rel=0),
        num("(c)", "Write the rate law and calculate the value of the rate constant, k, including units.", k0, "M⁻²·s⁻¹",
            [R_(1, "Rate law: rate = k[NO]²[O₂]"), R_(1, "Correct value of k with correct units (M⁻²·s⁻¹)", True)],
            ["rate = k[NO]²[O₂].", f"k = rate / ([NO]²[O₂]) = {rates[0]:.2e} / ((0.010)²(0.010)) = {g(k0)} M⁻²·s⁻¹."], rel=0.02),
        num("(d)", "Calculate the initial rate when [NO] = 0.015 M and [O₂] = 0.0050 M.", r_new, "M/s",
            [R_(1, "Correct rate using the rate law and k", True)],
            [f"rate = ({g(k0)})(0.015)²(0.0050) = {g(r_new)} M/s."], rel=0.03),
        wr("(e)", "A proposed mechanism is: step 1 (fast, equilibrium) 2 NO ⇌ N₂O₂; step 2 (slow) N₂O₂ + O₂ → 2 NO₂. "
                  "Show that this mechanism is consistent with the experimental rate law.",
           [R_(1, "States that the slow step determines the rate: rate = k₂[N₂O₂][O₂]"),
            R_(1, "Uses the fast equilibrium ([N₂O₂] = K[NO]²) to eliminate the intermediate and obtain rate = k₂K[NO]²[O₂], matching the data")],
           "The slow step is rate-determining: rate = k₂[N₂O₂][O₂]. N₂O₂ is an intermediate, so use the fast equilibrium: K = [N₂O₂]/[NO]², giving [N₂O₂] = K[NO]². "
           "Substituting: rate = k₂K[NO]²[O₂] = k[NO]²[O₂], which matches the experimental rate law."),
    ]})

# ---------------------------------------------------------------- 3 equilibrium
N2O4, NO2 = 0.0420, 0.0140
Kc = NO2 ** 2 / N2O4
Kp = Kc * R * 298.15
c0 = 0.200
x = (-Kc + sqrt(Kc * Kc + 16 * Kc * c0)) / 8
FRQS.append({
    "id": "frq-03", "title": "Dinitrogen tetroxide equilibrium", "kind": "long", "minutes": 18, "topics": ["Equilibrium"],
    "stem": f"N₂O₄(g) ⇌ 2 NO₂(g)   ΔH° > 0\nAt equilibrium at 298 K in a rigid container, [N₂O₄] = {N2O4:.4f} M and [NO₂] = {NO2:.4f} M.",
    "parts": [
        wr("(a)", "Write the equilibrium-constant expression for Kc.", [R_(1, "Kc = [NO₂]² / [N₂O₄] (products over reactants, coefficient as exponent)")],
           "Kc = [NO₂]² / [N₂O₄]"),
        num("(b)", "Calculate the value of Kc at 298 K.", Kc, "",
            [R_(1, f"Substitutes the equilibrium concentrations correctly: ({NO2:.4f})² / {N2O4:.4f}"), R_(1, "Correct value of Kc", True)],
            [f"Kc = ({NO2:.4f})² / {N2O4:.4f} = {g(Kc, 3)}."], rel=0.02, ans_text=g(Kc, 3)),
        num("(c)", "Calculate Kp for the reaction at 298 K.", Kp, "",
            [R_(1, "Uses Kp = Kc(RT)^Δn with Δn = +1 and T = 298 K"), R_(1, "Correct value of Kp", True)],
            ["Δn = 2 − 1 = +1.", f"Kp = Kc(RT) = {g(Kc, 3)} x (0.08206 x 298.15) = {g(Kp)}."], rel=0.03, ans_text=g(Kp, 3)),
        num("(d)", f"A new rigid container starts with {c0:.3f} M N₂O₄ and no NO₂ at 298 K. Using the Kc value from part (b), calculate [NO₂] at equilibrium.", 2 * x, "M",
            [R_(1, "Sets up an ICE table / expression 4x² / (0.200 − x) = Kc"), R_(1, "Correct equilibrium [NO₂] (solves the quadratic)", True)],
            ["ICE: [N₂O₄] = 0.200 − x, [NO₂] = 2x.", f"Kc = (2x)² / (0.200 − x) → 4x² + {g(Kc, 3)}x − {g(Kc * c0, 3)} = 0.", f"x = {g(x, 3)} M, so [NO₂] = 2x = {g(2 * x)} M."], rel=0.03),
        wr("(e)", "The volume of the container is suddenly decreased at constant temperature. Predict how the equilibrium position shifts and what happens to the value of Kc. Justify both.",
           [R_(1, "Shifts toward the reactant side (toward N₂O₄), because that side has fewer moles of gas and reduces the pressure increase"),
            R_(1, "Kc does not change, because K depends only on temperature")],
           "Decreasing the volume raises the total pressure, so the system shifts toward the side with fewer moles of gas, i.e. toward N₂O₄ (1 mol vs 2 mol). Kc is unchanged because it depends only on temperature."),
    ]})

# ---------------------------------------------------------------- 4 acid/base
C_ha, pH0 = 0.100, 2.88
h = 10 ** -pH0
Ka = h * h / (C_ha - h)
pKa = -log10(Ka)
nHA, nOH = 25.0 * 0.100, 15.0 * 0.100
pHbuf = pKa + log10((nOH) / (nHA - nOH))
Kb = 1e-14 / Ka
FRQS.append({
    "id": "frq-04", "title": "A weak acid and its titration", "kind": "long", "minutes": 18, "topics": ["Acids & Bases"],
    "stem": f"A {C_ha:.3f} M solution of a weak monoprotic acid, HA, has a pH of {pH0} at 25 °C. A 25.0 mL sample of this solution is titrated with 0.100 M NaOH.",
    "parts": [
        num("(a)", "Calculate Ka for HA.", Ka, "",
            [R_(1, "Uses [H⁺] = 10^(−pH) and Ka = [H⁺][A⁻]/[HA] with [HA] ≈ 0.100 − [H⁺]"), R_(1, "Correct Ka", True)],
            [f"[H⁺] = 10^(−{pH0}) = {g(h)} M = [A⁻].", f"Ka = ({g(h)})² / ({C_ha:.3f} − {g(h)}) = {g(Ka)}."], rel=0.04, ans_text=g(Ka, 3)),
        num("(b)", "Calculate the percent ionization of HA in the 0.100 M solution.", h / C_ha * 100, "%",
            [R_(1, "Correct percent ionization ([H⁺]/0.100 x 100)", True)],
            [f"% ionization = {g(h)} / {C_ha:.3f} x 100 = {g(h / C_ha * 100)}%."], rel=0.03),
        num("(c)", "Calculate the pH of the solution after 15.0 mL of 0.100 M NaOH has been added to the 25.0 mL sample.", pHbuf, "",
            [R_(1, "Finds the moles of HA and A⁻ after the neutralization (1.00 mmol HA, 1.50 mmol A⁻)"), R_(1, "Uses pH = pKa + log([A⁻]/[HA]) to get the correct pH", True)],
            [f"mmol HA = {g(nHA)}, mmol OH⁻ = {g(nOH)}; after reaction HA = {g(nHA - nOH)} mmol, A⁻ = {g(nOH)} mmol.", f"pKa = −log({g(Ka)}) = {g(pKa)}.", f"pH = {g(pKa)} + log({g(nOH)}/{g(nHA - nOH)}) = {g(pHbuf, 3)}."],
            rel=0, abs_=0.05, ans_text=g(pHbuf, 3)),
        num("(d)", "Calculate the volume of 0.100 M NaOH required to reach the equivalence point.", 25.0, "mL",
            [R_(1, "25.0 mL (moles of base = moles of acid, equal concentrations)", True)],
            ["At equivalence mol OH⁻ = mol HA = 0.0250 L x 0.100 M = 2.50 x 10⁻³ mol → V = 2.50e-3 / 0.100 = 0.0250 L = 25.0 mL."], rel=0.01),
        wr("(e)", "Predict whether the pH at the equivalence point is less than 7, equal to 7, or greater than 7. Justify your answer.",
           [R_(1, "Greater than 7"), R_(1, "At equivalence the solution contains A⁻, the conjugate base of a weak acid, which reacts with water: A⁻ + H₂O ⇌ HA + OH⁻, producing OH⁻")],
           "Greater than 7. At the equivalence point all HA has become A⁻, the conjugate base of a weak acid. A⁻ hydrolyzes: A⁻ + H₂O ⇌ HA + OH⁻, producing hydroxide and making the solution basic."),
        num("(f)", "Calculate Kb for A⁻.", Kb, "",
            [R_(1, "Kb = Kw / Ka = 1.0 x 10⁻¹⁴ / Ka", True)],
            [f"Kb = 1.0e-14 / {g(Ka)} = {g(Kb)}."], rel=0.05, ans_text=g(Kb, 3)),
    ]})

# ---------------------------------------------------------------- 5 thermodynamics
dH, dS = -92.2, -198.7
dG = dH - 298 * dS / 1000
Tcross = dH * 1000 / dS
K298 = exp(-dG * 1000 / (8.314 * 298))
FRQS.append({
    "id": "frq-05", "title": "Thermodynamics of ammonia synthesis", "kind": "long", "minutes": 18, "topics": ["Thermodynamics", "Equilibrium"],
    "stem": f"N₂(g) + 3 H₂(g) → 2 NH₃(g)   ΔH° = {dH} kJ/mol(rxn),  ΔS° = {dS} J/(mol·K)(rxn)\n(Use R = 8.314 J/(mol·K).)",
    "parts": [
        num("(a)", "Calculate ΔG° for the reaction at 298 K, in kJ/mol.", dG, "kJ/mol",
            [R_(1, "Uses ΔG° = ΔH° − TΔS° with consistent units (J converted to kJ)"), R_(1, "Correct ΔG° with units", True)],
            [f"TΔS° = 298 x ({dS}) / 1000 = {g(298 * dS / 1000)} kJ.", f"ΔG° = {dH} − ({g(298 * dS / 1000)}) = {g(dG)} kJ/mol."], rel=0.01, abs_=0.3),
        wr("(b)", "Explain, in terms of the particles, why ΔS° for the reaction is negative.", [R_(1, "4 mol of gas react to form 2 mol of gas; fewer gas particles/less disorder (fewer microstates), so entropy decreases")],
           "The reaction converts 4 moles of gas (1 N₂ + 3 H₂) into 2 moles of gas (2 NH₃). Fewer gas particles means less dispersal of matter and energy, so the entropy of the system decreases."),
        num("(c)", "Calculate the temperature, in kelvin, at which ΔG° = 0 for this reaction.", Tcross, "K",
            [R_(1, "Sets ΔG° = 0 so T = ΔH°/ΔS° (with ΔH° converted to J)"), R_(1, "Correct temperature", True)],
            [f"0 = ΔH° − TΔS° → T = ΔH°/ΔS° = ({dH} x 1000) / ({dS}) = {g(Tcross, 3)} K."], rel=0.01),
        num("(d)", "Calculate the equilibrium constant K for the reaction at 298 K.", K298, "",
            [R_(1, "Uses ΔG° = −RT ln K with ΔG° in joules"), R_(1, "Correct K", True)],
            [f"ln K = −ΔG°/RT = −({g(dG * 1000)} J) / ((8.314)(298)) = {g(-dG * 1000 / (8.314 * 298), 4)}.", f"K = e^({g(-dG * 1000 / (8.314 * 298), 4)}) = {g(K298)}."], rel=0.05, ans_text=g(K298, 3)),
        wr("(e)", "As the temperature is increased, does K increase, decrease, or stay the same? Justify your answer.",
           [R_(1, "K decreases"), R_(1, "The reaction is exothermic (ΔH° < 0); raising the temperature favors the endothermic reverse reaction (Le Chatelier), or ΔG° becomes less negative so K decreases")],
           "K decreases. The forward reaction is exothermic (ΔH° < 0), so increasing the temperature shifts the equilibrium toward the reactants. Equivalently, −TΔS° becomes more positive, making ΔG° less negative and lowering K."),
    ]})

# ---------------------------------------------------------------- 6 electrochemistry
E0 = 1.10
dGcell = -2 * F * E0 / 1000
E_n = E0 - 0.0592 / 2 * log10(0.010 / 1.0)
I, t = 2.50, 30.0 * 60
mCu = I * t / (2 * F) * M["Cu"]
FRQS.append({
    "id": "frq-06", "title": "A zinc–copper cell", "kind": "long", "minutes": 18, "topics": ["Electrochemistry"],
    "stem": "A galvanic cell is built from a Zn(s) electrode in 1.0 M Zn(NO₃)₂ and a Cu(s) electrode in 1.0 M Cu(NO₃)₂, joined by a salt bridge. "
            "E°(Zn²⁺/Zn) = −0.76 V and E°(Cu²⁺/Cu) = +0.34 V. (F = 96,485 C/mol e⁻)",
    "parts": [
        wr("(a)", "Identify the anode, write the half-reaction that occurs there, and state the direction of electron flow in the external wire.",
           [R_(1, "Zn is the anode; Zn(s) → Zn²⁺ + 2e⁻ (oxidation)"), R_(1, "Electrons flow from the Zn electrode (anode) to the Cu electrode (cathode)")],
           "The zinc electrode is the anode (oxidation): Zn(s) → Zn²⁺(aq) + 2 e⁻. Electrons flow through the wire from the Zn electrode to the Cu electrode."),
        num("(b)", "Calculate ΔG° for the cell reaction, in kJ per mole of reaction.", dGcell, "kJ/mol",
            [R_(1, "Uses ΔG° = −nFE° with n = 2 and E°cell = 1.10 V"), R_(1, "Correct ΔG° in kJ with the negative sign", True)],
            [f"E°cell = 0.34 − (−0.76) = {E0:.2f} V; n = 2.", f"ΔG° = −(2)(96485)({E0:.2f}) = {g(dGcell * 1000)} J = {g(dGcell)} kJ/mol."], rel=0.01),
        num("(c)", "Calculate the cell potential at 25 °C when [Zn²⁺] = 0.010 M and [Cu²⁺] = 1.0 M.", E_n, "V",
            [R_(1, "Q = [Zn²⁺]/[Cu²⁺] = 0.010 and the Nernst equation E = E° − (0.0592/n) log Q"), R_(1, "Correct E", True)],
            ["Q = [Zn²⁺]/[Cu²⁺] = 0.010/1.0 = 0.010.", f"E = 1.10 − (0.0592/2) log(0.010) = 1.10 + 0.0592 = {g(E_n, 3)} V."], rel=0, abs_=0.01),
        num("(d)", "A current of 2.50 A is passed through a solution of Cu²⁺ for 30.0 minutes in an electrolytic cell. Calculate the mass of copper deposited.", mCu, "g",
            [R_(1, "Charge Q = It = (2.50 A)(1800 s) and moles of e⁻ = Q/F, with 2 e⁻ per Cu"), R_(1, "Correct mass of Cu in grams", True)],
            [f"Q = It = 2.50 x 1800 = {g(I * t)} C.", f"mol e⁻ = {g(I * t)} / 96485 = {g(I * t / F)} mol; mol Cu = {g(I * t / F / 2)} mol.", f"mass = {g(I * t / F / 2)} x {M['Cu']} = {g(mCu)} g."], rel=0.015),
    ]})

# ---------------------------------------------------------------- 7 bonding / IMF
bonds = {"C-H": 413, "O=O": 498, "C=O": 799, "O-H": 463}
brk = 4 * bonds["C-H"] + 2 * bonds["O=O"]
frm = 2 * bonds["C=O"] + 4 * bonds["O-H"]
dHb = brk - frm
FRQS.append({
    "id": "frq-07", "title": "Structure, forces and bond energies", "kind": "short", "minutes": 14, "topics": ["Bonding & Geometry"],
    "stem": "Ethanol (CH₃CH₂OH, boiling point 78 °C) and dimethyl ether (CH₃OCH₃, boiling point −24 °C) are isomers with the formula C₂H₆O. Average bond enthalpies (kJ/mol): "
            "C–H 413, O=O 498, C=O 799, O–H 463.",
    "parts": [
        wr("(a)", "Draw the Lewis structure of dimethyl ether and describe it in words (central atom, bonds, and lone pairs).",
           [R_(1, "Oxygen is bonded to two CH₃ groups (C–O–C); each C has three C–H bonds"), R_(1, "Oxygen has two lone pairs (all atoms satisfy octet/duet)")],
           "H₃C–O–CH₃: oxygen is the central atom bonded to two carbon atoms by single bonds, each carbon is bonded to three hydrogens, and oxygen carries two lone pairs."),
        wr("(b)", "Predict the molecular geometry around the oxygen atom in dimethyl ether, and explain why the C–O–C arrangement is bent rather than linear.",
           [R_(1, "Bent (V-shaped) molecular geometry around oxygen"),
            R_(1, "Oxygen has four electron groups (two bonding pairs and two lone pairs) arranged tetrahedrally; the lone pairs occupy space and repel, so the two C–O bonds are not opposite each other")],
           "Oxygen has four electron groups (two C–O bonds and two lone pairs), so the electron arrangement is tetrahedral and the molecular geometry is bent. The lone pairs take up space and repel the bonding pairs, so the C–O–C angle is roughly tetrahedral (about 110°), not 180°."),
        wr("(c)", "Explain, in terms of intermolecular forces, why ethanol has a much higher boiling point than dimethyl ether.",
           [R_(1, "Ethanol molecules form hydrogen bonds (O–H···O); dimethyl ether has no O–H bond so cannot hydrogen bond with itself"),
            R_(1, "Hydrogen bonding is stronger than the dipole–dipole/dispersion forces in the ether, so more energy is needed to separate ethanol molecules (similar molar masses so dispersion forces are comparable)")],
           "Ethanol has an O–H bond, so its molecules hydrogen-bond to each other. Dimethyl ether has no H bonded to O, so it has only dipole–dipole and dispersion forces. The two have the same molar mass (similar dispersion forces), so the stronger hydrogen bonding in ethanol gives it the higher boiling point."),
        num("(d)", "Use the average bond enthalpies to estimate ΔH for the combustion CH₄ + 2 O₂ → CO₂ + 2 H₂O(g), in kJ/mol.", dHb, "kJ/mol",
            [R_(1, f"Bonds broken (4 C–H + 2 O=O = {brk} kJ) and bonds formed (2 C=O + 4 O–H = {frm} kJ) identified correctly"), R_(1, "Correct ΔH = broken − formed, with the negative sign", True)],
            [f"Broken: 4(413) + 2(498) = {brk} kJ.", f"Formed: 2(799) + 4(463) = {frm} kJ.", f"ΔH = {brk} − {frm} = {dHb} kJ/mol."], rel=0.01),
    ]})

# ---------------------------------------------------------------- 8 gases
mKClO3 = 4.00
nKClO3 = mKClO3 / chem.molar_mass("KClO3")
nO2 = nKClO3 * 3 / 2
Ptot, Pw = 745.0, 23.8
PO2 = Ptot - Pw
VO2 = nO2 * R * 298.15 / (PO2 / 760)
FRQS.append({
    "id": "frq-08", "title": "Oxygen from potassium chlorate", "kind": "short", "minutes": 14, "topics": ["Gases", "Moles & Stoichiometry"],
    "stem": f"2 KClO₃(s) → 2 KCl(s) + 3 O₂(g)\nA {mKClO3:.2f} g sample of KClO₃ is completely decomposed by heating. The O₂ is collected over water at 25 °C. "
            f"The total pressure in the collection vessel is {Ptot:g} torr, and the vapor pressure of water at 25 °C is {Pw} torr. (1 atm = 760 torr)",
    "parts": [
        num("(a)", "Calculate the number of moles of O₂(g) produced.", nO2, "mol",
            [R_(1, "Converts grams of KClO₃ to moles using its molar mass"), R_(1, "Uses the 3 O₂ : 2 KClO₃ mole ratio for the correct moles of O₂", True)],
            [f"molar mass KClO₃ = {g(chem.molar_mass('KClO3'), 4)} g/mol; moles = {mKClO3:.2f}/{g(chem.molar_mass('KClO3'), 4)} = {g(nKClO3, 4)} mol.", f"moles O₂ = {g(nKClO3, 4)} x 3/2 = {g(nO2, 4)} mol."]),
        num("(b)", "Calculate the partial pressure of the O₂(g), in torr.", PO2, "torr",
            [R_(1, "Subtracts the water vapor pressure from the total pressure (Dalton's law)", True)],
            [f"P(O₂) = {Ptot:g} − {Pw} = {g(PO2, 4)} torr."], rel=0.005),
        num("(c)", "Calculate the volume, in liters, that the O₂(g) occupies at 25 °C and the partial pressure from part (b).", VO2, "L",
            [R_(1, "Converts pressure to atm and temperature to kelvin and uses PV = nRT"), R_(1, "Correct volume with units", True)],
            [f"P = {g(PO2, 4)} torr / 760 = {g(PO2 / 760, 4)} atm; T = 298.15 K.", f"V = nRT/P = ({g(nO2, 4)})(0.08206)(298.15) / {g(PO2 / 760, 4)} = {g(VO2)} L."], rel=0.02),
        wr("(d)", "At 25 °C, would helium atoms or oxygen molecules have the greater root-mean-square speed? Justify your answer.",
           [R_(1, "Helium atoms have the greater rms speed"), R_(1, "At the same temperature the average kinetic energy is the same, so the lighter particles (smaller molar mass) must move faster (u_rms = √(3RT/M))")],
           "Helium. At the same temperature all gases have the same average kinetic energy (½mv²). He has a much smaller molar mass than O₂, so its speed must be greater: u_rms = √(3RT/M)."),
    ]})

# ---------------------------------------------------------------- 9 lab / spectrophotometry
mm_cuso4_5 = chem.molar_mass("CuSO4") + 5 * chem.molar_mass("H2O")
m_need = 0.100 * 0.250 * mm_cuso4_5
c_unk = 0.0400 * 0.455 / 0.280
FRQS.append({
    "id": "frq-09", "title": "Preparing and analyzing a copper(II) solution", "kind": "short", "minutes": 14, "topics": ["Solutions"],
    "stem": "A student prepares a standard copper(II) sulfate solution from the hydrate CuSO₄·5H₂O and uses a spectrophotometer to find the concentration of an unknown Cu²⁺ solution.",
    "parts": [
        num("(a)", "Calculate the mass of CuSO₄·5H₂O needed to prepare 100.0 mL of 0.250 M CuSO₄(aq).", m_need, "g",
            [R_(1, "Moles needed = (0.1000 L)(0.250 M) = 0.0250 mol"), R_(1, "Molar mass of the hydrate (249.7 g/mol, including 5 H₂O) used for the correct mass", True)],
            ["moles = 0.1000 L x 0.250 mol/L = 0.0250 mol.", f"molar mass CuSO₄·5H₂O = {g(chem.molar_mass('CuSO4'), 5)} + 5({g(chem.molar_mass('H2O'), 4)}) = {g(mm_cuso4_5, 4)} g/mol.", f"mass = 0.0250 x {g(mm_cuso4_5, 4)} = {g(m_need)} g."]),
        wr("(b)", "Describe how to prepare the 100.0 mL solution accurately after the solid has been weighed. Name the glassware used.",
           [R_(1, "Dissolve the solid in a portion (less than 100 mL) of distilled water in a beaker, then transfer quantitatively (rinsing) into a 100.0 mL volumetric flask"),
            R_(1, "Add distilled water to the calibration mark (bottom of the meniscus at the line) and mix thoroughly by inverting")],
           "Dissolve the weighed solid in less than 100 mL of distilled water in a beaker, transfer it (rinsing the beaker into the flask) to a 100.0 mL volumetric flask, add water until the bottom of the meniscus is at the mark, then stopper and invert several times to mix."),
        num("(c)", "A 0.0400 M standard has an absorbance of 0.280 at the analysis wavelength. The unknown has an absorbance of 0.455. Assuming Beer's law (A = εbc) holds, calculate the concentration of the unknown.", c_unk, "M",
            [R_(1, "Recognizes A is proportional to c for the same cell: c_unk = c_std x (A_unk / A_std)"), R_(1, "Correct concentration", True)],
            [f"c_unk = 0.0400 x (0.455 / 0.280) = {g(c_unk)} M."], rel=0.01),
        wr("(d)", "Explain why the absorbance measurements are made at the wavelength of maximum absorbance (λmax).",
           [R_(1, "At λmax the absorbance changes the most per unit concentration (greatest sensitivity), and small wavelength errors have the smallest effect, so Beer's law is followed most closely")],
           "At λmax the solution absorbs most strongly, so the absorbance is most sensitive to concentration (largest slope in the Beer's-law plot) and small errors in the wavelength setting change the reading the least."),
    ]})

# ---------------------------------------------------------------- 10 atomic structure & periodicity
dE = 2.178e-18 * (1 / 4 - 1 / 16)
lam = 6.626e-34 * 3.00e8 / dE * 1e9
FRQS.append({
    "id": "frq-10", "title": "Atomic structure and periodic trends", "kind": "short", "minutes": 14, "topics": ["Electronic Structure & Periodicity"],
    "stem": "Answer the following about atomic structure and periodic trends. (Use h = 6.626 x 10⁻³⁴ J·s, c = 3.00 x 10⁸ m/s, and Eₙ = −2.178 x 10⁻¹⁸ J / n² for hydrogen.)",
    "parts": [
        wr("(a)", "Write the ground-state electron configuration of the Fe²⁺ ion and state the number of unpaired electrons in it.",
           [R_(1, "1s² 2s² 2p⁶ 3s² 3p⁶ 3d⁶ ([Ar] 3d⁶): the 4s electrons are removed first"), R_(1, "Four unpaired electrons (3d⁶: one paired set, four singly occupied orbitals)")],
           "Fe is [Ar] 4s² 3d⁶. Fe²⁺ loses the two 4s electrons: [Ar] 3d⁶. In the five 3d orbitals, six electrons give one pair and four unpaired electrons."),
        wr("(b)", "Explain why the first ionization energy of oxygen is lower than that of nitrogen.",
           [R_(1, "Nitrogen's 2p subshell is half-filled (three electrons in separate orbitals); oxygen has one 2p orbital with a paired set of electrons"),
            R_(1, "Electron–electron repulsion between the paired electrons in oxygen makes that electron easier to remove")],
           "N has the configuration 2p³ with one electron in each p orbital. O is 2p⁴, so one orbital holds a pair. The repulsion between the two paired electrons raises their energy, so the electron is removed more easily from O than from N."),
        wr("(c)", "Explain why a magnesium atom has a smaller atomic radius than a sodium atom.",
           [R_(1, "Mg has more protons (greater nuclear charge) and the outer electrons are in the same shell (n = 3) with similar shielding"),
            R_(1, "The greater effective nuclear charge pulls the outer electrons closer to the nucleus")],
           "Na and Mg have valence electrons in the same shell (n = 3) with similar shielding from the core, but Mg has one more proton. The greater effective nuclear charge pulls the outer electrons closer, giving a smaller radius."),
        num("(d)", "Calculate the wavelength, in nm, of the photon emitted when an electron in a hydrogen atom falls from n = 4 to n = 2.", lam, "nm",
            [R_(1, "Correct wavelength (ΔE = 2.178e-18(1/4 − 1/16), λ = hc/ΔE)", True)],
            [f"ΔE = 2.178e-18 (1/2² − 1/4²) = {g(dE)} J.", f"λ = hc/ΔE = (6.626e-34)(3.00e8) / {g(dE)} = {g(lam / 1e9)} m = {g(lam)} nm."], rel=0.015),
    ]})


def main():
    for q in FRQS:
        q["points"] = sum(p["points"] for p in q["parts"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(FRQS, indent=1, ensure_ascii=False), encoding="utf-8")
    tot = sum(q["points"] for q in FRQS)
    print(f"wrote {len(FRQS)} free-response questions ({tot} points, {sum(len(q['parts']) for q in FRQS)} parts) to {OUT.relative_to(ROOT)}")
    for q in FRQS:
        nums = [(p["label"], p["answer_text"]) for p in q["parts"] if p["type"] == "numeric"]
        print(f"  {q['id']} {q['title']:<46} {q['points']:>2} pts  " + "  ".join(f"{l}={a}" for l, a in nums))


if __name__ == "__main__":
    main()
