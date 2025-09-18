# Publishing Savior to PyPI

## First Time Setup

1. Create a PyPI account at https://pypi.org/account/register/
2. Generate an API token at https://pypi.org/manage/account/token/
3. Save your token securely

## Publishing Steps

1. **Clean previous builds:**
```bash
rm -rf dist/ build/ *.egg-info
```

2. **Build the package:**
```bash
python -m pip install --upgrade build
python -m build
```

3. **Upload to PyPI:**
```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

When prompted, use:
- Username: `__token__`
- Password: Your PyPI API token (including the `pypi-` prefix)

## Test on TestPyPI First (Optional)

1. **Upload to TestPyPI:**
```bash
python -m twine upload --repository testpypi dist/*
```

2. **Test install:**
```bash
pip install -i https://test.pypi.org/simple/ savior-backup
```

## After Publishing

Users can now install with:
```bash
pip install savior-backup
```

## Version Updates

1. Update version in:
   - `setup.py`
   - `pyproject.toml`
   - `savior/__init__.py` (if it exists)

2. Commit changes:
```bash
git add -A
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

3. Follow publishing steps above

## Notes

- Package name is `savior-backup` (since `savior` was taken on PyPI)
- Command remains `savior` after installation
- Make sure README.md images use absolute URLs for PyPI