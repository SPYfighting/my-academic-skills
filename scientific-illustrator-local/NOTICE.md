# Sources and licenses

This skill adapts and restructures public MIT-licensed material from [yrui-cmd/cell-lct](https://github.com/yrui-cmd/cell-lct/tree/4af98d8057f48a944141f9122da7aba83d544d28). The reviewed upstream commit was `4af98d8057f48a944141f9122da7aba83d544d28`, dated `2026-09-06T16:20:16Z`.

Adapted concepts and implementation include SVG-to-cubic geometry, Windows COM/JSX invocation, native paths and text, geometry caches, and resumable batches. The Python cache, playback scheduling, and JSX execution were reworked for local engines and stricter input handling. Upstream tests do not establish this implementation's native compatibility.

This package contains no Xiaomiao server, proprietary algorithms or weights, API key, payment flow, `cell_no_ai` service, AI-origin-mark removal service, Adobe application, model, or font files. It does not bypass service authentication.

[VTracer 1.0.0-alpha.4](https://github.com/visioncortex/vtracer/releases/tag/1.0.0-alpha.4) is an optional, separately installed dependency under its own license. Its installer downloads only a pinned official release asset and verifies SHA256. Python dependencies retain their respective licenses.

Preserve the upstream copyright and MIT terms in [LICENSE](LICENSE). English documentation and the repository self-check were added for distribution; runtime compatibility remains limited to the evidence described in the skill.
