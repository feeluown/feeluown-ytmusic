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
- Store these notes under `.agent_tasks/` (replaces `progress/`).
