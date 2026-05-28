#!/usr/bin/env bash
# Manual PyPI publish — the escape hatch when the GitHub Actions
# release workflow can't run (no token, no trusted publishing, or
# you're cutting a hotfix from a private branch).
#
# Usage:
#   PYPI_API_TOKEN_LOCAL=pypi-<token> ./scripts/publish-to-pypi.sh
#
# Reads the token from PYPI_API_TOKEN_LOCAL specifically to avoid
# accidentally re-using a CI-side secret name in a local shell.

set -euo pipefail

if [ -z "${PYPI_API_TOKEN_LOCAL:-}" ]; then
  echo "PYPI_API_TOKEN_LOCAL is not set; aborting." >&2
  echo "" >&2
  echo "Create a PyPI token scoped to the context-os project at:" >&2
  echo "  https://pypi.org/manage/account/token/" >&2
  echo "Then export it as PYPI_API_TOKEN_LOCAL in your shell." >&2
  exit 1
fi

# Reset dist/ so we never publish a stale wheel by accident.
rm -rf dist/
python -m pip install --upgrade build twine >/dev/null

echo "Building wheel + sdist…"
python -m build

echo ""
echo "Verifying the package version matches the latest git tag…"
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
TAG_VERSION="${LATEST_TAG#v}"
PKG_VERSION=$(python -c "import contextos; print(contextos.__version__)")
if [ -n "$LATEST_TAG" ] && [ "$TAG_VERSION" != "$PKG_VERSION" ]; then
  echo "Warning: latest tag '$LATEST_TAG' ($TAG_VERSION) does not match"
  echo "package version $PKG_VERSION. Press Enter to publish anyway, Ctrl-C to abort."
  read -r
fi

echo ""
echo "Uploading $(ls dist/*.whl 2>/dev/null) and $(ls dist/*.tar.gz 2>/dev/null) …"
python -m twine upload dist/* \
  --username __token__ \
  --password "$PYPI_API_TOKEN_LOCAL"

echo ""
echo "Done. Verify at https://pypi.org/project/context-os/"
