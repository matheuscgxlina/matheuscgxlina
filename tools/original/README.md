# MONO / INVADERS — Original Edition

An independent, monochrome contribution arcade for GitHub profiles, maintained by Matheus (matheuscgxlina).

## Design

- Continuous SVG sweep at 220 px/s, configurable from 120–300.
- Projectiles launch as the ship crosses occupied columns; impact timing is calculated from distance.
- Real contribution counts, 53-week calendar, compact particle effects, larger original ship.
- No third-party runtime engine, packages, scripts in SVG, telemetry or personal access token.
- Python standard library; the original local calendar client queries GitHub GraphQL.
- CI validates timelines, counts, empty/dense calendars, speed bounds and external-resource absence before publishing.

## Run

```sh
python3 -m unittest discover -s tools/original -p 'test_*.py' -v
python3 tools/original/render.py --demo --output /tmp/mono.svg
```

For real data, supply GITHUB_TOKEN through the environment and omit --demo. Never commit tokens.

## Origins and attribution

The Original Edition evolves the independent MONO / INVADERS SVG generator created before the REMAKE experiment. It does not import or incorporate the gh-space-shooter engine. The space-shooter calendar concept is inspired by community projects, including gh-space-shooter. The separate historical REMAKE implementation retains its upstream MIT notice in tools/remake/LICENSE. Development was assisted by AI. Do not claim authorship of upstream third-party code.

## Status

Initial portfolio implementation; visual smoothness is subject to browser rendering. The previous REMAKE and its assets remain available for rollback.
