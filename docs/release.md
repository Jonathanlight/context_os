# Releasing ContextOS

Tagging `vX.Y.Z` on `develop` triggers `.github/workflows/release.yml`,
which builds the wheel + sdist, verifies the package version matches
the tag, publishes to PyPI, and creates a GitHub Release with the
`CHANGELOG.md` excerpt as the body.

The PyPI publish step is the **one** part of the pipeline that needs
manual setup before it works. Pick one of the two paths below per
project.

## Path A — PyPI API token (faster setup)

Use this when you want the release pipeline working in five minutes.
Slightly weaker than OIDC (the token lives in a GitHub Actions
secret), but adequate for solo / small-team projects.

1. Create the project on PyPI by uploading a first release manually
   (or wait — once trusted publishing is configured later, the first
   automated release will create it).
2. On PyPI, **Account settings → API tokens → Add API token**.
   - **Token name**: `context-os-github-actions`.
   - **Scope**: limit to the `context-os` project (after the first
     publish creates it) for blast-radius reasons.
3. Copy the `pypi-…` token string.
4. On GitHub, **Repository → Settings → Secrets and variables →
   Actions → New repository secret**.
   - Name: `PYPI_API_TOKEN`.
   - Value: the token string from step 3.
5. (Optional but recommended) Restrict the `pypi` environment in
   **Settings → Environments → pypi** to require a deployment
   reviewer or branch protection.

The next time a `v*` tag is pushed, the workflow logs
`Publishing via API token (PYPI_API_TOKEN secret)` and uploads via
the token.

## Path B — Trusted publishing (OIDC, recommended long-term)

No token lives anywhere; PyPI verifies the GitHub Actions workflow
identity via OpenID Connect. Stronger because revocation is one
PyPI-side click; downside is the initial setup needs PyPI-side
configuration.

1. On PyPI, **Your projects → context-os → Publishing → Add a new
   publisher** (or for first-time projects: **Account settings →
   Publishing → Add a new pending publisher**).
   - **PyPI Project Name**: `context-os`.
   - **Owner**: `Jonathanlight`.
   - **Repository name**: `context_os`.
   - **Workflow filename**: `release.yml`.
   - **Environment name**: `pypi` (matches `environment: pypi` in
     `release.yml`).
2. Do NOT set `PYPI_API_TOKEN` (or unset it if previously set). The
   action falls through to OIDC when the secret is empty.

The next time a `v*` tag is pushed, the workflow logs
`Publishing via trusted publishing (OIDC)` and exchanges the GitHub
Actions ID token for a short-lived upload token.

## Manual escape hatch

If neither path is available (e.g. you're rolling a hotfix from a
private branch), there's a one-liner that bypasses the workflow:

```bash
# In the repo root, on the commit you want to publish:
python -m pip install --upgrade build twine
python -m build
python -m twine upload dist/* \
  --username __token__ \
  --password "$PYPI_API_TOKEN_LOCAL"
```

`$PYPI_API_TOKEN_LOCAL` is a token you keep in your shell config,
**not** the same secret committed to GitHub Actions. Same scope
rules apply: limit to the `context-os` project.

## Operator checklist when cutting a release

```bash
# 1. Confirm the version in pyproject.toml and __init__.py match
grep -E '^version|^__version__' pyproject.toml src/contextos/__init__.py

# 2. Confirm the CHANGELOG has an entry for the new version
head -20 CHANGELOG.md

# 3. Tag + push
git tag -a vX.Y.Z -m "vX.Y.Z — <one-line>"
git push origin vX.Y.Z

# 4. Watch the workflow
gh run watch
```

If the workflow fails at the `Publish to PyPI` step:

- Read the `Detect publish mode` step's notice line — it tells you
  which path was attempted.
- For Path A: check the `PYPI_API_TOKEN` secret is set and not
  expired.
- For Path B: check the Trusted Publisher entry on PyPI matches
  owner / repo / workflow / environment exactly. The error message
  ``invalid-publisher`` means a claim didn't match.

A failed publish does **not** roll back the tag. The tag stays on
GitHub; rerun the workflow after fixing the setup
(`gh workflow run release.yml --ref vX.Y.Z`).

## VSCode Marketplace

The extension under `extensions/vscode/` ships independently on the
VSCode Marketplace via `.github/workflows/vscode-publish.yml`, also
triggered by `v*` tag pushes. The workflow bumps the extension's
`package.json` to match the tag, builds, and runs `vsce publish` when
the `VSCE_PAT` secret is present (falls through to a build-only run
otherwise).

### One-time setup

1. **Create the Marketplace publisher.** Go to
   <https://aka.ms/vscode-create-publisher> and create one whose ID
   matches `publisher` in `extensions/vscode/package.json`
   (currently `jonathanlight`).
2. **Generate a Personal Access Token.**
   - Sign in to <https://dev.azure.com/> (Microsoft Azure DevOps).
   - **User settings → Personal access tokens → New token**.
   - **Organization**: `All accessible organizations`.
   - **Scope**: select **Marketplace → Manage**.
   - Copy the token (you can't view it later).
3. **Store the PAT on GitHub.**
   - **Repository → Settings → Secrets and variables → Actions →
     New repository secret**.
   - Name: `VSCE_PAT`.
   - Value: the token from step 2.
4. (Optional) **Set up the `vscode` environment** under
   **Settings → Environments → vscode** with a deployment reviewer
   for first-time human approval.

The next `v*` tag push runs the workflow; the
`Detect publish mode` step prints
`Publishing to VSCode Marketplace (VSCE_PAT secret present).` and
the publish step uploads the `.vsix`.

### Manual escape hatch

When the GitHub Actions path isn't available:

```bash
cd extensions/vscode
npm ci
npm run build
npx @vscode/vsce publish --pat "$VSCE_PAT_LOCAL"
```

Same pattern as the PyPI fallback: `$VSCE_PAT_LOCAL` is a token you
keep in your shell config, **distinct** from the CI-side `VSCE_PAT`
to avoid cross-contamination.

### When the publish fails

- `ERROR Personal Access Token verification failed` → the PAT is
  expired or scoped wrong. Regenerate with the Marketplace > Manage
  scope.
- `ERROR The Publisher 'X' does not exist` → the publisher in
  `package.json` does not match the Marketplace publisher you
  created. Edit `package.json` or create the matching publisher.
- `ERROR Already exists at this version` → the marketplace already
  has the same version. Bump `version` in `package.json` (or push
  a new git tag) before re-running.
