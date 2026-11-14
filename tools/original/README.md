# MONO / INVADERS

An independent, monochrome contribution arcade for GitHub profiles, maintained by Matheus (matheuscgxlina).

## Design

- Continuous SVG sweep at 145 px/s, configurable from 120–170.
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

The MONO / INVADERS evolves the independent MONO / INVADERS SVG generator created before the REMAKE experiment. It does not import or incorporate the gh-space-shooter engine. The space-shooter calendar concept is inspired by community projects, including gh-space-shooter. The historical REMAKE experiment is retired; its upstream MIT notice remains in tools/remake/LICENSE for attribution. Development was assisted by AI. Do not claim authorship of upstream third-party code.

## Status

v1.6 refinement: persistent contribution colors, pooled projectiles, clipping-based enemy destruction, rolling score digits, month alignment and a strict 100 KB SVG budget. CI tests sparse and dense calendars. Pull requests validate read-only; scheduled publishing updates the generated asset only. The animated SVG uses SMIL directly without a media-query override that replaces the arcade with a static image. Visual smoothness remains subject to browser rendering. Retired renderers and generated images are removed from the working tree; earlier versions remain in Git history.
