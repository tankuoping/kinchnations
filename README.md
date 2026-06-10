# Kinch Nation

Country-level [KinchRanks](https://www.speedsolving.com/threads/kinchranks-a-new-rating-system.54508/), rebuilt from the WCA results export twice daily. Replacement for the no-longer-updating wca.cuber.pro/kinch/countries.

- **Site**: static `index.html`, computes all kinch scores client-side from `data/kinch.json`
- **Data**: `scripts/build_kinch.py` downloads the [WCA TSV export](https://www.worldcubeassociation.org/export/results), extracts national bests per event/gender, writes compact JSON (~hundreds of KB)
- **Schedule**: GitHub Actions cron at 23:00 and 11:00 UTC = **7:00 am and 7:00 pm SGT**

## Setup

1. Push this repo to GitHub
2. Repo → Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save
3. Actions tab → "Update Kinch data" → **Run workflow** once (populates real data, ~2-3 min)
4. Import repo into Vercel (framework preset: Other, no build command, output dir: `./`)

Every data commit by the bot triggers a Vercel redeploy automatically.

## Scoring

Per event: 100 × (best NR in selected region ÷ this country's NR).
- Average-only: 3x3, 2x2, 4x4–7x7, OH, Clock, Megaminx, Pyraminx, Skewb, Square-1
- Better of single/mean: 3BLD, FMC
- Single-only: 4BLD, 5BLD
- Multi-blind: points + fraction of hour remaining, ratio vs best

Overall = plain average of all 17 event scores. Region and gender filters re-score against that subset's best, matching the original site's behaviour.

Unofficial — not affiliated with the WCA.
