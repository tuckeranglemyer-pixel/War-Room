---
name: war-room-vercel-deploy
description: >-
  Deploys the War Room frontend to Vercel production when code is pushed to
  main on GitHub via GitHub Actions. Use when the user asks about Vercel
  deploys, CI/CD, automatic deployment on push, GitHub Actions, or debugging
  frontend production builds.
---

# War Room — Vercel deploy on GitHub push

## What actually runs on push

Cursor skills do **not** execute on GitHub. Production deploys are handled by **GitHub Actions**: `.github/workflows/deploy-frontend.yml` runs on every push to `main` that touches `frontend/**` or that workflow file. Manual re-run: Actions tab → workflow → **Run workflow**.

## Required GitHub secrets

Repository **Settings → Secrets and variables → Actions** must define:

| Secret | Purpose |
|--------|---------|
| `VERCEL_TOKEN` | Vercel → Account Settings → Tokens |
| `VERCEL_ORG_ID` | Vercel project → Settings → General (team/org id) |
| `VERCEL_PROJECT_ID` | Same page — Project ID |

Without all three, the job fails at the deploy step.

## Agent guidance

- After frontend changes merged to `main`, production updates automatically once secrets are set; no need to run `npx vercel --prod` locally unless testing deploy outside CI.
- If the user reports deploy failures, check the latest workflow run log and verify the three secrets match the Vercel project linked to `frontend`.
- Optional: connect the same repo in the Vercel dashboard for preview deployments on PRs; this workflow is specifically **production** on `main`.
