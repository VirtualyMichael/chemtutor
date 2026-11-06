"""Chemistry cheat sheet content (formulas, algorithms, notation, constants, lookup tables).

Plain-text math with unicode sub/superscripts so it renders anywhere and is searchable.
Entry kinds: eq (name/eq/note), steps (ordered algorithm), table (head/rows), list (bullets).
"""
from __future__ import annotations
from . import chem


def E(name, eq, note=""):
    return {"t": "eq", "name": name, "eq": eq, "note": note}


def S(name, steps):
    return {"t": "steps", "name": name, "steps": steps}


def T(name, head, rows):
    return {"t": "table", "name": name, "head": head, "rows": rows}


def L(name, items):
    return {"t": "list", "name": name, "items": items}


SECTIONS = [
    {"id": "start", "title": "Problem-solving checklist", "entries": [
        S("Attack any word problem", [
            "Write what the question asks for, with its units.",
            "List every given value with units. Convert °C → K and mL → L now.",
            "Pick the relationship that connects givens to the unknown (search this sheet by keyword).",
            "Rearrange the formula for the unknown BEFORE plugging in numbers.",
            "Plug in, carry units through, calculate.",
            "Round to the right significant figures and state units.",
            "Sanity check: sign, size, and units make sense?"]),
        L("Classic mistakes", [
            "Forgetting to convert °C to kelvin in any gas, thermodynamics or Arrhenius problem.",
            "Using mL instead of L in molarity or gas-law calculations.",
            "Using the mass of a compound as if it were moles. Always convert to moles first.",
            "Forgetting the mole ratio from the balanced equation.",
            "Mixing J and kJ (ΔG = ΔH − TΔS needs the same energy unit).",
            "Using the wrong R for the units you have (see Constants).",
            "Putting solids and pure liquids in K or Q expressions."]),
    ]},
    {"id": "units", "title": "Units, measurement & math", "entries": [
        T("SI prefixes", ["Prefix", "Symbol", "Factor"], [
            ["tera", "T", "10¹²"], ["giga", "G", "10⁹"], ["mega", "M", "10⁶"], ["kilo", "k", "10³"],
            ["deci", "d", "10⁻¹"], ["centi", "c", "10⁻²"], ["milli", "m", "10⁻³"], ["micro", "µ", "10⁻⁶"],
            ["nano", "n", "10⁻⁹"], ["pico", "p", "10⁻¹²"]]),
        T("Useful conversions", ["Quantity", "Equivalent"], [
            ["Length", "1 in = 2.54 cm (exact) · 1 mi = 1.609 km · 1 m = 100 cm = 1000 mm"],
            ["Mass", "1 lb = 453.6 g = 0.4536 kg · 1 kg = 1000 g"],
            ["Volume", "1 L = 1000 mL = 1000 cm³ · 1 mL = 1 cm³ · 1 gal = 3.785 L · 1 fl oz = 29.57 mL"],
            ["Time", "1 h = 60 min = 3600 s"],
            ["Energy", "1 cal = 4.184 J · 1 kJ = 1000 J · 1 L·atm = 101.3 J"],
            ["Pressure", "1 atm = 760 torr = 760 mmHg = 101.325 kPa = 1.01325 bar"]]),
        E("Temperature", "K = °C + 273.15   ·   °F = (9/5)°C + 32   ·   °C = (5/9)(°F − 32)",
          "A change of 1 °C equals a change of 1 K."),
        E("Density", "ρ = m / V   →   m = ρV   ·   V = m / ρ", "Water ≈ 1.00 g/mL. Unit equivalence: 1 g/mL = 1 g/cm³ = 1000 kg/m³."),
        E("Percent error", "% error = |measured − accepted| / accepted × 100"),
        L("Significant figures", [
            "Nonzero digits are always significant.",
            "Zeros between nonzero digits are significant (4001 → 4).",
            "Leading zeros are never significant (0.0045 → 2).",
            "Trailing zeros count only if there is a decimal point (100. → 3, 100.0 → 4, 100 → ambiguous).",
            "Multiply/divide: keep the fewest sig figs of the inputs.",
            "Add/subtract: keep the fewest decimal places.",
            "Exact numbers (counts, defined conversions like 1000 mL/L) have unlimited sig figs.",
            "Round only at the end; keep extra digits in between."]),
        E("Scientific notation", "N = a × 10ⁿ with 1 ≤ a < 10",
          "Moving the decimal LEFT makes n positive; RIGHT makes it negative. Type as 3.2e-5 or 3.2 x 10^-5."),
        S("Dimensional analysis (factor-label)", [
            "Start with the given quantity and its unit.",
            "Multiply by conversion factors written as fractions equal to 1 (e.g. 1000 m / 1 km).",
            "Arrange each fraction so the unit you want to cancel is on the opposite side.",
            "Continue until only the desired unit remains.",
            "Multiply the numbers across; divide by the denominators."]),
    ]},
    {"id": "constants", "title": "Constants", "entries": [
        T("Fundamental constants", ["Name", "Symbol", "Value"], [
            ["Gas constant", "R", "0.08206 L·atm/(mol·K) = 8.314 J/(mol·K) = 62.36 L·torr/(mol·K)"],
            ["Avogadro's number", "Nₐ", "6.022 × 10²³ mol⁻¹"],
            ["Planck's constant", "h", "6.626 × 10⁻³⁴ J·s"],
            ["Speed of light", "c", "3.00 × 10⁸ m/s"],
            ["Faraday constant", "F", "96,485 C per mole of electrons"],
            ["Elementary charge", "e", "1.602 × 10⁻¹⁹ C"],
            ["Rydberg energy (Bohr)", "R_H", "2.178 × 10⁻¹⁸ J"],
            ["Ion-product of water (25 °C)", "K_w", "1.0 × 10⁻¹⁴"],
            ["Nernst factor (25 °C, log₁₀)", "RT ln10 / F", "0.0592 V"],
            ["Molar volume, ideal gas at STP (0 °C, 1 atm)", "V_m", "22.4 L/mol"]]),
        T("Water properties", ["Property", "Value"], [
            ["Specific heat, liquid", "4.184 J/(g·°C)"], ["Specific heat, ice", "2.09 J/(g·°C)"],
            ["Specific heat, steam", "2.01 J/(g·°C)"],
            ["Heat of fusion", "6.01 kJ/mol (334 J/g) at 0 °C"],
            ["Heat of vaporization", "40.7 kJ/mol (2260 J/g) at 100 °C"],
            ["Freezing-point depression constant K_f", "1.86 °C·kg/mol"],
            ["Boiling-point elevation constant K_b", "0.512 °C·kg/mol"]]),
    ]},
    {"id": "naming", "title": "Nomenclature & notation", "entries": [
        T("Common polyatomic ions", ["Name", "Formula"], [
            ["ammonium", "NH₄⁺"], ["hydronium", "H₃O⁺"], ["hydroxide", "OH⁻"], ["nitrate", "NO₃⁻"], ["nitrite", "NO₂⁻"],
            ["sulfate", "SO₄²⁻"], ["sulfite", "SO₃²⁻"], ["phosphate", "PO₄³⁻"], ["carbonate", "CO₃²⁻"],
            ["hydrogen carbonate (bicarbonate)", "HCO₃⁻"], ["acetate", "C₂H₃O₂⁻ (CH₃COO⁻)"], ["cyanide", "CN⁻"],
            ["permanganate", "MnO₄⁻"], ["chromate", "CrO₄²⁻"], ["dichromate", "Cr₂O₇²⁻"], ["chlorate", "ClO₃⁻"],
            ["perchlorate", "ClO₄⁻"], ["hypochlorite", "ClO⁻"], ["peroxide", "O₂²⁻"]]),
        T("Typical monatomic ion charges", ["Group / element", "Ion"], [
            ["Group 1 (Li, Na, K…)", "+1"], ["Group 2 (Mg, Ca, Ba…)", "+2"], ["Al", "3+"], ["Ag", "+1"], ["Zn", "2+"],
            ["Fe", "2+ or 3+"], ["Cu", "+ or 2+"], ["Group 15 (N, P)", "3−"], ["Group 16 (O, S)", "2−"],
            ["Group 17 (F, Cl, Br, I)", "1−"]]),
        T("Molecular-compound prefixes", ["Prefix", "Number"], [
            ["mono", "1"], ["di", "2"], ["tri", "3"], ["tetra", "4"], ["penta", "5"], ["hexa", "6"],
            ["hepta", "7"], ["octa", "8"], ["nona", "9"], ["deca", "10"]]),
        L("Naming rules", [
            "Ionic: cation name + anion name ending in -ide (NaCl sodium chloride).",
            "Metals with several charges: Roman numeral = charge (FeCl₃ iron(III) chloride).",
            "Molecular (two nonmetals): prefixes for each element; omit mono- on the first (N₂O₄ dinitrogen tetroxide).",
            "Binary acids: hydro- + stem + -ic acid (HCl hydrochloric acid).",
            "Oxyacids: anion -ate → -ic acid, -ite → -ous acid (H₂SO₄ sulfuric, H₂SO₃ sulfurous).",
            "Hydrates: name + prefix + hydrate (CuSO₄·5H₂O copper(II) sulfate pentahydrate)."]),
        L("Strong acids and bases (everything else is weak)", [
            "Strong acids: HCl, HBr, HI, HNO₃, H₂SO₄ (first proton), HClO₄, HClO₃.",
            "Strong bases: hydroxides of Group 1, plus Ca(OH)₂, Sr(OH)₂, Ba(OH)₂."]),
        T("Solubility rules (water)", ["Group", "Rule"], [
            ["Always soluble", "Group 1 cations and NH₄⁺ · nitrates · acetates · chlorates"],
            ["Mostly soluble", "Cl⁻, Br⁻, I⁻ (except with Ag⁺, Pb²⁺, Hg₂²⁺) · sulfates (except Ba²⁺, Pb²⁺, Sr²⁺; Ca²⁺ slightly)"],
            ["Mostly insoluble", "carbonates, phosphates, sulfides, hydroxides, oxides (except with Group 1 / NH₄⁺; Ba(OH)₂ and Ca(OH)₂ slightly)"]]),
        T("Notation", ["Symbol", "Meaning"], [
            ["(s) (l) (g) (aq)", "solid, liquid, gas, dissolved in water"], ["→", "reaction proceeds to products"],
            ["⇌", "reversible reaction (equilibrium)"], ["Δ over arrow", "heat applied"],
            ["[X]", "molar concentration of X (mol/L)"], ["M", "molarity, mol solute / L solution"],
            ["m", "molality, mol solute / kg solvent"], ["ν (nu)", "frequency (Hz = s⁻¹)"], ["λ (lambda)", "wavelength"],
            ["ΔH, ΔS, ΔG", "change in enthalpy, entropy, free energy"], ["°  (superscript)", "standard state (1 atm or 1 M, usually 25 °C)"],
            ["n", "moles"], ["i", "van't Hoff factor"], ["Q", "reaction quotient"], ["K", "equilibrium constant"]]),
        L("Reaction types", [
            "Synthesis: A + B → AB.   Decomposition: AB → A + B.",
            "Single replacement: A + BC → AC + B.   Double replacement: AB + CD → AD + CB.",
            "Combustion: hydrocarbon + O₂ → CO₂ + H₂O.",
            "Acid–base: acid + base → salt + water.   Precipitation: two solutions form an insoluble solid.",
            "Redox: electrons transferred (oxidation = loss, reduction = gain)."]),
        S("Balance a chemical equation", [
            "Write the correct formulas for all reactants and products (never change subscripts).",
            "Count atoms of each element on both sides.",
            "Balance elements that appear in only one compound on each side first; leave H and O (or free elements) for last.",
            "Adjust coefficients only. Use fractions if helpful, then multiply through to clear them.",
            "Recount every element, and check the total charge for ionic equations."]),
        S("Write a net ionic equation", [
            "Write the balanced molecular equation with states.",
            "Split strong electrolytes (soluble salts, strong acids/bases) into ions.",
            "Cancel spectator ions that appear unchanged on both sides.",
            "Rewrite what remains, and check atoms and charge balance."]),
    ]},
    {"id": "moles", "title": "Moles & stoichiometry", "entries": [
        E("Moles from mass", "n = m / M", "m in g, M (molar mass) in g/mol. M = sum of atomic masses from the periodic table."),
        E("Particles", "N = n · Nₐ   with Nₐ = 6.022 × 10²³ per mol"),
        E("Percent composition", "% element = (subscript × M_element) / M_compound × 100"),
        E("Percent yield", "% yield = actual yield / theoretical yield × 100"),
        S("Mass → mass stoichiometry", [
            "Balance the equation.",
            "Convert grams of the given substance → moles (÷ molar mass).",
            "Multiply by the mole ratio (coefficient wanted / coefficient given).",
            "Convert moles of the wanted substance → grams (× molar mass)."]),
        S("Limiting reagent", [
            "Convert each reactant mass to moles.",
            "Divide each by its coefficient; the SMALLEST result is limiting.",
            "Use the limiting reagent's moles for all product calculations (theoretical yield).",
            "Leftover excess = initial moles − moles consumed (via mole ratio), converted to grams."]),
        S("Empirical formula from percent or mass data", [
            "Assume 100 g so percents become grams.",
            "Convert each element's grams to moles.",
            "Divide all by the smallest mole value.",
            "If a result is near x.5, multiply all by 2 (x.33 or x.67 → ×3) to get whole numbers.",
            "Those whole numbers are the subscripts."]),
        E("Molecular formula", "n = M_molecular / M_empirical   →   molecular = (empirical)ₙ"),
        S("Combustion analysis (C, H, O compounds)", [
            "Moles C = moles CO₂ collected.",
            "Moles H = 2 × moles H₂O collected.",
            "Mass O = sample mass − mass C − mass H; convert to moles.",
            "Find the empirical formula from the mole ratio."]),
    ]},
    {"id": "solutions", "title": "Solutions", "entries": [
        E("Molarity", "M = mol solute / L solution", "Convert mL to L. n = M·V."),
        E("Dilution", "M₁V₁ = M₂V₂", "Moles of solute stay the same; volumes can be in any unit if both match."),
        E("Mass percent", "% (m/m) = mass solute / mass solution × 100"),
        E("Molality", "m = mol solute / kg solvent", "Depends on solvent mass, not volume, so it does not change with temperature."),
        E("Mole fraction", "Xₐ = nₐ / n_total", "Mole fractions sum to 1."),
        E("Parts per million", "ppm = mass solute / mass solution × 10⁶", "For dilute water solutions, 1 ppm ≈ 1 mg/L."),
        S("Titration / solution stoichiometry", [
            "Write the balanced neutralization equation.",
            "Find moles of the known solution: n = M·V (V in L).",
            "Use the mole ratio from the equation to get moles of the unknown.",
            "Divide by volume (for molarity) or by molarity (for volume)."]),
        E("Freezing-point depression", "ΔT_f = i · K_f · m", "K_f(water) = 1.86 °C·kg/mol. Freezing point = 0 − ΔT_f."),
        E("Boiling-point elevation", "ΔT_b = i · K_b · m", "K_b(water) = 0.512 °C·kg/mol. Boiling point = 100 + ΔT_b."),
        E("Osmotic pressure", "π = i · M · R · T", "R = 0.08206 L·atm/(mol·K), T in K, π in atm."),
        E("Raoult's law", "P_solution = X_solvent · P°_solvent"),
        E("Henry's law", "S = k_H · P_gas", "Gas solubility is proportional to its partial pressure."),
        T("van't Hoff factor i (ideal)", ["Solute", "i"], [
            ["glucose, sucrose, urea (nonelectrolytes)", "1"], ["NaCl, KBr, HCl", "2"],
            ["CaCl₂, Na₂SO₄, MgCl₂", "3"], ["AlCl₃, Na₃PO₄", "4"]]),
    ]},
    {"id": "gases", "title": "Gases", "entries": [
        E("Ideal gas law", "PV = nRT", "P in atm, V in L, T in K, R = 0.08206 L·atm/(mol·K)."),
        E("Boyle's law (T, n constant)", "P₁V₁ = P₂V₂"),
        E("Charles's law (P, n constant)", "V₁/T₁ = V₂/T₂", "T in kelvin."),
        E("Gay-Lussac's law (V, n constant)", "P₁/T₁ = P₂/T₂"),
        E("Combined gas law", "P₁V₁/T₁ = P₂V₂/T₂"),
        E("Avogadro's law (P, T constant)", "V₁/n₁ = V₂/n₂"),
        E("Dalton's law", "P_total = P₁ + P₂ + …   ·   Pᵢ = Xᵢ · P_total"),
        E("Gas collected over water", "P_gas = P_atm − P_water vapor"),
        E("Gas density / molar mass", "d = PM / RT   ·   M = dRT / P", "d in g/L, M in g/mol."),
        E("Graham's law (effusion)", "rate₁ / rate₂ = √(M₂ / M₁)", "Lighter gas effuses faster."),
        E("Kinetic theory: speed", "u_rms = √(3RT / M)", "Use R = 8.314 J/(mol·K), M in kg/mol, result in m/s."),
        E("Average kinetic energy", "KE_avg = (3/2) R T per mole", "Depends only on temperature."),
        E("van der Waals (real gas)", "(P + a n²/V²)(V − n b) = nRT"),
        S("Gas problem routine", [
            "Convert temperature to K, pressure to atm, volume to L.",
            "Decide which variable is unknown and which law connects the others.",
            "Choose R to match units (0.08206 for atm and L).",
            "Rearrange first, then substitute and calculate."]),
    ]},
    {"id": "thermo", "title": "Thermochemistry", "entries": [
        E("Heat from temperature change", "q = m · c · ΔT", "ΔT = T_final − T_initial. Water: c = 4.184 J/(g·°C). Positive q = heat absorbed."),
        E("Heat of phase change", "q = n · ΔH_phase", "Melting: ΔH_fus = 6.01 kJ/mol. Boiling: ΔH_vap = 40.7 kJ/mol. Temperature stays constant."),
        E("Enthalpy from formation data", "ΔH°_rxn = Σ n ΔH°f(products) − Σ n ΔH°f(reactants)",
          "ΔH°f of an element in its standard state = 0. Multiply by coefficients."),
        S("Hess's law", [
            "Write the target reaction.",
            "Arrange the given reactions so their sum equals the target.",
            "Reverse a reaction → change the sign of its ΔH.",
            "Multiply a reaction by k → multiply its ΔH by k.",
            "Add the equations (cancel species that appear on both sides) and add the ΔH values."]),
        E("Calorimetry", "q_rxn = −(q_solution + q_calorimeter)", "q_cal = C_cal · ΔT. ΔH per mole = q_rxn / n."),
        E("Bond enthalpies", "ΔH ≈ Σ(bonds broken) − Σ(bonds formed)", "Breaking bonds costs energy; forming bonds releases it."),
        E("First law", "ΔE = q + w   ·   w = −P ΔV", "1 L·atm = 101.3 J. Work done BY the system is negative w."),
        T("Sign conventions", ["Quantity", "Meaning"], [
            ["ΔH < 0", "exothermic (heat released, surroundings warm)"], ["ΔH > 0", "endothermic (heat absorbed)"],
            ["q > 0", "system gains heat"], ["w < 0", "system does work on surroundings (expansion)"]]),
        S("Heating curve (ice at −10 °C → steam at 120 °C)", [
            "Warm ice: q = m·c_ice·ΔT.",
            "Melt: q = n·ΔH_fus (temperature constant at 0 °C).",
            "Warm liquid: q = m·c_water·ΔT.",
            "Boil: q = n·ΔH_vap (constant at 100 °C).",
            "Warm steam: q = m·c_steam·ΔT.",
            "Add all the q values (convert J and kJ consistently)."]),
    ]},
    {"id": "atoms", "title": "Atomic structure & periodicity", "entries": [
        E("Subatomic counts", "neutrons = A − Z   ·   electrons (neutral) = Z   ·   electrons (ion) = Z − charge",
          "A = mass number, Z = atomic number. Cation: lost electrons; anion: gained."),
        E("Average atomic mass", "M_avg = Σ (isotope mass × fractional abundance)", "Convert percent to fraction (÷ 100)."),
        E("Wave relation", "c = λ ν", "c = 3.00×10⁸ m/s, λ in m (1 nm = 10⁻⁹ m), ν in s⁻¹."),
        E("Photon energy", "E = h ν = h c / λ", "h = 6.626×10⁻³⁴ J·s. Result in joules per photon."),
        E("Bohr energy levels (hydrogen)", "Eₙ = −2.178×10⁻¹⁸ J / n²"),
        E("Energy of a transition", "ΔE = 2.178×10⁻¹⁸ J · (1/n_f² − 1/n_i²)", "Negative = emitted photon. Wavelength from |ΔE| = hc/λ."),
        E("de Broglie wavelength", "λ = h / (m v)", "m in kg, v in m/s."),
        T("Quantum numbers", ["Symbol", "Name", "Allowed values"], [
            ["n", "principal (shell)", "1, 2, 3, …"], ["l", "angular momentum (subshell)", "0 to n−1  (0=s, 1=p, 2=d, 3=f)"],
            ["mₗ", "magnetic (orbital)", "−l to +l  (s:1, p:3, d:5, f:7 orbitals)"], ["mₛ", "spin", "+½ or −½"]]),
        L("Filling electrons", [
            "Aufbau order: 1s 2s 2p 3s 3p 4s 3d 4p 5s 4d 5p 6s 4f 5d 6p 7s.",
            "Pauli exclusion: max 2 electrons per orbital, with opposite spins.",
            "Hund's rule: fill degenerate orbitals singly (parallel spins) before pairing.",
            "Capacity: s 2, p 6, d 10, f 14 electrons.",
            "Exceptions: Cr = [Ar] 4s¹ 3d⁵, Cu = [Ar] 4s¹ 3d¹⁰ (half/full d-shells are extra stable).",
            "Cations: remove electrons from the highest n first (4s before 3d).",
            "Valence electrons of a main-group element: group number for groups 1–2; group number − 10 for groups 13–18."]),
        T("Periodic trends", ["Property", "Across a period →", "Down a group ↓"], [
            ["Atomic radius", "decreases", "increases"], ["Ionization energy", "increases", "decreases"],
            ["Electronegativity", "increases", "decreases"], ["Electron affinity (magnitude)", "generally increases", "generally decreases"],
            ["Metallic character", "decreases", "increases"]]),
        L("Ions & size", ["Cations are smaller than their atoms; anions are larger.",
                          "Isoelectronic ions: more protons → smaller radius (Al³⁺ < Mg²⁺ < Na⁺ < Ne < F⁻ < O²⁻)."]),
    ]},
    {"id": "bonding", "title": "Bonding & geometry", "entries": [
        S("Draw a Lewis structure", [
            "Count total valence electrons (add for anions, subtract for cations).",
            "Put the least electronegative atom (not H) in the center and connect atoms with single bonds.",
            "Complete octets on the outer atoms with lone pairs.",
            "Put leftover electrons on the central atom.",
            "If the central atom lacks an octet, convert lone pairs to double/triple bonds.",
            "Check formal charges; prefer structures with charges closest to zero."]),
        E("Formal charge", "FC = V − N − B/2", "V valence electrons, N nonbonding electrons, B electrons in bonds (so B/2 = number of bonds)."),
        L("Octet exceptions", ["Incomplete octet: Be (4), B (6).", "Expanded octet allowed for period 3+ (P, S, Cl, Xe…).",
                               "Odd-electron molecules (NO, NO₂) have a radical."]),
        T("Polarity by electronegativity difference (rough)", ["Δ EN", "Bond type"], [
            ["< 0.4", "nonpolar covalent"], ["0.4 – 1.7", "polar covalent"], ["> 1.7", "ionic"]]),
        T("VSEPR geometries", ["Electron groups", "Lone pairs", "Shape", "Ideal angle(s)", "Hybridization"], [
            ["2", "0", "linear", "180°", "sp"],
            ["3", "0", "trigonal planar", "120°", "sp²"], ["3", "1", "bent", "<120°", "sp²"],
            ["4", "0", "tetrahedral", "109.5°", "sp³"], ["4", "1", "trigonal pyramidal", "<109.5°", "sp³"],
            ["4", "2", "bent", "<109.5°", "sp³"],
            ["5", "0", "trigonal bipyramidal", "90°, 120°", "sp³d"], ["5", "1", "seesaw", "~90°, ~120°", "sp³d"],
            ["5", "2", "T-shaped", "~90°", "sp³d"], ["5", "3", "linear", "180°", "sp³d"],
            ["6", "0", "octahedral", "90°", "sp³d²"], ["6", "1", "square pyramidal", "~90°", "sp³d²"],
            ["6", "2", "square planar", "90°", "sp³d²"]]),
        L("Sigma and pi bonds", ["Single bond = 1 σ.  Double = 1 σ + 1 π.  Triple = 1 σ + 2 π.",
                                 "Count groups around an atom: bonds (any multiplicity) + lone pairs = electron groups."]),
        L("Intermolecular forces (weakest → strongest, for similar size)", [
            "London dispersion (all molecules; grows with size/polarizability).",
            "Dipole–dipole (polar molecules).",
            "Hydrogen bonding (H bonded to N, O or F, attracted to a lone pair on N, O, F).",
            "Ion–dipole (ions in polar solvent) and ionic bonds are strongest.",
            "Stronger forces → higher boiling/melting point, higher viscosity, lower vapor pressure."]),
        E("Bond order", "BO = (bonding e⁻ − antibonding e⁻) / 2", "Higher bond order → shorter, stronger bond."),
    ]},
    {"id": "liquids", "title": "Liquids & solids", "entries": [
        E("Clausius–Clapeyron", "ln(P₂/P₁) = −(ΔH_vap / R)(1/T₂ − 1/T₁)", "R = 8.314 J/(mol·K), T in K, ΔH in J/mol."),
        E("Bragg's law", "n λ = 2 d sin θ", "X-ray diffraction from crystal planes spacing d."),
        T("Atoms per cubic unit cell", ["Cell", "Atoms"], [["simple cubic", "1"], ["body-centered (bcc)", "2"], ["face-centered (fcc)", "4"]]),
        L("Crystal types", ["Ionic: high m.p., brittle, conducts when molten/dissolved.",
                            "Metallic: conducts, malleable.", "Covalent network (diamond, SiO₂): very hard, very high m.p.",
                            "Molecular: low m.p., held by intermolecular forces."]),
    ]},
    {"id": "kinetics", "title": "Kinetics", "entries": [
        E("Rate law", "rate = k [A]ᵐ [B]ⁿ", "Orders m, n come from experiments (not from the balanced equation). Overall order = m + n."),
        T("Integrated rate laws", ["Order", "Integrated law", "Straight-line plot", "Half-life", "Units of k"], [
            ["0", "[A] = [A]₀ − kt", "[A] vs t", "t½ = [A]₀ / 2k", "M/s"],
            ["1", "ln[A] = ln[A]₀ − kt", "ln[A] vs t", "t½ = 0.693 / k", "1/s"],
            ["2", "1/[A] = 1/[A]₀ + kt", "1/[A] vs t", "t½ = 1 / (k[A]₀)", "1/(M·s)"]]),
        E("First-order decay (shortcut)", "[A] = [A]₀ e^(−kt)   ·   N = N₀ (½)^(t / t½)"),
        E("Arrhenius equation", "k = A e^(−Ea / RT)   ·   ln k = ln A − Ea/(RT)", "R = 8.314 J/(mol·K); Ea in J/mol."),
        E("Two-temperature form", "ln(k₂/k₁) = (Ea / R)(1/T₁ − 1/T₂)"),
        S("Method of initial rates", [
            "Pick two experiments where only one reactant's concentration changes.",
            "Divide the rate ratio by the concentration ratio raised to the unknown order: rate₂/rate₁ = ([A]₂/[A]₁)ᵐ.",
            "Solve for m (usually 0, 1 or 2); repeat for each reactant.",
            "Plug any experiment into the rate law to solve for k (with units)."]),
        L("Mechanisms", ["Each elementary step's rate law follows its molecularity.",
                         "The slowest step (rate-determining) sets the overall rate law.",
                         "A catalyst lowers Ea and is regenerated; it does not change K or ΔH."]),
    ]},
    {"id": "equilibrium", "title": "Equilibrium", "entries": [
        E("Equilibrium constant", "aA + bB ⇌ cC + dD:   K = [C]ᶜ[D]ᵈ / ([A]ᵃ[B]ᵇ)",
          "Leave out pure solids and liquids. Kc uses concentrations; Kp uses partial pressures (atm)."),
        E("Kp and Kc", "Kp = Kc (RT)^Δn", "Δn = moles of gaseous products − moles of gaseous reactants. R = 0.08206, T in K."),
        E("Manipulating K", "Reverse reaction: 1/K  ·  multiply coefficients by n: Kⁿ  ·  add reactions: multiply their K's"),
        E("Reaction quotient", "Q has the same form as K but uses the current concentrations",
          "Q < K → shifts forward (to products). Q > K → shifts reverse. Q = K → at equilibrium."),
        S("ICE table", [
            "Write the balanced equation and the K expression.",
            "Make a table of Initial, Change (+x or −x scaled by coefficients), Equilibrium concentrations.",
            "Substitute the equilibrium row into K and solve for x.",
            "If K is small (<10⁻³) and x is under 5% of the initial value, you may drop x from (C − x).",
            "Otherwise solve the quadratic: x = (−b ± √(b² − 4ac)) / 2a; keep the physical root.",
            "Compute the requested equilibrium concentrations and check by recalculating K."]),
        T("Le Chatelier", ["Disturbance", "Shift"], [
            ["Add reactant / remove product", "toward products"], ["Add product / remove reactant", "toward reactants"],
            ["Increase pressure (decrease volume)", "toward fewer moles of gas"], ["Increase temperature", "endothermic direction (K changes)"],
            ["Add catalyst or inert gas (constant V)", "no shift"]]),
        E("Solubility product", "AₘBₙ(s) ⇌ mA + nB:   Ksp = [A]ᵐ[Bₙ]ⁿ", "AgCl: Ksp = s². Ca(OH)₂: Ksp = 4s³. Precipitate forms if Q > Ksp."),
    ]},
    {"id": "acidbase", "title": "Acids & bases", "entries": [
        E("pH and pOH", "pH = −log[H₃O⁺]   ·   pOH = −log[OH⁻]   ·   pH + pOH = 14.00 (25 °C)", "[H₃O⁺] = 10^(−pH)."),
        E("Water", "K_w = [H₃O⁺][OH⁻] = 1.0×10⁻¹⁴"),
        E("Weak acid", "Ka = [H₃O⁺][A⁻] / [HA]   ·   pKa = −log Ka"),
        E("Conjugate pair", "Ka · Kb = K_w   ·   pKa + pKb = 14.00"),
        E("Weak-acid pH (approx.)", "[H₃O⁺] ≈ √(Ka · C)", "Valid if x < 5% of C. Exact: x² + Ka·x − Ka·C = 0."),
        E("Percent ionization", "% = [H₃O⁺]ₑq / C × 100"),
        E("Henderson–Hasselbalch (buffers)", "pH = pKa + log([A⁻] / [HA])", "Equal amounts of acid and base → pH = pKa. Works with moles too if volume is common."),
        S("pH when a strong acid and strong base are mixed", [
            "Find moles of H⁺ (acid: M × V in L × H⁺ per formula) and moles of OH⁻.",
            "Subtract the smaller from the larger; the excess species determines pH.",
            "Divide by total volume (sum of volumes) to get the concentration.",
            "Excess H⁺: pH = −log[H⁺]. Excess OH⁻: pOH = −log[OH⁻], pH = 14 − pOH."]),
        L("Titration curve landmarks", ["Initial: pH of the starting acid/base.",
                                        "Buffer region (weak): at half-equivalence, pH = pKa.",
                                        "Equivalence: moles acid = moles base. Strong–strong pH 7; weak acid + strong base pH > 7.",
                                        "After equivalence: pH set by excess strong titrant."]),
        L("Quick facts", ["Acid donates H⁺ (Brønsted–Lowry); base accepts H⁺.",
                          "Stronger acid → weaker conjugate base.",
                          "Salt of strong acid + strong base: neutral. Weak acid + strong base: basic. Strong acid + weak base: acidic."]),
    ]},
    {"id": "thermod", "title": "Thermodynamics", "entries": [
        E("Gibbs free energy", "ΔG = ΔH − T ΔS", "Make units match: ΔS is usually J/K, ΔH kJ → convert. T in K."),
        T("Spontaneity", ["ΔH", "ΔS", "Spontaneous?"], [
            ["−", "+", "always"], ["+", "−", "never"], ["−", "−", "at low T"], ["+", "+", "at high T"]]),
        E("Crossover temperature", "ΔG = 0   →   T = ΔH / ΔS"),
        E("Entropy change of a reaction", "ΔS° = Σ n S°(products) − Σ n S°(reactants)"),
        E("Free energy and K", "ΔG° = −R T ln K   ·   ΔG = ΔG° + R T ln Q", "R = 8.314 J/(mol·K), so convert ΔG° from kJ to J."),
        E("Free energy of formation", "ΔG°_rxn = Σ n ΔG°f(products) − Σ n ΔG°f(reactants)"),
        L("Entropy qualitatively", ["Gas ≫ liquid > solid.", "More moles of gas on the product side → ΔS > 0.",
                                    "Dissolving a solid, heating, and expanding usually raise entropy.",
                                    "Second law: ΔS_universe > 0 for a spontaneous process."]),
    ]},
    {"id": "electro", "title": "Electrochemistry", "entries": [
        E("Cell potential", "E°_cell = E°_cathode − E°_anode", "Use both as REDUCTION potentials. Do not multiply by coefficients. E° > 0 → spontaneous (galvanic)."),
        E("Free energy", "ΔG° = −n F E°", "F = 96,485 C/mol e⁻; result in J, so ÷1000 for kJ."),
        E("K from E°", "log K = n E° / 0.0592   (25 °C)   ·   ln K = nFE° / RT"),
        E("Nernst equation", "E = E° − (0.0592 / n) log Q   (25 °C)", "Q excludes solids. At equilibrium E = 0."),
        E("Electrolysis: charge", "moles e⁻ = I · t / F", "I in amperes (C/s), t in seconds."),
        E("Electrolysis: mass", "mass = (I · t / (n F)) · M", "n = electrons per ion (e.g. 2 for Cu²⁺)."),
        L("Cell basics", ["Oxidation at the anode; reduction at the cathode (An Ox, Red Cat).",
                          "Galvanic cell: anode (−), cathode (+); electrons flow anode → cathode through the wire.",
                          "Electrolytic cell: anode (+), cathode (−); an outside current drives a non-spontaneous reaction.",
                          "A larger E° means a stronger oxidizing agent."]),
        T("Standard reduction potentials (25 °C)", ["Half-reaction", "E° (V)"], [
            ["F₂ + 2e⁻ → 2F⁻", "+2.87"], ["Au³⁺ + 3e⁻ → Au", "+1.50"], ["Cl₂ + 2e⁻ → 2Cl⁻", "+1.36"],
            ["O₂ + 4H⁺ + 4e⁻ → 2H₂O", "+1.23"], ["Br₂ + 2e⁻ → 2Br⁻", "+1.07"], ["Ag⁺ + e⁻ → Ag", "+0.80"],
            ["Fe³⁺ + e⁻ → Fe²⁺", "+0.77"], ["I₂ + 2e⁻ → 2I⁻", "+0.54"], ["Cu²⁺ + 2e⁻ → Cu", "+0.34"],
            ["2H⁺ + 2e⁻ → H₂", "0.00"], ["Pb²⁺ + 2e⁻ → Pb", "−0.13"], ["Sn²⁺ + 2e⁻ → Sn", "−0.14"],
            ["Ni²⁺ + 2e⁻ → Ni", "−0.25"], ["Fe²⁺ + 2e⁻ → Fe", "−0.44"], ["Zn²⁺ + 2e⁻ → Zn", "−0.76"],
            ["Al³⁺ + 3e⁻ → Al", "−1.66"], ["Mg²⁺ + 2e⁻ → Mg", "−2.37"], ["Na⁺ + e⁻ → Na", "−2.71"],
            ["Li⁺ + e⁻ → Li", "−3.04"]]),
        S("Balance a redox reaction (acidic solution)", [
            "Split into oxidation and reduction half-reactions.",
            "Balance atoms other than O and H.",
            "Balance O by adding H₂O; balance H by adding H⁺.",
            "Balance charge by adding electrons.",
            "Multiply half-reactions so electrons match; add and cancel.",
            "For basic solution, add OH⁻ equal to H⁺ to both sides and combine into H₂O."]),
    ]},
    {"id": "nuclear", "title": "Nuclear chemistry", "entries": [
        T("Decay modes", ["Type", "Particle", "Effect on (A, Z)"], [
            ["alpha", "⁴₂He", "A − 4, Z − 2"], ["beta (β⁻)", "⁰₋₁e", "A same, Z + 1"],
            ["positron (β⁺)", "⁰₊₁e", "A same, Z − 1"], ["electron capture", "⁰₋₁e absorbed", "A same, Z − 1"],
            ["gamma", "γ", "no change"]]),
        E("Radioactive decay", "N = N₀ (½)^(t / t½)   ·   k = 0.693 / t½   ·   ln(N/N₀) = −kt", "Number of half-lives = t / t½."),
        E("Mass–energy", "E = Δm c²   ·   1 u = 931.5 MeV", "Mass defect = (mass of separate nucleons) − (mass of nucleus)."),
        L("Balancing nuclear equations", ["Total mass numbers (A) match on both sides.", "Total atomic numbers (Z) match on both sides."]),
    ]},
]


def payload() -> dict:
    """Everything the cheat-sheet UI needs: sections plus the periodic table (same masses used in problems)."""
    return {"sections": SECTIONS, "elements": chem.elements()}
