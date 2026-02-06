# Project Best Practices

## Versioning & Release
- Keep `pyproject.toml` `project.version` and `fuo_ytmusic/__init__.py` `__version__` in sync.
- Update the `README.md` changelog with date and highlights before tagging.
- Use commit message: `chore: bump version to X.Y.Z`.
- Tag releases as `vX.Y.Z` and push only the newly created tag (avoid `--tags`).

## Authentication & Profiles (YouTube Music)
- Headerfile authentication is independent from browser sessions; switching accounts
  in the browser does not update the plugin state.
- When testing multi-profile behavior, ensure the active profile is selected via
  API or by re-exporting the headerfile from the browser.
- Prefer explicit profile selection in code paths that require user-specific data
  (e.g., playlists), to avoid accidental cross-account reads.

## Manual Tests
- Keep `manual_tests/` scripts concise and focused on user workflows.
- Avoid leaving verbose debug output in manual tests after verification.
- Manual tests should not hardcode proxies; let users configure networking explicitly.

## Logging & Error Handling
- Provide clear, user-actionable errors for auth failures (e.g., cookie expired).
- Avoid masking network/proxy issues as auth errors when possible.

## Localization (Language Selection)
- Avoid hard-coding `ytmusicapi` language; pick a supported value dynamically.
- Use `LANGUAGE` config for overrides, and fall back to app/system locale when unset.
- Keep the mapping logic in a shared helper module and cover it with unit tests.

## Workflow
- Keep a lightweight `todo` list for the current task:
  - Update it before/after each meaningful step.
  - Mark items done as soon as they are completed.
- Keep a short `proposal` note for design changes:
  - Capture the intended approach, tradeoffs, and assumptions.
  - Use it to confirm alignment before coding.

## PR Description
- Avoid inline `gh pr create --body "..."` for markdown with backticks/newlines.
- Prefer `--body-file` with a temporary markdown file for both create/edit.
- If using `gh api` to patch PR body, pass a JSON file via `--input`.
- Verify final body with `gh api repos/<owner>/<repo>/pulls/<num> --jq '.body'`.
- Keep structure stable: `## Summary` and `## Testing`.

## Code Style
- Use `ruff` for linting and formatting.
- Lint with `ruff check .` (or `uv run ruff check .`).
- Format with `ruff format .` (or `uv run ruff format .`).
- Store these notes under `.agent_tasks/` (replaces `progress/`).
