"""Checks on the generated problem bank and shared chemistry data.  Run:  python -m unittest tests.test_generated"""
import json, math, re, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import chem, reference, web  # noqa: E402

GEN = {p["id"]: p for p in json.loads((Path(__file__).resolve().parents[1] / "data/problems/generated.json").read_text(encoding="utf-8"))}


class Structure(unittest.TestCase):
    def test_fields_and_uniqueness(self):
        self.assertGreater(len(GEN), 300)
        qs = [p["question"] for p in GEN.values()]
        self.assertEqual(len(qs), len(set(qs)), "duplicate questions")
        for p in GEN.values():
            for k in ("id", "topic", "level", "question", "answer", "answer_text", "steps", "tolerance_rel", "tolerance_abs"):
                self.assertIn(k, p, p["id"])
            self.assertTrue(1 <= p["level"] <= 5, p["id"])
            self.assertTrue(math.isfinite(p["answer"]), p["id"])
            self.assertTrue(p["steps"] and all(s.strip() for s in p["steps"]), p["id"])
            if "x 10^" in p["answer_text"]:
                self.assertIn("scientific notation", p["question"], p["id"])

    def test_all_loaded_together_without_id_clashes(self):
        loaded = web.load_problems()
        files = list((Path(__file__).resolve().parents[1] / "data/problems").glob("*.json"))
        total = sum(len(json.loads(f.read_text(encoding="utf-8"))) for f in files)
        self.assertEqual(len(loaded), total)

    def test_every_answer_grades_correct_and_wrong_answers_do_not(self):
        for p in GEN.values():
            self.assertTrue(web.check_answer(p, p["answer_text"])["correct"], f"{p['id']} rejects its own answer {p['answer_text']!r}")
            self.assertTrue(web.check_answer(p, str(p["answer"]))["correct"], p["id"])
            wrong = p["answer"] * 1.5 if p["answer"] else 1
            if p["answer"] < 0:
                wrong = p["answer"] * 1.5
            self.assertFalse(web.check_answer(p, f"{wrong:.6g}")["correct"], f"{p['id']} accepts a wrong answer")


class KnownValues(unittest.TestCase):
    def near(self, pid, expected, tol):
        self.assertAlmostEqual(GEN[pid]["answer"], expected, delta=tol, msg=pid)

    def test_molar_masses(self):  # NaCl, H2O, CO2, CaCO3, H2SO4, NaOH, Mg(OH)2, glucose
        for i, v in enumerate([58.44, 18.015, 44.009, 100.086, 98.072, 39.997, 58.319, 180.156], 1):
            self.near(f"gen-molarmass-{i:02d}", v, 0.02)

    def test_hess_formation_entropy(self):
        for i, v in enumerate([-110.5, 66.4, -571.6, 1.9], 1):
            self.near(f"gen-hess-{i:02d}", v, 0.01)
        for i, v in enumerate([-890.3, -2219.9, 178.3, -92.2, -137.1, -197.8], 1):
            self.near(f"gen-formation-{i:02d}", v, 0.05)
        for i, v in enumerate([-198.7, -187.9, 160.7, -326.5], 1):
            self.near(f"gen-entropy-{i:02d}", v, 0.05)

    def test_misc_textbook_values(self):
        self.near("gen-speed-02", 15.0, 1e-9)            # 54 km/h
        self.near("gen-ksp-01", 1.342e-5, 1e-8)          # AgCl
        self.near("gen-ecell-01", 1.10, 1e-9)            # Zn/Cu
        self.near("gen-massmass-01", 472.7, 1.0)         # 52.9 g H2 -> H2O
        h = [p for p in GEN.values() if "n = 3 to n = 2" in p["question"] and "wavelength" in p["question"]][0]
        self.assertAlmostEqual(h["answer"], 657, delta=3)  # H-alpha ~656 nm

    def test_periodic_table_data(self):
        self.assertAlmostEqual(chem.molar_mass("Al2(SO4)3"), 342.15, delta=0.05)
        self.assertAlmostEqual(chem.molar_mass("(NH4)2SO4"), 132.14, delta=0.05)
        self.assertEqual(chem.parse("Ca3(PO4)2"), {"Ca": 3, "P": 2, "O": 8})
        self.assertEqual(chem.Z["U"], 92)
        with self.assertRaises(ValueError):
            chem.parse("Xx2")
        grid = [e for e in chem.elements() if "col" in e]
        self.assertEqual(len({(e["col"], e["row"]) for e in grid}), len(grid), "two elements share a cell")


