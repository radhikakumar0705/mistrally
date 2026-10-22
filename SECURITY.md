# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's
[private vulnerability reporting](https://github.com/radhikakumar0705/sockrat/security/advisories/new)
rather than opening a public issue. Include steps to reproduce and the affected version or commit.

## How the project stays secure

| Practice | Where |
|---|---|
| Dependency updates | Dependabot opens weekly PRs for Python, npm, Docker base images and GitHub Actions |
| Static analysis | CodeQL (security-and-quality queries) on every push and weekly |
| Image scanning | Trivy scans every image in CI; a fixable HIGH or CRITICAL vulnerability fails the build |
| Software bill of materials | An SPDX SBOM is published for each image with every CI run |
| Secret scanning | gitleaks runs as a pre-commit hook; the full history has been scanned clean |
| Hardened containers | Non-root users, read-only root filesystems, dropped capabilities, OS security updates applied at build time |

The application's own security design (authentication, token rotation, CSRF, data isolation and the code
sandbox) is described in [docs/design.md](docs/design.md#7-security).
