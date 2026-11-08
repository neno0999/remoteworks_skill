---
name: remoteworks-matcher
description: Find remote work and freelance platforms that fit a person's skills, level, country and goal, using the curated Remote Works dataset (134+ platforms, wasian.my.id/remoteworks). Use when someone asks where to find remote jobs, freelance clients, micro tasks, AI training or translation work, "platform apa yang cocok buat saya", or wants to compare Upwork, Fiverr, job boards and similar platforms for their own profile.
---

# Remote Works Matcher

Recommend platforms from the public Remote Works dataset and explain why each one fits.
Reply in the language the user writes in (Bahasa Indonesia or English).

## 1. Get the profile (ask only what is missing, max 4 questions)

- What do they do or want to do? (skills, tools)
- Level: beginner, mid or senior
- Goal: freelance projects, a regular job, small side tasks, or open to anything
- Country (Indonesia gets extra local options)

If the user already said enough, skip straight to step 2. Do not interrogate.

## 2. Run the matcher

Run the script by its full path. `<skill_dir>` is the folder that contains this SKILL.md (do not rely on the current directory, it is usually not the skill folder):

```bash
python3 "<skill_dir>/scripts/match.py" --about "<the user's own words>" --top 8
# or explicit:
python3 "<skill_dir>/scripts/match.py" --skills design,writing --level beginner --want freelance --country ID --top 8
```

- Skill tags: dev, design, writing, marketing, sales, data, ai_training, translation, transcription, va_admin, customer_support, finance, product, video_audio, legal, research, education
- `--want`: freelance | employment | microtask | any
- It reads the live data from https://wasian.my.id/remoteworks/platforms.json (5 second timeout) and falls back to the bundled snapshot in `data/platforms.json` when offline or when the live data fails validation. It prints which one it used. Add `--offline` to skip the network entirely (use this when you know there is no internet).
- Check the printed `Profile:` line. Skill, level and goal are guessed from free text and can be wrong; if they look off, rerun with explicit `--skills/--level/--want`.
- Add `--json` if you want structured output to reformat.

If you cannot run code, fetch the JSON (or read `data/platforms.json`) and apply the same rubric by hand: skill overlap first, then platform type vs goal, then level, then Indonesia focus.

## 3. Present the result

Scores are coarse and many platforms tie (ties are broken alphabetically, not by quality). Do not present the order as a precise ranking. Choose among tied platforms using `best_fit`, `fee` and the reasons, and say when several are equally good fits.

For the top 5 (plus up to 3 "also worth a look"):

- Name, type, and the concrete reason it fits this person
- Fee in plain words, from the data's `fee` field
- The link
- Mark every platform with `affiliate: true` as **[Affiliate]**
- One honest caveat when relevant (strict screening for beginners, company careers pages are jobs not gigs, microtasks pay little)

Then end with these two lines, always:

> Links marked [Affiliate] earn the site owner a commission at no cost to you. Affiliate status is never used in ranking.
> Data: wasian.my.id/remoteworks (CC BY 4.0) https://wasian.my.id/remoteworks

## Hard rules

1. **Never rank, filter or pick by affiliate status.** It is a label only. Do not nudge users toward an affiliate platform, and do not drop a good non-affiliate one to make room.
2. **Use only what is in the data.** Do not invent platforms, fees, requirements or acceptance rates. If something is not in the data, say you do not know and suggest checking the platform.
3. **Derived fields are hints.** `type`, `skills`, `indonesia_focus` and `vetted` are derived automatically (see `meta.derived_note`). Do not present them as verified facts.
4. **No income promises.** Never guarantee earnings, approval or that a platform is legit for the user's situation. Remind them to check terms, fees and payout options (including payment methods available in their country) before signing up.
5. **Stay safe.** Legit platforms do not ask applicants to pay to get work. Say so if the user mentions it.
6. **Attribution is required** (CC BY 4.0). Keep the data line from step 3.
