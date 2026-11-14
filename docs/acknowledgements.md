# Acknowledgements

The product and visual surface are adapted from [CodeNotch](https://github.com/vinzdg/codenotch), an MIT-licensed macOS project by Vinz. Milestone 5 uses revision `ec1a7e3fc0634f668741cb0357029420bdd4281c` as its fixed reference.

The QML implementation directly adapts the reference's measured geometry, pure-black palette, usage bands, motion timing, provider-ring layout, tooltip silhouette, and interaction model. CodeNotch's Swift/AppKit implementation is not vendored; Omarchy layer-shell integration, provider execution, normalized snapshots, caching, multi-monitor lifecycle, and input regions remain native to this project.

Version 0.12.0 additionally compares against CodeNotch 1.25.0, revision `835550a342871779135b6484d6899161c5222f7c`. Session-state parsing, busy-to-finished/blocked transition semantics, peek durations, the settings orb and placement behavior follow that revision. See [the parity matrix](codenotch-parity.md) for what is implemented and what remains different.

The Claude and OpenAI/Codex marks come from the same Lobe Icons source documented by CodeNotch's Windows port. The Perplexity mark comes from Simple Icons. License details and required notices are in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
