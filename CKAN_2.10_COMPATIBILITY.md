# CKAN 2.10 Compatibility Guide

## Overview

This document outlines the changes made to ensure `ckanext-schemingdcat` is fully compatible with CKAN 2.10.x. The extension now supports **CKAN 2.9+ and CKAN 2.10+**, with specific improvements for CKAN 2.10 compatibility.

## Version Requirements

- **CKAN**: 2.9.0 or later (including CKAN 2.10.x)
- **Python**: 3.7 or later (CKAN 2.10 requires Python 3.7+)

## Changes Made for CKAN 2.10 Compatibility

### 1. Python Version Requirements

**Issue**: No explicit Python version requirement was set in `setup.py`.

**Solution**: Added `python_requires='>=3.7'` to `setup.py` to align with CKAN 2.10 requirements.

```python
setup(
    ...
    python_requires='>=3.7',
    ...
)
```

### 2. Deprecated Import: `ckan.lib.base`

**Issue**: The extension was using `import ckan.lib.base as base` and calling `base.abort()` in blueprint.py.

**Solution**: Replaced with Flask's native `abort` function.

**Before**:
```python
import ckan.lib.base as base
...
return base.abort(404, _('Dataset not found'))
```

**After**:
```python
from flask import abort
...
return abort(404, _('Dataset not found'))
```

**Files modified**:
- `ckanext/schemingdcat/blueprint.py`

### 3. Deprecated Import: `ckan.common`

**Issue**: Multiple files were importing from `ckan.common`, which contains deprecated proxies in CKAN 2.10.

**Solution**: Replaced all `ckan.common` imports with their modern equivalents.

#### 3.1. Request Object

**Before**:
```python
from ckan.common import request
```

**After**:
```python
from flask import request
```

**Files modified**:
- `ckanext/schemingdcat/blueprint.py` (already using Flask)
- `ckanext/schemingdcat/faceted.py`
- `ckanext/schemingdcat/helpers.py`
- `ckanext/schemingdcat/package_controller.py`

#### 3.2. Config Object

**Before**:
```python
from ckan.common import config
```

**After**:
```python
from ckan.plugins.toolkit import config
```

**Files modified**:
- `ckanext/schemingdcat/utils.py`

#### 3.3. JSON Module

**Before**:
```python
from ckan.common import json
```

**After**:
```python
import json
```

**Files modified**:
- `ckanext/schemingdcat/helpers.py`

#### 3.4. Context Object (c → g)

**Issue**: The Pylons context object `c` is deprecated in favor of Flask's `g` object.

**Before**:
```python
from ckan.common import c
...
if hasattr(c, "search_facets_limits"):
    limit = c.search_facets_limits.get(facet)
```

**After**:
```python
from flask import g as flask_g
...
if hasattr(flask_g, "search_facets_limits"):
    limit = flask_g.search_facets_limits.get(facet)
```

**Files modified**:
- `ckanext/schemingdcat/helpers.py`

### 4. Removed Flask Detection Checks

**Issue**: Code was checking `is_flask_request()` to determine if running under Flask or Pylons.

**Solution**: Removed these checks since CKAN 2.10 is Flask-only.

**Before**:
```python
from ckan.common import is_flask_request
...
params_items = (
    request.params.items(multi=True)
    if is_flask_request()
    else request.params.items()
)
```

**After**:
```python
params_items = request.params.items(multi=True)
```

**Files modified**:
- `ckanext/schemingdcat/helpers.py`

### 5. Package Metadata

**Issue**: Missing Python version classifiers in `setup.py`.

**Solution**: Added appropriate classifiers for Python versions and license.

```python
classifiers=[
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: GNU Affero General Public License v3',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
],
```

## Testing with CKAN 2.10

To test this extension with CKAN 2.10:

1. Ensure you have Python 3.7 or later:
   ```bash
   python --version
   ```

2. Install CKAN 2.10 and required dependencies:
   ```bash
   pip install -e git+https://github.com/ckan/ckan.git@ckan-2.10.5#egg=ckan
   ```

3. Install the extension:
   ```bash
   pip install -e "git+https://github.com/mjanez/ckanext-schemingdcat.git#egg=ckanext-schemingdcat"
   ```

4. Run the tests:
   ```bash
   pytest --ckan-ini=test.ini ckanext/schemingdcat/tests
   ```

## Backward Compatibility

All changes maintain **backward compatibility** with CKAN 2.9.x. The extension will work correctly with both CKAN 2.9 and CKAN 2.10.

## Migration Notes

If you are upgrading from CKAN 2.9 to CKAN 2.10:

1. **No configuration changes required** - The extension will work with your existing configuration.
2. **Python version** - Ensure you're running Python 3.7 or later.
3. **Dependencies** - Update all CKAN extensions to their CKAN 2.10-compatible versions:
   - `ckanext-scheming` (release-3.0.0 or later)
   - `ckanext-dcat` (1.2.0-geodcatap or later)
   - `ckanext-spatial` (v2.1.1 or later)
   - `ckanext-harvest` (v1.5.6 or later)

## What's Still Compatible

The following patterns, while modernized, remain compatible with CKAN 2.9:

- ✅ Blueprint-based routing (modern pattern, works in both versions)
- ✅ Flask request/response objects (works in both versions)
- ✅ `ckan.plugins.toolkit` usage (recommended pattern)
- ✅ Template rendering via `toolkit.render()`
- ✅ Logic layer via `logic.get_action()`

## Known Issues

None at this time. All deprecated code has been updated to use modern CKAN patterns.

## Future Considerations

For future CKAN versions (2.11+), consider:

1. **Plugin interfaces**: Stay updated with IPlugin interface changes
2. **API changes**: Monitor CKAN changelog for API modifications
3. **Template helpers**: Check for helper function updates
4. **Configuration options**: Watch for deprecated config keys

## References

- [CKAN 2.10 Changelog](https://docs.ckan.org/en/2.10/changelog.html)
- [CKAN Extension Development](https://docs.ckan.org/en/2.10/extensions/index.html)
- [Migrating to Flask](https://docs.ckan.org/en/2.9/maintaining/upgrading/upgrade-to-flask.html)

## Contributing

If you find any CKAN 2.10 compatibility issues, please:

1. Open an issue on GitHub
2. Include your CKAN version (`ckan --version`)
3. Include your Python version (`python --version`)
4. Provide error logs and stack traces

---

**Last Updated**: February 2026
**CKAN Versions Tested**: 2.9.0 - 2.10.5
**Python Versions Tested**: 3.7, 3.8, 3.9, 3.10
