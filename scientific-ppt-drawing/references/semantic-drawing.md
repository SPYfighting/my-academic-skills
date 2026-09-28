# Semantic drawing in PowerPoint

Draw as a skilled person would construct the figure, not as a pixel converter would dissect an image. Before writing SVG, list the visual objects and decide how each should be edited later. Keep this list short enough that the important parts can be located in PowerPoint's Selection Pane.

## Object mapping

- A continuous connector, contour, strand, helix side, trace, or ribbon is one SVG `<path>` containing all of its Bézier segments. If it must cross behind another object, it may be split at that occlusion.
- A device is a set of functional parts: housing, tray, screen, arm, tubing, stand, or column. Use separate shapes where a human would recolor, move, or replace a part.
- A repeated same-style grid, such as microplate wells or chart ticks, may be one compound path with multiple subpaths. Do not create one tiny PowerPoint object per mark unless each mark carries independent scientific meaning.
- Text is live `<text>`, one label or line per object. Rebuild arrowheads as filled native shapes. Preserve paint order for intentional overlaps.
- A complex protein cartoon may have several continuous colored strands. Favor a recognizable topology and honest simplification over thousands of irregular trace fragments.

Use simple paths and basic shapes first. Reuse repeated geometry with consistent spacing, line width, and color. Inspect the generated PPTX object count before evaluating pixel similarity. If an instrument icon has hundreds of objects, redesign it around its functional parts. If a smooth line consists of many short objects, join the line into a single path. Add detail when it carries scientific identity; the target is a well constructed editable figure, not the fewest possible objects.

In the Baker seven-stage validation schematic, the revised manual redraw used 216 native objects, including 33 text objects; the earlier pixel trace used 1,462. The simpler 138-object version lost identifying instrument detail and was rejected. Treat these comparisons as practical warning signs, not universal shape limits. When transferring artwork into an existing deck, use the slide's white background instead of a full-slide white rectangle that would cover existing content.

For a reference image, compare three things separately: scientific meaning, visible composition, and editing structure. All labels and meaningful components should be present; deviations due to simplification should be reported. Rendered similarity alone cannot justify fragmented objects. Select representative lines, icons, and text in PowerPoint to verify the structure.
