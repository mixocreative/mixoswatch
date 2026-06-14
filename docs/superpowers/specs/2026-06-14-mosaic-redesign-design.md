# Swatch Mosaic redesign

Date: 2026-06-14
Status: approved, implementing

## Goal

Rework the Swatch Mosaic tool from per-block rectangles into an interactive
SVG of merged colour regions, with a selectable swatch source.

## Requirements

1. **Responsive modal** - no `min-height`; the canvas grows to fill the
   available space so large screens get a larger mosaic.
2. **Drop area === display area** - one container. Empty: dashed prompt.
   After drop: dashed border gone, container holds the mosaic. A **Remove**
   button returns to the empty/upload state for a new image.
3. **Connected-component merge** - cells with the same matched swatch that
   touch on an edge (4-connectivity) merge into one region. Corner-only
   (diagonal) touch stays separate. No special background handling.
4. **Hover** a region -> coloured edge glow in the region's own colour that
   bleeds onto neighbours. Hovered region paints on top.
5. **Click** a region -> opens the swatch detail card **on top of** the still
   open mosaic modal (modal does not close).
6. **Swatch source selector** - match only against the chosen pool:
   - On screen (current grid filter) - default.
   - Any saved palette (by name) - match only from that palette's swatches.
7. Keep: pixel-size slider, region names (with on/off toggle), Lab dE
   matching, PNG download.

## Engine

SVG. One `<path>` per connected region; `d` is the union of the region's cell
rects, so adjacent same-region cells fill seamlessly into the irregular shape
(no outline tracing). `viewBox="0 0 bx by"` auto-scales to the container.

- Hover glow: `filter: drop-shadow()` in the region colour; JS re-appends the
  hovered path to the end of the SVG so its glow draws over neighbours.
- Label: one JP traditional name per region (hex fallback), placed at the
  centre of the region's largest inscribed rectangle (always inside, even for
  concave shapes), font auto-fit with margin, vertical (縦書き) for tall-narrow,
  hidden when it cannot fit. Names on/off toggle.

## Pipeline

image -> downscale work canvas -> per-block average -> nearest swatch in the
selected pool (Lab dE) -> `idx[bx*by]` -> 4-connectivity flood fill ->
`regionId` per cell -> per-region SVG path + label.

`poolFromSource(source)`:
- `screen`: `filtered()` (+ `GS_DATA` greys), full swatch objects.
- palette id: each `{C,M,Y,K,hex}` resolved to its full twin via
  `DEDUP_BY_KEY.get(_swKey(s))` for names/detail; hex used for matching; falls
  back to the minimal swatch when no twin exists (click guarded to full only).

## Conflict resolution

- **Escape**: the window-level mosaic Escape bails when the detail overlay is
  open, so Escape closes only the detail; the mosaic stays.
- **z-index**: detail overlay 1300 > mosaic 1200.
- **Backdrop clicks**: detail is on top; its backdrop closes only the detail.
- **Focus traps**: detail and mosaic are separate DOM siblings; focus lives in
  the detail while open, so its trap handles Tab; the mosaic trap does not fire.
- **Region click** no longer closes the modal (was close-then-open).

## Removed

Background detection + its toggle, the greedy rectangle merge, the single
background-piece path, the original-image preview pane.
