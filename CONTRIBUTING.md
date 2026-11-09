# Contributing

Run `python3 -m unittest discover -s scripts -p "test_*.py"`, then Homebrew style and audit checks on macOS.

## Repository maintenance

Use a Conventional Commit PR title and a concise changes list in the body.
Completed PR branches are deleted automatically.

Keep GitHub Actions pinned to full commit SHAs with version comments. Check the
actions' upstream releases when maintaining workflows. Renovate is not configured:
application versions and checksums are updated by the release notification workflow.

Publication workflows commit verified generated records directly to main using
GITHUB_TOKEN. Main rejects deletion and force pushes; requiring pull requests for
these updates first requires adapting the publication authentication and workflow.
