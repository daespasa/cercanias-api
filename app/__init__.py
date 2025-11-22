"""Package initializer for `app`.

This module exposes the FastAPI instance defined in the top-level `app.py` file
as the attribute `app`, so tests and other imports that do `from app import app`
continue to work even though there is a package named `app`.

We load `app.py` explicitly from the project root and expose its `app` symbol.
"""
from importlib import util, import_module
import os
import sys

_root = os.path.dirname(os.path.dirname(__file__))
_app_py = os.path.join(_root, "app.py")

if os.path.exists(_app_py):
	spec = util.spec_from_file_location("_cercanias_app_module", _app_py)
	module = util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	# expose the FastAPI instance
	try:
		app = getattr(module, "app")
	except Exception:
		# fallback: module may not define app yet
		app = None
else:
	app = None

__all__ = ["app"]
