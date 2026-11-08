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
        # vetted networks may appear (some place people into long-term roles), but goal fit must dominate
        top = self.top("senior developer, full-time job", 8)
        self.assertTrue({p["type"] for p in top} <= {"company_careers", "job_board", "staffing", "vetted_network"})
        self.assertGreaterEqual(sum(p["type"] in ("company_careers", "job_board", "staffing") for p in top), 3)

    def test_indonesia_bonus(self):
        ids = [p["id"] for p in self.top("designer in Indonesia, freelance", 3)]
        self.assertTrue(any(i in ids for i in ("freelancercoid", "projectscoid")), ids)

    def test_beginner_not_pushed_to_strict_screening(self):
        for p in self.top("pemula desainer, freelance", 5):
            self.assertNotEqual(p["type"], "vetted_network", p["id"])

    def test_deterministic(self):
        prof = profile("writer, freelance")
        self.assertEqual(order(DOC["platforms"], prof), order(DOC["platforms"], prof))


class TieBreakAndRegion(unittest.TestCase):
    def ranked(self, text):
        return match.rank(DOC["platforms"], profile(text))

    def test_scores_are_differentiated(self):
        for text in ("designer freelance", "developer full-time", "translator freelance"):
            top = [round(s, 1) for s, *_ in self.ranked(text)[:10]]
            self.assertGreaterEqual(len(set(top)), 5, f"{text}: {top}")

    def test_specialist_beats_generalist_for_same_skill(self):
        by_id = {p["id"]: s for s, _, p, _ in self.ranked("designer freelance")}
        spec = [p["id"] for p in DOC["platforms"] if p["skills"] == ["design"] and p["type"] == "marketplace"]
        gen = [p["id"] for p in DOC["platforms"] if len(p["skills"]) >= 6 and "design" in p["skills"] and p["type"] == "marketplace"]
        if spec and gen:
            self.assertGreater(max(by_id[i] for i in spec), min(by_id[i] for i in gen))

    def test_non_indonesian_gets_no_indonesia_local_boost(self):
        top = [p["id"] for _, _, p, _ in self.ranked("designer from the Philippines, freelance")[:6]]
        self.assertNotIn("freelancercoid", top)
        self.assertNotIn("projectscoid", top)

    def test_regions_from_country_and_text(self):
        self.assertEqual(profile("writer from Nigeria")["region"], "africa")
        self.assertEqual(profile("dev in Brazil")["region"], "latam")
        self.assertEqual(profile("designer in Germany")["region"], "europe")
        self.assertEqual(profile("designer in the Philippines")["region"], "asia")
        self.assertIsNone(profile("designer")["region"])

    def test_region_bonus_never_excludes(self):
        ids = {p["id"] for _, _, p, _ in self.ranked("designer from Nigeria")}
        self.assertEqual(len(ids), len(DOC["platforms"]))


class TextParsing(unittest.TestCase):
    """Free-text detection must not fire inside unrelated words."""

    def test_no_midword_matches(self):
        prof = profile("I want to build leads for tax syntax")
        self.assertNotIn("design", prof["skills"])   # "ui" in build
        self.assertEqual(prof["level"], "mid")        # "lead" is not seniority
        self.assertIn("marketing", match.tags_from_text("run ads and seo"))
        self.assertNotIn("marketing", match.tags_from_text("downloads and leads"))
        self.assertNotIn("finance", match.tags_from_text("syntax"))

    def test_data_entry_is_not_beginner(self):
        prof = profile("data entry job")
        self.assertEqual(prof["skills"], {"va_admin"})
        self.assertEqual(prof["level"], "mid")
        self.assertEqual(profile("entry-level data entry")["level"], "beginner")

    def test_real_terms_still_detected(self):
        self.assertIn("design", profile("desainer grafis")["skills"])
        self.assertIn("design", profile("UI/UX designer")["skills"])
        self.assertIn("writing", profile("saya suka menulis")["skills"])
        self.assertEqual(profile("senior developer")["level"], "senior")
        self.assertEqual(profile("kerja di Indonesia")["country"], "ID")
        self.assertIn("customer_support", profile("customer support agent")["skills"])

    def test_keywords_skip_filler(self):
        kws = profile("developer looking for a full-time remote job")["keywords"]
        for w in ("full", "time", "remote", "looking"):
            self.assertNotIn(w, kws)


class Loading(unittest.TestCase):
    def test_offline_uses_snapshot_without_network(self):
        orig = match.urllib.request.urlopen
        match.urllib.request.urlopen = lambda *a, **k: self.fail("network used")
        try:
            doc, source = match.load(offline=True)
        finally:
            match.urllib.request.urlopen = orig
        self.assertEqual(source, "snapshot")
        self.assertEqual(len(doc["platforms"]), len(DOC["platforms"]))

    def test_check_rejects_bad_data(self):
        for mutate in (lambda p: p.update(link="http://x.example"),
                       lambda p: p.update(type="bogus"),
                       lambda p: p.update(skills="dev")):
            doc = copy.deepcopy(DOC)
            mutate(doc["platforms"][0])
            with self.assertRaises(ValueError):
                match._check(doc)


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

    def test_cli_survives_ascii_only_stdout(self):
        import io, contextlib
        buf = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
        with contextlib.redirect_stdout(buf):
            match.main(["--file", os.path.join(SKILL, "data", "platforms.json"), "--about", "designer", "--top", "30"])


if __name__ == "__main__":
    unittest.main()
