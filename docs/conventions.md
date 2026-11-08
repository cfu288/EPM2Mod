# Conventions

## Commits: Conventional Commits

`<type>(<scope>)?: <summary>`. The `.githooks/commit-msg` hook enforces it. Enable the hook once per clone:

```bash
git config core.hooksPath .githooks
```

| Type | Use for |
|---|---|
| `feat` | new tool capability or new patch spec |
| `fix` | bug fix in tools or a patch spec |
| `docs` | docs, camera log entries |
| `test` | tests |
| `refactor`, `chore`, `build`, `ci`, `perf`, `style`, `revert` | as usual |
| `exp` | ad-hoc work in `experiments/` |

Suggested scopes: `oetool`, `build`, `patch/<name>`, `flash`, `camera-log`, `format`, `exp/<slug>`.

Examples: `feat(patch/movie-limit): raise 29-min cap to 9 h`, `docs(camera-log): record movie-limit flash`.

## Where things go

- **`tools/`:** reusable, tested code.
- **`patches/`:** one JSON spec per mod. Every op states the bytes it expects to replace. Add `expected_sha256` and `status` once a build has been camera-tested.
- **`docs/`:** durable knowledge. Facts there must be sourced or reproducible.
- **`experiments/YYYY-MM-DD-slug/`:** ad-hoc scripts and `NOTES.md`. Anything bulky goes in its `out/` subfolder, which is git-ignored. Promote findings into `docs/` or `tools/` once they hold up.
- **`firmware/` and `build/`:** binaries are never committed. `firmware/SHA256SUMS` is.

## Camera-testing rule

Never flash a build that hasn't been recorded in [camera-log.md](camera-log.md) before and after: file, sha256, lamp timings, result. Keep the stock BIN at hand for recovery.
