# Setup and PowerPoint control

The CLI requires Python 3.11–3.13 with `requirements.lock`. Create a local virtual environment in this skill directory or use an already verified one. On macOS:

```text
<python3.11-to-3.13> -m venv <skill_dir>/.venv
<skill_dir>/.venv/bin/python -m pip install -r <skill_dir>/requirements.lock
<skill_dir>/.venv/bin/python <skill_dir>/scripts/figure_cli.py doctor
```

For raster reconstruction, install the optional pinned `requirements-vtracer.lock` as well. The OpenCV contour backend remains available without it but can create very large numbers of shapes.

The initial Mac validation used PowerPoint 16.113.2 and Python 3.12.14. The virtual environment is a local runtime and is not part of the portable skill package. `doctor` checks libraries and tracing backends; it does not check whether PowerPoint is installed or render correctly.

For Windows x86-64, the pinned releases of [Pillow](https://pypi.org/project/pillow/12.3.0/), [NumPy](https://pypi.org/project/numpy/2.3.5/), and [OpenCV headless](https://pypi.org/project/opencv-python-headless/4.13.0.92/) list Windows wheels on PyPI. This confirms package availability, not a successful installation or PowerPoint run on Windows. Other Windows architectures have not been checked.

For a new figure, launch PowerPoint, open the generated PPTX and inspect the slide. For an already open user deck, keep that document open, open the generated figure deck, select the figure objects on its slide, copy them, select the requested target slide, paste, position, and save. Confirm the pasted shapes and labels remain individually editable. If the source slide has a white page/background object, avoid covering existing target content unintentionally. Never edit a screenshot instead of the figure objects.

App control depends on the agent environment. In Codex on macOS, select `Microsoft PowerPoint` through the available CUA application interface and use its UI state. A shell `open -a "Microsoft PowerPoint" <file.pptx>` can launch a file when no UI tool is present; use an actual PowerPoint view or an authorized human review for visual validation. On Windows, use the available UI controller's app/window inventory to launch or select PowerPoint, then open the output file through its UI. This Windows route is specified but has not been tested on hardware.

## Compatibility check and fallback

The bundled blank template and renderer use base PresentationML and DrawingML shapes and live text. They do not require Office 2010+ extensions, macros, linked resources, embedded pictures, SmartArt, or visual effects. Microsoft lists `.pptx` as the default PowerPoint XML format from Office PowerPoint 2007 through later desktop releases ([format reference](https://learn.microsoft.com/en-us/office/compatibility/office-file-format-reference)) and marks its [cubic freeform curves](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.cubicbeziercurveto) as available from Office 2007. This is a format-level expectation, not proof that every application version renders this file identically. The older `.ppt` format is outside this skill's editable-output target: Microsoft's [compatibility guidance](https://support.microsoft.com/en-us/powerpoint/compatibility-checker-in-powerpoint) notes that conversions can turn shapes or text into pictures.

For a new PowerPoint version or machine:

1. Run `figure_cli.py compatibility <output.pptx>`. A passing structural result does not replace an application check.
2. Render `<skill_dir>/examples/compatibility-smoke.svg` to a **new temporary PPTX** (for example, `figure_cli.py render <skill_dir>/examples/compatibility-smoke.svg <test.pptx> --width-in 4`) and open it in the target PowerPoint. Confirm its text remains editable and that the curved line exposes Edit Points. Do this before transferring a large figure into an existing deck.
3. If text spacing changes because a font is missing, render a **new** PPTX using `--fallback-font Arial`, inspect the new text layout, and record the substitution. The original PPTX and SVG remain available. If a native shape cannot be edited, stop claiming target-version compatibility and retain the editable SVG and verified PPTX for further adaptation; a picture-only export may be supplied solely as a visual preview.

Only macOS PowerPoint has been checked natively so far. An independent importer can catch some package and layout problems but cannot establish Windows PowerPoint behavior.
