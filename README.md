# README (EN)

# Container Packing Optimizer

A tool that decides how to load mixed product cartons into a shipping container, then renders the plan as side / top / 3D views and a worker instruction sheet.

## Problem

Given an order (quantity per product) and a container type, output a packing plan that:

- Reaches 97–98% length utilization (the sweet spot — fully packed but not so tight that workers can't push cartons in)
- Keeps height differences between and within sections small
- Respects per-product max stacking layers and container inner dimensions
- Never tilts, over-stacks, or changes vertical orientation of any carton

## Products

| Product | Carton L×W×H (cm) | Max layers | Weight |
| --- | --- | --- | --- |
| 5L | 32 × 24 × 22 | 7 | 11.18 kg |
| 2L | 37.5 × 27.5 × 28.5 | 8 | 18.54 kg |
| Icon (艾考) | 42.5 × 28 × 35.5 | 6 | 19.86 kg |

## Containers

| Container | Inner L × W × H (cm) |
| --- | --- |
| 20ft sea / rail | 589 × 235 × 239 |
| 40ft sea | 1203 × 235 × 239 |
| 40ft rail | 1250 × 240 × 250 |

Products keep their vertical height; only the footprint may rotate (normal vs. rotated).

## How it works

The container is divided into **segments** along its length. Each segment holds one product type (`pure`) or stacks 5L on top of two base layers of 2L / Icon (`shared`).

1. **Enumerate ways** — for each product, list valid footprint orientations (cols across width, length per row).
2. **Enumerate segments** — for each way × row count, compute layers / height / length. Drop anything that exceeds container height, length, or layer cap.
3. **Enumerate shared segments** — for orders with 5L, try stacking 5L on top of a 2-layer base of 2L or Icon.
4. **Prune** — keep only the Pareto-best ~30–50 candidates per product (min side gap at each length).
5. **Combine & score** — Cartesian-product the candidates across products and pick the highest-scoring combo.

## Scoring

```
score = w1 · util_score
      − w2 · height_variance / container_height
      − w3 · side_gap_avg / container_width
```

- `util_score`: piecewise — rewards utilization up to 97%, plateaus at 0.98 in the 97–98% sweet spot, penalizes anything above 98% (workers can't squeeze it in)
- `height_variance` = max adjacent inter-segment step + max intra-segment step (the "ugliest stair" on each axis)
- `side_gap_avg`: average leftover width gap (tighter is better)
- Hard cutoff: utilization must be ≥ 95%, otherwise rejected
- Default weights: `w1 = 1.0, w2 = 0.5, w3 = 0.15`

## Output

- **Side view** — length × height cross-section, each layer drawn row by row, tail row dimmed to show "not fully filled"
- **Top view** — length × width footprint per segment
- **3D view** — Plotly interactive box rendering, with the partially-filled top layer rendered at lower opacity
- **Worker guide** — natural-language step-by-step instructions for the loading crew

## Files

- `config.py` — product specs, container specs, colors
- `packing.py` — core algorithm: ways → segments → combos → score
- `visualization.py` — side / top / 3D rendering + worker guide



## Status

- ✅ 3D visualization
- ✅ Worker instruction generator (Chinese, simhei.ttf bundled)
- ✅ Utilization sweet-spot scoring (97–98%)
- ✅ Shared segment (5L on top of 2L / Icon)
- ✅ Top-layer partial-fill rendering
- 🔧 Empirical weight tuning across real orders