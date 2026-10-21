# Releasing azauthlib

Releases are built once by GitHub Actions. The same wheel and source distribution are published to
PyPI and attached to the GitHub release with a SHA-256 checksum file.

## One-time repository configuration

1. Create a GitHub environment named `pypi`. Add required reviewers when another trusted maintainer
   is available.
2. In the PyPI `azauthlib` project, add a GitHub Trusted Publisher with:
   - owner: `doydl-technologies`
   - repository: `azauthlib`
   - workflow: `publish.yml`
   - environment: `pypi`
3. Protect `main` with a ruleset requiring pull requests, CI, CodeQL, resolved conversations, and
   blocked force pushes and deletion.
4. Restrict GitHub Actions to approved actions and require full-length commit SHA pinning.

Do not configure a long-lived PyPI API token. The publish job requests a short-lived OIDC token.

## Release procedure

1. Confirm the version in `src/azauthlib/__init__.py` is unused on both PyPI and GitHub.
2. Replace `Unreleased` in `CHANGELOG.md` with the release date and prepare release notes under
   `.github/release-notes/`.
3. Run the complete local release checks:

   ```bash
   python -m pip install -e ".[dev]"
   ruff check .
   ruff format --check .
   bandit -c pyproject.toml -r src
   pip-audit --skip-editable
   pytest
   python -m pytest -q -o addopts= .github/desktop/test_helpers.py
   python -m build
   twine check dist/*
   ```

4. Merge the release pull request into `main` only after all required checks pass. Require both
   `CI` and `Desktop package checks` on the exact release commit, including Windows, macOS, and
   Linux desktop checks. A local Windows pass does not replace the native macOS/Linux checks.
   Review the Windows upgrade guidance and include every runtime asset and restored test in the
   commit; do not publish from an uncommitted working tree.
5. Create a draft GitHub release targeting `main` with a tag matching `v` plus the exact package
   version, for example `v2.0.0`. Paste the matching release-notes file. Mark the GitHub release as
   a pre-release only when the package version is itself a pre-release.
6. Publish the GitHub release. The `Publish to PyPI` workflow verifies that the tagged commit is on
   `main`, verifies the tag/version match, builds and smoke-tests the distributions, publishes them
   to PyPI, and attaches them plus `SHA256SUMS.txt` to the GitHub release. Source-quality,
   security, installed-wheel tests, and runtime-asset checks must pass before publication.
7. Verify the GitHub workflow, PyPI metadata, provenance, and a clean-environment installation.

Published PyPI files and release tags are immutable release records. If a release is wrong, publish
a corrected version rather than replacing its files or moving its tag.

The current source version is `004.017.006`, normalized by Python packaging to `4.17.6`.
With the current tag check, use `v004.017.006` for the GitHub tag and `4.17.6` in pip commands.
