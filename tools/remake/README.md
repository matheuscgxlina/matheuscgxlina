# MONO / INVADERS — REMAKE

Based on [gh-space-shooter](https://github.com/czl9707/gh-space-shooter) by Zane Chen, MIT licensed. Upstream revision: `b24c9792454d1a2e0139ccf72840424e1f83c3f2`. See LICENSE.

The upstream movement, shooting, collisions, column strategy, particles and simulation clock are retained. The local wrapper provides monochrome colors, title, footer, grid, month labels, a 53-week calendar adapter and a bounded frame budget. Upstream computes a frame delay of 2000/FPS milliseconds; configured FPS 80 yields 25 ms frames (40 fps playback) with the same simulation-speed ratio. The original engine is checked out at a fixed commit during CI, not fetched dynamically at runtime. The repository's existing calendar query uses only the temporary GitHub token. Output is animated WebP.
