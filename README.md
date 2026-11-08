# Remote Works Matcher (Claude skill)

A free Claude skill that recommends remote work and freelance platforms for **your** skills, level, goal and region. It reads the curated list at [wasian.my.id/remoteworks](https://wasian.my.id/remoteworks) (134 platforms, mostly global) and explains why each match fits.

Example: *"I'm a beginner graphic designer in the Philippines looking for freelance clients."* Indonesian input is understood too, and Claude replies in the language you write in.

## Install

**Claude Code**

```bash
git clone https://github.com/neno0999/remoteworks_skill.git
cp -r remoteworks_skill/skills/remoteworks-matcher ~/.claude/skills/
```

**claude.ai / Claude desktop:** run `./scripts/package.sh`, then upload `dist/remoteworks-matcher.zip` in the Skills settings (menu names may change; look for Capabilities, then Skills).

## Use

Describe yourself to Claude. It asks only for what is missing, ranks platforms, and shows a short reason, fee and link for each.

You can also run the matcher directly (Python 3, no dependencies):

```bash
python3 skills/remoteworks-matcher/scripts/match.py --about "beginner designer in Nigeria, freelance"
python3 skills/remoteworks-matcher/scripts/match.py --skills dev --level senior --want employment --country BR --json
python3 skills/remoteworks-matcher/scripts/match.py --about "data entry" --offline   # skip the network
```

## How ranking works

Score 0 to 100, deterministic, ties broken alphabetically:

| Signal | Effect |
|---|---|
| Skill overlap with the platform's `skills` tags | up to +60 |
| Platform type vs your goal (freelance, employment, microtask) | up to +15 |
| Your level (beginner vs strict screening, senior vs vetted networks) | -10 to +5 |
| Keywords from your description found in the platform text | up to +15 |
| Regional focus (see below) | +6, or +10 for Indonesia-local platforms when you are in Indonesia |
| Tie-breakers: specialist over generalist, level wording in the platform's own text, worker-side fee | +6 to -1 in total |

The tie-breakers are small on purpose, so they separate near-equal platforms but never override skill or goal fit.

### Regions and "global" use

Most platforms (126 of 134) are global and carry no country restriction. The dataset has **no per-country eligibility data**, so nothing is ever hidden or excluded because of your country. Your country only adds a small bonus to platforms whose own description says they focus on your region (Asia, Africa, Europe, Latin America). The 8 platforms flagged `indonesia_focus` are the Indonesia-local ones (for example Jobstreet, Kalibrr, Glints); they are boosted only for users in Indonesia.

`--country` accepts any ISO code. Known codes (for example PH, NG, BR, DE) also set a region; unknown codes simply give no regional bonus.

Skill tags, type, region and the Indonesia flag are **derived automatically** from the source text, so treat them as hints, not verified facts. Always check a platform's own terms, fees, payout options and whether it accepts workers from your country.

## Honesty

- Some links are **affiliate links** (marked `[Affiliate]`). The site owner may earn a commission at no cost to you.
- The affiliate flag is **never used for ranking.** This is enforced in code (the scorer never receives that field) and by tests that flip every flag and require an identical ranking. Run `python3 -m unittest discover -s tests -v`.
- The source page also shows paid placements labelled "Ads". Those are not part of this dataset.
- No income promises. No invented data: the skill only uses what is in the dataset.

## Data and updates

- Live: `https://wasian.my.id/remoteworks/platforms.json`
- A bundled snapshot is used offline (`--offline` forces it). A weekly GitHub Action fetches the live file, validates it (and refuses broken or shrunken data), then **opens a pull request** on the `data-sync` branch if anything changed. Nothing is pushed to `main` automatically.
- For the Action to open PRs, enable **Settings, Actions, General, Workflow permissions: Read and write permissions** and tick **Allow GitHub Actions to create and approve pull requests**. PRs opened by the Action do not trigger the Tests workflow (a GitHub limitation); the sync job runs the tests itself before opening the PR.
- Schema: version 1.0, fields documented in the JSON's `meta` block.

## License

- Code and skill: [MIT](LICENSE)
- Data: [CC BY 4.0](DATA-LICENSE.md). Credit: *Data by wasian.my.id (https://wasian.my.id/remoteworks), CC BY 4.0*

Not affiliated with any platform listed.
