## Fork Status

This repository is maintained locally as a `stream-curator` fork of:

- Upstream: `https://github.com/BAIGUANGMEI/zhihu-cli`
- Upstream branch: `main`

Current local git remote layout:

- `origin`: currently still points to the upstream repository
- `upstream`: explicitly points to the upstream repository

When publishing a personal or organization fork, change `origin` to your fork URL and keep `upstream` pointing at the original project.

## Fork Purpose

This fork exists to support `stream-curator` integration and release bundling.

The local working tree currently contains stream-curator-driven changes in these areas:

- login flow updates, including QR/browser-assisted session handling
- Zhihu content fetch behavior for feed, hot, answers, articles, and hydrate paths
- article comment support and related client methods
- output/rendering adjustments used by `stream-curator`
- CLI/test adjustments for reader and collector workflows

## Publishing Notes

Before publishing this fork:

1. Commit the current working tree into one or more reviewable commits.
2. Preserve the upstream `LICENSE`.
3. Keep fork-only behavior documented here or in the README.
4. If changes are generally useful upstream, submit them separately as focused pull requests.
