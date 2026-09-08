# Raster reconstruction and recovery

## Separate text first

Record exact wording, per-line baselines, size, family, weight, color, alignment, and rotation. Check Greek letters, hyphens, and superscripts/subscripts against the source. Split multiline labels and script positions into separate text runs. OCR can assist, but a detected bounding-box top is not a text baseline.

Clean only reviewed text regions. For a flat background:

```text
<python> -X utf8 <cli> erase-text --source-image <original.png> --text-manifest <text.json> --output <text-cleaned.png> --method flat --confirm-background-boxes
```

For a background that varies vertically but is uniform along each row, add `"background_sample_x": [5, 6]` to each applicable text run. These must be reviewed background columns for that image. Use `--method row-sample --confirm-background-boxes`; the script samples the original image on the same row. Sample columns must not intersect any text-erasure box or cross an antialiased edge, cell, arrow, or other structure. Do not reuse the example coordinates blindly.

If neither background model applies, use an authorized image-editing tool to remove only the lettering from a copy. Where text overlaps a structure that cannot be recovered reliably, mark the uncertainty instead of deleting the structure. `cleanup_audit` checks pixels outside text boxes; it cannot certify structures inside them.

## Trace and preserve color

| Profile | Intended starting point | Behavior |
|---|---|---|
| auto | Initial comparison for simple diagrams | Compare balanced and fine candidates |
| balanced | Large shapes and few colors | 16 colors; stronger simplification |
| fine | More small structures | 32 colors; weaker simplification |
| faithful | Detailed low-resolution schematics | VTracer 1.x; 4x Lanczos; 128 colors; cutout/spline; more control points |

The faithful profile uses filter-speckle=4, color-precision=8, gradient-step=4, simplify=0.6, and optimize=0, then returns the SVG to the original dimensions. The resampled image is limited to 32 megapixels. Interpolation adds no original information; more colors and anchors are not automatically better. Inspect local features before selecting a result. Repair specific vectors in a new job if needed rather than flattening similar colors globally.

Keep artwork and labels in the original image coordinate system. After enlarged tracing, scale only the tracing group back down; merged text retains the original baselines and sizes. Write SVG with the standard default namespace, because some renderers reject an `ns0:`-prefixed root.

## Native playback and recovery

Review candidates before long native playback. Windows maintains one COM connection; both systems share batch scheduling. The renderer redraws before export instead of after every batch. Progress is written approximately every ten seconds, with status and saved checkpoints in the job directory.

Use the saved document's full path, not the shared filename `figure.ai`, to identify a job. Windows path comparison ignores case; macOS preserves case for case-sensitive volumes. Source SVG, cache, and batch order are verified by hashes; changed input requires a new job.

Organize live text when creating objects rather than moving items by indexes from a changing collection. Supplemental geometry must use the same viewBox and artboard transform. If the user has edited native objects manually, review whether the original job can still be resumed: batch-count checks do not prove that the edited appearance matches the source.

## Troubleshooting

| Symptom | Action |
|---|---|
| Illustrator connection fails | Check that the application is open in the same user session; use PowerShell 5.1 for the Windows bridge |
| Multiple versions are running | Select Windows `--prog-id Illustrator.Application.N`, or macOS `--app-path` with the exact running `.app` |
| macOS denies automation | The user grants the terminal/agent permission under Privacy & Security > Automation; scripts do not change system permissions |
| Missing font | Identify the intended font or agree an acceptable substitute, then update the SVG/manifest in a new job |
| Pale nuclei disappear or the background flattens | Compare higher-color candidates and inspect local regions; apply white-background changes only to identified background objects |
| A small closed cubic loop is rejected | This parser supports a single closed cubic by splitting it exactly; use the updated skill and prepare a new job |
| No clear placement exists | Use a blank artboard/document, or allow overlap only when already authorized |
| An Adobe dialog blocks playback | Inspect the dialog and confirm the previous operation is idle before starting another drawing |
| Success log but incorrect image | Inspect the real PNG, font faces, and object hierarchy; execution success is not visual acceptance |

Record source validation, simulated DOM checks, native application checks, visual review, and user acceptance separately. Mark each only after that check actually occurred.
