from app.config import settings as settings_module
print('Settings MRO:', settings_module.Settings.__mro__)
print('GTFS_DATA_DIR default:', settings_module.settings.GTFS_DATA_DIR)
import os
os.environ['GTFS_DATA_DIR']='C:/tmp/foo'
# re-instantiate to see env effect
s = settings_module.Settings()
print('GTFS_DATA_DIR from new instance:', s.GTFS_DATA_DIR)
