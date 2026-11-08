#!/usr/bin/env python3
"""Rank Remote Works platforms for a user profile. Standard library only.

Data: live JSON from https://wasian.my.id/remoteworks/platforms.json
(CC BY 4.0), falling back to the bundled snapshot in ../data/platforms.json.

Examples:
  python3 match.py --about "desainer grafis pemula di Indonesia, cari freelance"
  python3 match.py --skills design,writing --level mid --want freelance --country ID --json

Integrity rule: the `affiliate` flag is NEVER used for scoring. score() only
receives a copy of each platform with that key removed, so it cannot influence
the ranking. tests/test_match.py enforces this.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

DEFAULT_URL = "https://wasian.my.id/remoteworks/platforms.json"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.normpath(os.path.join(HERE, "..", "data", "platforms.json"))

# free text (English + Indonesian) -> skill tag.
# Patterns are matched with a left word boundary (see _rx) so "ui" does not hit "build"
# and "ads" does not hit "leads". Short tokens also carry a trailing \b.
SYNONYMS = {
    "dev": r"developer|programmer|coding|coder|software|web ?dev|backend|frontend|devops|engineer|pemrograman|programming",
    "design": r"design|desain|desainer|graphic|grafis|ui\b|ux\b|logo|ilustrasi|illustrat",
    "writing": r"writer|writing|penulis|menulis|nulis|konten|content|copywrit|blog|editor naskah|proofread",
    "marketing": r"marketing|pemasaran|sosmed|social media|seo\b|iklan|ads\b|growth|community",
    "sales": r"sales|penjualan|business development",
    "data": r"data analy|analis data|data science|analytics|machine learning|bi\b",
    "ai_training": r"annotat|labeling|label data|ai training|ai tutor|rater|penilai ai",
    "translation": r"translat|terjemah|penerjemah|locali[sz]|linguist",
    "transcription": r"transcri|transkrip|caption",
    "va_admin": r"virtual assistant|asisten virtual|va\b|admin|data entry|bookkeep|pembukuan",
    "customer_support": r"customer (service|support|success)|cs\b|helpdesk|help desk|call cent|support (agent|specialist|rep)|layanan pelanggan|dukungan pelanggan",
    "finance": r"finance|keuangan|accounting|akuntan|pajak|tax\b",
    "product": r"product manag|product owner|produk manajer",
    "video_audio": r"video|audio|podcast|animasi|animation|voice|musik|editor video",
    "legal": r"legal|hukum|compliance|paralegal",
    "research": r"research|riset|survey|survei|akademik|academic",
    "education": r"teach|tutor|guru|mengajar|educat|coach|mentor",
}
LEVELS = {
    "beginner": r"pemula|beginner|fresh ?grad|entry[- ]level|junior|baru mulai|belum ada pengalaman",
    "senior": r"senior|expert|ahli|berpengalaman|principal|staff engineer",
}
WANTS = {
    "employment": r"karyawan|full[- ]?time|lamar|employment|employee|kerja tetap|lowongan",
    "microtask": r"micro ?task|receh|sampingan|side income|tugas kecil|survey berbayar|part[- ]?time santai",
    "freelance": r"freelanc|proyek|project|klien|client|lepas",
}
COUNTRY_RX = r"indonesia|indo\b|wni\b|rupiah"


def _rx(pattern):
    """Compile with a left word boundary: matches word starts, not mid-word."""
    return re.compile(r"(?<![a-z0-9])(?:" + pattern + ")")


SYNONYMS_RX = {k: _rx(v) for k, v in SYNONYMS.items()}
LEVELS_RX = {k: _rx(v) for k, v in LEVELS.items()}
WANTS_RX = {k: _rx(v) for k, v in WANTS.items()}
COUNTRY_RE = _rx(COUNTRY_RX)

# words that say nothing about the person's field; excluded from keyword matching
STOPWORDS = set("""
yang untuk dengan cari mau saya kerja bisa ingin dari dan atau pada agar akan juga lagi sudah belum
with that from want looking this have need find help into some about also like would could should
full time part remote work working worker jobs job anywhere level people person someone anything
year years month months more most very much many other than then them they their there where which
""".split())

TYPE_FIT = {
    "freelance":  {"marketplace": 15, "vetted_network": 12, "language_services": 8, "ai_training": 6,
                   "job_board": 5, "microtask": 4, "staffing": 4, "company_careers": 0},
    "employment": {"company_careers": 15, "job_board": 12, "staffing": 12, "vetted_network": 8,
                   "ai_training": 4, "marketplace": 3, "language_services": 3, "microtask": 2},
    "microtask":  {"microtask": 15, "ai_training": 14, "language_services": 12, "marketplace": 4,
                   "job_board": 2, "staffing": 2, "vetted_network": 2, "company_careers": 0},
    "any":        {t: 8 for t in ("marketplace", "vetted_network", "language_services", "ai_training",
                                  "job_board", "microtask", "staffing", "company_careers")},
}
TYPE_NOTE = {
    "company_careers": "company careers page: apply for a job, not a freelance marketplace",
    "vetted_network": "selective screening",
    "job_board": "job board: you apply to employers",
    "staffing": "long-term staffing (employment-style)",
    "microtask": "small paid tasks",
    "ai_training": "AI training / data annotation work",
    "language_services": "translation / transcription work",
    "marketplace": "marketplace: you find clients or gigs",
}

DISCLOSURE = ("Links marked [Affiliate] earn the site owner a commission at no cost to you. "
              "Affiliate status is never used in ranking.")
ATTRIBUTION = "Data: wasian.my.id/remoteworks (CC BY 4.0) https://wasian.my.id/remoteworks"


def load(url=DEFAULT_URL, file=None, timeout=5, offline=False):
    """Return (doc, source) where source is 'live', 'snapshot' or 'file'."""
    if file:
        with open(file, encoding="utf-8") as f:
            return _check(json.load(f)), "file"
    if offline:
        with open(DEFAULT_FILE, encoding="utf-8") as f:
            return _check(json.load(f)), "snapshot"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "remoteworks-matcher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _check(json.loads(r.read().decode("utf-8"))), "live"
    except Exception as e:  # network down, blocked host, bad JSON: use the bundled copy
        print(f"note: live data unavailable ({type(e).__name__}); using bundled snapshot", file=sys.stderr)
        with open(DEFAULT_FILE, encoding="utf-8") as f:
            return _check(json.load(f)), "snapshot"


def _check(doc):
    if not isinstance(doc, dict) or not doc.get("platforms"):
        raise ValueError("platforms.json has no platforms")
    types = set(doc.get("meta", {}).get("types") or TYPE_FIT["any"])
    for p in doc["platforms"]:
        for k in ("id", "name", "type", "link", "skills"):
            if k not in p:
                raise ValueError(f"platform {p.get('id')} missing {k}")
        if not str(p["link"]).startswith("https://"):
            raise ValueError(f"platform {p['id']} has a non-https link")
        if p["type"] not in types:
            raise ValueError(f"platform {p['id']} has unknown type {p['type']!r}")
        if not isinstance(p["skills"], list):
            raise ValueError(f"platform {p['id']} skills is not a list")
    return doc


def tags_from_text(text):
    text = (text or "").lower()
    return {tag for tag, rx in SYNONYMS_RX.items() if rx.search(text)}


def infer(text, table, default):
    text = (text or "").lower()
    for value, rx in table.items():
        if rx.search(text):
            return value
    return default


def score(p, prof):
    """p MUST NOT contain the affiliate flag (see rank())."""
    reasons = []
    req = prof["skills"]
    pts = 0.0
    if req:
        overlap = sorted(req & set(p["skills"]))
        if overlap:
            pts += 60.0 * len(overlap) / len(req)
            reasons.append("skills match: " + ", ".join(overlap))
        elif p["skills"] == ["general"]:
            pts += 15
            reasons.append("generalist board (all fields)")
        text = " ".join([p.get("skills_text", ""), p.get("work_type", ""), p.get("best_fit", "")]).lower()
        hits = [k for k in prof["keywords"] if k in text]
        if hits:
            pts += min(15, 5 * len(hits))
            reasons.append("mentions: " + ", ".join(hits[:3]))
    else:
        pts += 20

    t = p["type"]
    pts += TYPE_FIT[prof["want"]].get(t, 0)
    if TYPE_NOTE.get(t):
        reasons.append(TYPE_NOTE[t])

    lvl = prof["level"]
    if lvl == "beginner":
        adj = {"vetted_network": -10, "microtask": 4, "ai_training": 2, "language_services": 2}.get(t, 0)
        if adj < 0:
            reasons.append("screening is strict, better once you have experience")
    elif lvl == "senior":
        adj = {"vetted_network": 5, "microtask": -5}.get(t, 0)
    else:
        adj = {"vetted_network": 3}.get(t, 0)
    pts += adj

    if prof["country"] == "ID" and p.get("indonesia_focus"):
        pts += 10
        reasons.append("explicitly targets Indonesia")
    return max(0.0, min(100.0, pts)), reasons


def rank(platforms, prof):
    scored = []
    for p in platforms:
        clean = {k: v for k, v in p.items() if k != "affiliate"}  # structural guarantee
        s, why = score(clean, prof)
        scored.append((s, p["name"].lower(), p, why))
    scored.sort(key=lambda x: (-x[0], x[1]))  # tie-break by name only
    return scored


def build_profile(args):
    about = args.about or ""
    skills = set(s.strip() for s in (args.skills or "").split(",") if s.strip()) | tags_from_text(about)
    unknown = skills - set(SYNONYMS) - {"general"}
    if unknown:
        raise SystemExit(f"unknown skill tags: {sorted(unknown)}; valid: {sorted(SYNONYMS)}")
    level = args.level or infer(about, LEVELS_RX, "mid")
    want = args.want or infer(about, WANTS_RX, "any")
    country = (args.country or ("ID" if COUNTRY_RE.search(about.lower()) else "")).upper()
    known = list(SYNONYMS_RX.values()) + list(LEVELS_RX.values()) + list(WANTS_RX.values()) + [COUNTRY_RE]
    kws = []
    for w in re.findall(r"[a-zA-Z]{4,}", about.lower()):
        if w not in STOPWORDS and w not in kws and not any(rx.search(w) for rx in known):
            kws.append(w)
    return {"skills": skills, "level": level, "want": want, "country": country, "keywords": kws[:8]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--about", help="free text description of the person (English or Indonesian)")
    ap.add_argument("--skills", help="comma separated skill tags, e.g. design,writing")
    ap.add_argument("--level", choices=["beginner", "mid", "senior"])
    ap.add_argument("--want", choices=["freelance", "employment", "microtask", "any"])
    ap.add_argument("--country", help="ISO code, e.g. ID")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--file", help="read this JSON file instead of the network")
    ap.add_argument("--offline", action="store_true", help="skip the network, use the bundled snapshot")
    a = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):  # fees contain non-ASCII (e.g. an em dash); avoid crashes on cp1252 consoles
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    doc, source = load(a.url, a.file, offline=a.offline)
    prof = build_profile(a)
    ranked = rank(doc["platforms"], prof)[: a.top]

    items = [{
        "rank": i, "id": p["id"], "name": p["name"], "type": p["type"], "score": round(s, 1),
        "reasons": why, "fee": p.get("fee"), "best_fit": p.get("best_fit"), "link": p["link"],
        "affiliate": bool(p.get("affiliate")),
    } for i, (s, _, p, why) in enumerate(ranked, 1)]

    if a.json:
        print(json.dumps({
            "profile": {**prof, "skills": sorted(prof["skills"])}, "data_source": source,
            "results": items, "disclosure": DISCLOSURE, "attribution": ATTRIBUTION,
            "derived_note": doc.get("meta", {}).get("derived_note"),
        }, indent=2, ensure_ascii=False))
        return 0

    print(f"Profile: skills={sorted(prof['skills']) or 'any'} level={prof['level']} want={prof['want']} country={prof['country'] or '-'}")
    print(f"Data: {source} ({len(doc['platforms'])} platforms)\n")
    for it in items:
        tag = " [Affiliate]" if it["affiliate"] else ""
        print(f"{it['rank']}. {it['name']}{tag}  ({it['type']}, score {it['score']})")
        print(f"   why: {'; '.join(it['reasons']) or 'general fit'}")
        print(f"   fee: {it['fee']}")
        print(f"   link: {it['link']}\n")
    print(DISCLOSURE)
    print(ATTRIBUTION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
