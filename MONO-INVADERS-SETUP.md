# MONO / INVADERS — setup

1. Upload the contents of this package to `matheuscgxlina/matheuscgxlina` on `main`. Keep all directory paths, including `.github/workflows/mono-invaders.yml`.
2. Open Actions → MONO / INVADERS → Run workflow → main → Run workflow.
3. Check the workflow result. If successful, `assets/beyond/invaders.svg` is replaced with a real animated calendar and committed by `github-actions[bot]`.

The packaged SVG is a clearly labeled waiting screen, not invented contribution data. The workflow runs daily at 03:17 UTC (00:17 Brasília standard time) or manually. Scheduled workflows can be delayed, and GitHub may disable inactive public-repository schedules. No GitHub Pages, PAT, or third-party image service is necessary. The built-in workflow token is used for the GitHub GraphQL query and for writing the single generated SVG. If the token lacks API access or the repository prohibits direct pushes to main, the run fails without replacing the last committed asset. Review the workflow log before changing permissions; do not grant broad token permissions just to troubleshoot.

The calendar includes dates, weekday, contribution levels and counts that the GitHub API returns for the profile; private activity may be represented as aggregate counts depending on GitHub visibility and token access. No repository names, commit messages, source files or credentials are embedded. To avoid sharing private activity counts, review the profile's contribution visibility settings before enabling the workflow. The graphic is a separate README image, not a replacement for GitHub's native contribution chart.

Local checks: `cd tools && python -m unittest -v`. To generate an explicitly labeled demo locally: `python tools/generate_invaders.py --demo --output demo.svg` from the repository root. Demo data must never be published as actual activity.
