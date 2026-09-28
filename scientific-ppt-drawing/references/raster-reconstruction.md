# Raster reconstruction: selected details only

Default to [semantic drawing](semantic-drawing.md) for scientific schematics. Automated raster tracing is useful for a bounded detail with an irregular silhouette when hand redrawing would lose important shape information. It is not a direct final export route: tracing can turn one human-editable line into hundreds of fragments while still passing a visual similarity score.

Preserve the original and crop only the requested panel for reference. Transcribe labels before any trace so they stay live text. When its background is genuinely flat, `erase-flat-text` can remove verified text boxes from a copy; each manifest run requires an `erase_bbox`, a reviewed baseline position, font, and background color. Inspect the cleaned copy before tracing. Do not erase structures crossing a label box.

```text
<python> <skill_dir>/scripts/figure_cli.py erase-flat-text <original.png> <manifest.json> <clean.png> --reviewed
<python> <skill_dir>/scripts/figure_cli.py trace <detail.png> <empty-candidates-dir> --backend auto --profile auto
```

`trace` writes candidate SVG/PNG files and `trace-review.json`. Scores are heuristics for selecting a visual starting point; they do not test PowerPoint editing structure. Inspect the trace for duplicate contours, tiny regions, ragged lines, and accidental lettering. Redraw continuous lines as single paths; merge, simplify, or discard excess contours; rebuild labels as live text. Only then add the detail to the full figure and run `validate`, `render`, and `inspect`.

The OpenCV fallback can produce polygonal shapes and excess points. VTracer is optional and separately installed; `doctor` reports available backends. Record any region that was simplified and check its scientific meaning against the original. Never hide traced letter outlines behind opaque patches to claim editable text.
