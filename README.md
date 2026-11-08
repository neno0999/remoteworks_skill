# Remote Works Matcher (Claude skill)

A free Claude skill that recommends remote work and freelance platforms for **your** skills, level, country and goal. It reads the curated list at [wasian.my.id/remoteworks](https://wasian.my.id/remoteworks) (134+ platforms) and explains why each match fits.

Skill ini membantu menemukan platform kerja remote yang cocok dengan keahlianmu. Tinggal ceritakan profilmu ke Claude, misalnya: *"Aku desainer grafis pemula di Indonesia, cari klien freelance."*

## Install

**Claude Code**

```bash
git clone https://github.com/neno0999/remoteworks_skill.git
cp -r remoteworks_skill/skills/remoteworks-matcher ~/.claude/skills/
```

**claude.ai / Claude desktop:** run `./scripts/package.sh`, then upload `dist/remoteworks-matcher.zip` in the Skills settings (menu names may change; look for Capabilities, then Skills).

## Use

Just describe yourself to Claude. The skill asks only for what is missing, ranks platforms, and shows a short reason, fee and link for each.

You can also run the matcher directly (Python 3, no dependencies):

```bash
python3 skills/remoteworks-matcher/scripts/match.py --about "designer, beginner, Indonesia, freelance"
python3 skills/remoteworks-matcher/scripts/match.py --skills dev --level senior --want employment --json
python3 skills/remoteworks-matcher/scripts/match.py --about "data entry" --offline   # skip the network
```

## How ranking works

Score 0 to 100, deterministic, ties broken alphabetically:

| Signal | Effect |
|---|---|
| Skill overlap with the platform's `skills` tags | up to +60 |
| Platform type vs your goal (freelance, employment, microtask) | up to +15 |
| Your level (beginner vs strict screening, senior vs vetted networks) | -10 to +5 |
| Explicitly targets Indonesia (when you are there) | +10 |
| Keywords from your description found in the platform text | up to +15 |

Skill tags, type and the Indonesia flag are **derived automatically** from the source text, so treat them as hints, not verified facts. Always check a platform's own terms, fees and payout options.

## Honesty

- Some links are **affiliate links** (marked `[Affiliate]`). The site owner may earn a commission at no cost to you.
- The affiliate flag is **never used for ranking.** This is enforced in code (the scorer never receives that field) and by tests that flip every flag and require an identical ranking. Run `python3 -m unittest discover -s tests -v`.
- The source page also shows paid placements labelled "Ads". Those are not part of this dataset.
- No income promises. No invented data: the skill only uses what is in the dataset.

## Data and updates

- Live: `https://wasian.my.id/remoteworks/platforms.json`
- A bundled snapshot is used offline. A weekly GitHub Action refreshes it from the live URL (and refuses obviously broken data).
- Schema: version 1.0, fields documented in the JSON's `meta` block.

## License

- Code and skill: [MIT](LICENSE)
- Data: [CC BY 4.0](DATA-LICENSE.md). Credit: *Data by wasian.my.id (https://wasian.my.id/remoteworks), CC BY 4.0*

Not affiliated with any platform listed.
