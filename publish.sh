#!/bin/bash
# Publish Savior to PyPI

echo "🛟 Publishing Savior to PyPI..."

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build

# Upload to PyPI (requires PyPI account and API token)
python -m twine upload dist/*

echo "✅ Published! Users can now: pip install savior"