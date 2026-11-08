import copy
import importlib.util
import json
import os
import random
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "remoteworks-matcher")
spec = importlib.util.spec_from_file_location("match", os.path.join(SKILL, "scripts", "match.py"))
match = importlib.util.module_from_spec(spec)
spec.loader.exec_module(match)

with open(os.path.join(SKILL, "data", "platforms.json"), encoding="utf-8") as f:
    DOC = json.load(f)

PROFILES = [
    "desainer grafis pemula di Indonesia, cari freelance",
    "senior python developer, want a full-time remote job",
    "ibu rumah tangga, mau kerja sampingan tugas kecil",
    "translator and transcriptionist, beginner, freelance",
    "virtual assistant, mid level, anywhere",
    "",
]


def profile(text):
    ns = match.argparse.Namespace(about=text, skills=None, level=None, want=None, country=None)
    return match.build_profile(ns)


def order(platforms, prof):
    return [p["id"] for _, _, p, _ in match.rank(platforms, prof)]


class AffiliateInvariance(unittest.TestCase):
    """Ranking must be identical whatever the affiliate flags say."""

    def test_flags_do_not_change_order(self):
        rng = random.Random(7)
        for text in PROFILES:
            prof = profile(text)
            base = order(DOC["platforms"], prof)
            for mode in ("all_true", "all_false", "random", "invert"):
                ps = copy.deepcopy(DOC["platforms"])
                for p in ps:
                    p["affiliate"] = {"all_true": True, "all_false": False,
                                      "random": rng.random() < 0.5, "invert": not p["affiliate"]}[mode]
                self.assertEqual(base, order(ps, prof), f"{mode} changed ranking for {text!r}")

    def test_score_never_sees_affiliate(self):
        seen = []
        orig = match.score
        match.score = lambda p, prof: (seen.append("affiliate" in p), orig(p, prof))[1]
        try:
            match.rank(DOC["platforms"], profile("designer"))
        finally:
            match.score = orig
        self.assertTrue(seen and not any(seen))


class Sanity(unittest.TestCase):
    def top(self, text, n=5):
        return [p for _, _, p, _ in match.rank(DOC["platforms"], profile(text))[:n]]

    def test_designer_gets_design_platforms(self):
        for p in self.top("desainer grafis pemula di Indonesia, cari freelance"):
            self.assertIn("design", p["skills"], p["id"])

    def test_freelance_excludes_company_careers_from_top(self):
        for p in self.top("senior developer, freelance projects", 8):
            self.assertNotEqual(p["type"], "company_careers", p["id"])

    def test_employment_prefers_careers_and_boards(self):
        types = {p["type"] for p in self.top("senior developer, full-time job", 4)}
        self.assertTrue(types <= {"company_careers", "job_board", "staffing"}, types)

    def test_indonesia_bonus(self):
        ids = [p["id"] for p in self.top("designer in Indonesia, freelance", 3)]
        self.assertTrue(any(i in ids for i in ("freelancercoid", "projectscoid")), ids)

    def test_beginner_not_pushed_to_strict_screening(self):
        for p in self.top("pemula desainer, freelance", 5):
            self.assertNotEqual(p["type"], "vetted_network", p["id"])

    def test_deterministic(self):
        prof = profile("writer, freelance")
        self.assertEqual(order(DOC["platforms"], prof), order(DOC["platforms"], prof))


class DataContract(unittest.TestCase):
    def test_meta_and_license(self):
        m = DOC["meta"]
        self.assertEqual(m["license"], "CC BY 4.0")
        self.assertIn("wasian.my.id", m["attribution"])
        self.assertEqual(m["count"], len(DOC["platforms"]))

    def test_required_fields_and_types(self):
        for p in DOC["platforms"]:
            self.assertTrue(p["link"].startswith("https://"), p["id"])
            self.assertIn(p["type"], DOC["meta"]["types"], p["id"])
            for s in p["skills"]:
                self.assertIn(s, DOC["meta"]["skill_tags"], p["id"])
            self.assertIsInstance(p["affiliate"], bool, p["id"])

    def test_cli_output_discloses(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            match.main(["--file", os.path.join(SKILL, "data", "platforms.json"), "--about", "designer freelance"])
        out = buf.getvalue()
        self.assertIn("never used in ranking", out)
        self.assertIn("CC BY 4.0", out)
        self.assertIn("[Affiliate]", out)


if __name__ == "__main__":
    unittest.main()
