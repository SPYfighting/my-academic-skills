# Input and acceptance specification

## Supported SVG subset

Supported elements: path, rect including rounded corners, circle, ellipse, line, polygon, polyline, nested groups, and independent text. fontTools converts quadratic curves and arcs into cubic anchors and handles. Solid fills/strokes, holes, basic text styles, rotation, and similarity transforms are supported.

Unsupported input includes image, script, external resources, DOCTYPE, CSS classes/style elements, use, marker, clipPath, mask, filter, gradient, pattern, tspan, textPath, and nested SVG viewports. Group opacity, nonuniform scaling of text/strokes, and different fill/stroke opacity are also rejected. Text with `fill="none"` is rejected to avoid default black lettering. Expand unsupported effects explicitly and verify the appearance; do not silently discard them.

Lengths are numbers or px. Convert mm, pt, percent, and em explicitly. A diagram's display size does not imply an experimental scale. Statistical plots should use original vector exports and data; tracing and color quantization do not recover numeric measurements.

## Text manifest

`x,y` specify the text anchor and **baseline**, not a bounding-box corner. The chosen font must exist on the target machine. Use separate runs for multiline text and superscripts/subscripts. Keep the source wording in its original language.

```json
{
  "canvas": [200, 100],
  "runs": [
    {
      "id": "label_1",
      "text": "Input",
      "x": 20,
      "y": 25,
      "font_family": "Arial",
      "font_size": 14,
      "font_weight": "normal",
      "font_style": "normal",
      "fill": "#000000",
      "anchor": "start",
      "rotation": 0,
      "opacity": 1,
      "erase_bbox": [18, 10, 60, 29],
      "background": "#ffffff",
      "reviewed": true
    }
  ]
}
```

An optional top-level `source_sha256` must contain the actual source-image hash. Canvas dimensions must match exactly. `reviewed: true` records a real comparison with the original, not a value added merely to bypass validation. Record estimated fonts and sizes in the task audit.

Text defaults to the top of the artwork. Use `insert_before` with a validated root-level SVG object ID for special occlusion order. Do not insert absolute-coordinate labels inside a transformed group. For same-row background sampling, add `background_sample_x` as described in the workflow.

## Local inspection regions

```json
{"regions":[{"name":"critical_arrow","bbox":[75,35,150,75],"max_mae":0.08}]}
```

The error is mean absolute RGB difference normalized to 0-1. Global, foreground, edge, and local metrics assist candidate selection; all tasks still require visual review.

## Limits and outputs

Raster ranking: 8 megapixels. SVG: 30 MB, 100,000 XML nodes, 50,000 drawing objects, and 1,000,000 anchors. Exceeding a limit stops processing rather than silently downsampling or dropping objects. Complex microscopy photographs are generally unsuitable for this all-vector pipeline.

Prepared jobs contain `figure_master.svg`, `geometry-cache.json`, `job.json`, and, for tracing, `qa.json`, `candidate_comparison.csv`, and candidate PNGs. Actual Illustrator playback creates `figure.ai`, `figure.png`, and `playback.json`. CSV uses UTF-8 with BOM for Excel. Keep task artifacts outside the published skill directory.
