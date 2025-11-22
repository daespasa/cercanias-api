import os
from pathlib import Path
import tempfile

os.environ['GTFS_DATA_DIR']='x'
from app.config import settings as settings_module
print('Settings type:', settings_module.Settings)
print('Settings MRO:', settings_module.Settings.__mro__)
print('settings instance type:', type(settings_module.settings))
print('pydantic present?')
try:
    import pydantic
    print('pydantic version', pydantic.__version__)
except Exception as e:
    print('pydantic import failed', e)
