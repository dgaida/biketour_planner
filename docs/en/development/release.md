# Release Workflow

This project uses [Conventional Commits](https://www.conventionalcommits.org/) and [git-cliff](https://git-cliff.org/) for automated changelog generation.

## Commit Conventions

Commits should follow this format:

- `feat: ...` for new features.
- `fix: ...` for bug fixes.
- `docs: ...` for documentation changes.
- `style: ...` for styling changes.
- `refactor: ...` for code refactoring.
- `test: ...` for tests.
- `chore: ...` for maintenance tasks.

## Generating Changelog

The changelog can be manually updated with the following command:

```bash
git-cliff -o CHANGELOG.md
```

## Creating a New Release

1. Bump the version in `pyproject.toml`.
2. Update the changelog: `git-cliff -o CHANGELOG.md`.
3. Commit changes: `git commit -am "chore(release): prepare for vX.Y.Z"`.
4. Create a tag: `git tag vX.Y.Z`.
5. Push: `git push && git push --tags`.