class PlugBack(unittest.TestCase):
    """Independent checks: substitute the answer back into the defining equation."""

    def test_weak_acid_ph(self):
        n = 0
        for p in GEN.values():
            m = re.match(r"What is the pH of a ([\d.]+) M solution of .* \(Ka = ([\d.e+-]+)\)\?", p["question"])
            if not m:
                continue
            C0, Ka, x = float(m[1]), float(m[2]), 10 ** -p["answer"]
            self.assertAlmostEqual(x * x / (C0 - x) / Ka, 1, delta=0.12, msg=p["id"])  # pH given to ~0.02 -> few % in x
            n += 1
        self.assertGreaterEqual(n, 3)

    def test_ice_tables(self):
        n = 0
        for p in GEN.values():
            m = re.search(r"Kc = ([\d.]+)\. If a vessel starts with \[H₂\] = \[I₂\] = ([\d.]+) M.*", p["question"])
            if m:
                K, c0, y = float(m[1]), float(m[2]), p["answer"]
                self.assertAlmostEqual(y * y / (c0 - y / 2) ** 2 / K, 1, delta=0.01, msg=p["id"])
                n += 1
            m = re.search(r"N₂O₄\(g\) ⇌ 2 NO₂\(g\) has Kc = ([\d.]+)\. Starting with ([\d.]+) M", p["question"])
            if m:
                K, c0, y = float(m[1]), float(m[2]), p["answer"]
                self.assertAlmostEqual(y * y / (c0 - y / 2) / K, 1, delta=0.02, msg=p["id"])
                n += 1
        self.assertGreaterEqual(n, 4)

    def test_rate_orders(self):
        n = 0
        for p in GEN.values():
            rows = re.findall(r"\[A\] = ([\d.]+) M, \[B\] = ([\d.]+) M, initial rate = ([\d.e+-]+)", p["question"])
            if len(rows) != 4 or "reaction order" not in p["question"]:
                continue
            r = [float(x[2]) for x in rows]
            which = re.search(r"with respect to ([AB])", p["question"])[1]
            ratio = r[1] / r[0] if which == "A" else r[2] / r[0]
            self.assertAlmostEqual(math.log2(ratio), p["answer"], places=2, msg=p["id"])
            n += 1
        self.assertGreaterEqual(n, 4)

    def test_arrhenius(self):
        for p in GEN.values():
            m = re.match(r"A reaction has rate constant ([\d.e+-]+) s⁻¹ at (\d+) K and ([\d.e+-]+) s⁻¹ at (\d+) K", p["question"])
            if m:
                k1, T1, k2, T2 = float(m[1]), float(m[2]), float(m[3]), float(m[4])
                k2_back = k1 * math.exp(p["answer"] * 1000 / 8.314 * (1 / T1 - 1 / T2))
                self.assertAlmostEqual(k2_back / k2, 1, delta=0.01, msg=p["id"])

    def test_limiting_reagent_is_consistent(self):
        # product mass can never exceed what either reactant alone could make
        for p in GEN.values():
            m = re.match(r"For (.+?), ([\d.]+) g of (\S+) reacts with ([\d.]+) g of (\S+)\. What mass", p["question"])
            if not m:
                continue
            self.assertGreater(p["answer"], 0, p["id"])
            self.assertLess(p["answer"], float(m[2]) + float(m[4]) + 1e-6, f"{p['id']} violates conservation of mass")


class CheatSheet(unittest.TestCase):
    def test_structure(self):
        ids = [s["id"] for s in reference.SECTIONS]
        self.assertEqual(len(ids), len(set(ids)))
        for s in reference.SECTIONS:
            self.assertTrue(s["entries"], s["id"])
            for e in s["entries"]:
                self.assertIn(e["t"], ("eq", "steps", "table", "list"))
                self.assertTrue(e["name"].strip())
                if e["t"] == "table":
                    self.assertTrue(all(len(r) == len(e["head"]) for r in e["rows"]), f"{s['id']}/{e['name']} ragged table")
        json.dumps(reference.payload())  # serializable

    def test_key_formulas_present(self):
        text = json.dumps(reference.SECTIONS, ensure_ascii=False)
        for needle in ["PV = nRT", "M₁V₁ = M₂V₂", "ΔG = ΔH − T ΔS", "Henderson", "Nernst", "q = m · c · ΔT", "Kp = Kc (RT)^Δn", "Hess"]:
            self.assertIn(needle, text)

    def test_every_topic_has_a_cheat_sheet_section(self):
        titles = " ".join(s["title"].lower() for s in reference.SECTIONS)
        for kw in ["gases", "thermochemistry", "kinetics", "equilibrium", "acids", "electrochemistry", "bonding", "solutions", "moles"]:
            self.assertIn(kw, titles)


if __name__ == "__main__":
    unittest.main()
