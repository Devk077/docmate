# Manual Release Guide

This guide explains how to create releases for DoqToq using completely manual versioning and GitHub's web interface.

## Release Process

### 1. Prepare the Release

1. **Update CHANGELOG.md**:
   ```bash
   # Move items from [Unreleased] to a new version section
   # Example:
   ## [0.1.0] - 2025-08-01
   ### Added
   - Qdrant vector database integration
   - Dual vector database support (ChromaDB/Qdrant)
   - Enhanced configuration management with Pydantic
   ```

2. **Commit your changes**:
   ```bash
   git add CHANGELOG.md
   git commit -m "chore: prepare release v0.1.0"
   git push origin main
   ```

### 2. Create Release on GitHub

1. **Go to GitHub Releases**:
   - Navigate to `https://github.com/shre-db/doqtoq/releases`
   - Click "Create a new release"

2. **Fill in release details**:
   - **Tag version**: `v0.1.0` (will be created on publish)
   - **Release title**: `Release v0.1.0`
   - **Description**: Copy the relevant section from CHANGELOG.md

3. **Publish the release**:
   - Click "Publish release"
   - GitHub will automatically create the tag

### 3. That's it!

- ✅ CI pipeline runs automatically for all pushes to main
- ✅ Manual releases give you full control
- ✅ No complex automation to debug
- ✅ Simple and predictable process

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backwards compatible
- **PATCH** (0.1.1): Bug fixes, backwards compatible

## Example Release Notes Template

```markdown
## What's Changed

### Added
- Qdrant vector database integration
- Dual vector database support (ChromaDB/Qdrant)
- Enhanced configuration management with Pydantic

### Fixed
- Document processing memory optimization
- Vector database connection stability

### Changed
- Improved error handling and logging

## Installation

```bash
git clone https://github.com/shre-db/doqtoq.git
cd doqtoq
./install.sh
```

**Full Changelog**: https://github.com/shre-db/doqtoq/blob/main/CHANGELOG.md
```

## Benefits of This Approach

- **Simple**: No CI/CD complexity for releases
- **Flexible**: Release whenever you want
- **Clear**: Manual changelog updates
- **Fast**: No waiting for automation
- **Reliable**: No automation to break

## Future Migration

When ready for automation:
1. Add release job back to `.github/workflows/ci.yml`
2. Consider semantic-release or similar tools
3. Implement conventional commits if desired
