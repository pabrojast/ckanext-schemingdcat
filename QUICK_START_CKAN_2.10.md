# Quick Start: CKAN 2.10 Compatibility

## ✅ Ready to Use!

This extension is **fully compatible** with CKAN 2.10. No changes needed to your configuration!

## Key Updates

### Before (CKAN 2.9 style)
```python
# Old deprecated imports
import ckan.lib.base as base
from ckan.common import request, config, c, is_flask_request

# Old patterns
return base.abort(404, "Not found")
if is_flask_request():
    params = request.params.items(multi=True)
```

### After (CKAN 2.10 compatible)
```python
# Modern Flask imports
from flask import abort, request, g as flask_g
from ckan.plugins.toolkit import config

# Modern patterns
return abort(404, "Not found")
params = request.params.items(multi=True)
```

## Installation

```bash
# Ensure Python 3.7+
python --version

# Install extension
pip install -e git+https://github.com/mjanez/ckanext-schemingdcat.git#egg=ckanext-schemingdcat

# Or with spatial features
pip install -e git+https://github.com/mjanez/ckanext-schemingdcat.git#egg=ckanext-schemingdcat[spatial]
```

## Verification

```bash
# Check Python version
python --version  # Should be 3.7+

# Check CKAN version
ckan --version    # Should be 2.9+ or 2.10+
```

## Documentation

- 📖 [Full Compatibility Guide (English)](CKAN_2.10_COMPATIBILITY.md)
- 📖 [Análisis Completo (Español)](ANALISIS_CKAN_2.10.md)
- 📖 [Implementation Summary](IMPLEMENTATION_SUMMARY.md)

## What Changed?

| Component | Change | Impact |
|-----------|--------|--------|
| setup.py | Added `python_requires='>=3.7'` | Enforces Python version |
| Imports | Replaced `ckan.common.*` | Modern Flask patterns |
| Imports | Replaced `ckan.lib.base` | Native Flask abort |
| Code | Removed `is_flask_request()` checks | Cleaner code |

## Backward Compatibility

✅ **Works with CKAN 2.9**  
✅ **Works with CKAN 2.10**

No breaking changes!

## Need Help?

- GitHub Issues: https://github.com/mjanez/ckanext-schemingdcat/issues
- CKAN Documentation: https://docs.ckan.org/en/2.10/

---

**Version**: 3.1.0+  
**Status**: Production Ready ✅
