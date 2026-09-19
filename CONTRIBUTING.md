# Contributing

The project is being built in approval-gated milestones. Keep pull requests limited to the active milestone and avoid speculative provider or UI work.

Before submitting a change:

```sh
make check
```

Provider changes must include normalized synthetic fixtures and failure tests. Never commit real account output, credentials, tokens, cookies, home-directory paths, or unredacted errors.

Use two spaces for QML and JSON indentation and four spaces for Python. Runtime dependencies require an architecture discussion before introduction.
