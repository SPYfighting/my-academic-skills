# Sources and licenses

This skill adapts SVG parsing, tracing, text-manifest, and local preview modules from the user's [scientific-illustrator-local](https://github.com/SPYfighting/my-academic-skills/tree/98e4152/scientific-illustrator-local) skill at commit `98e4152`. That skill was released under MIT and itself credits [yrui-cmd/cell-lct](https://github.com/yrui-cmd/cell-lct/tree/4af98d8057f48a944141f9122da7aba83d544d28) for earlier geometry-cache concepts and code. The inherited MIT terms are in [LICENSE](LICENSE).

The PowerPoint DrawingML renderer, application workflow, and figure-specific validation were added here. It is a local tool; it does not include Adobe software, a cloud vectorization service, model weights, or fonts. `VTracer` 1.0.0a4 is an optional upstream package used to build smoother raster-derived paths and is installed separately from [PyPI](https://pypi.org/project/vtracer/1.0.0a4/). Other Python dependencies retain their respective licenses.

The `Baker nc.png` reference and generated panel-a validation files are outside the skill folder. They are not included in the skill package.
