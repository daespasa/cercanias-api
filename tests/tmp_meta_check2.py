import os, json, tempfile
from pathlib import Path

# prepare temp dir
tmp = Path(tempfile.mkdtemp())
print('tmp:', tmp)
zip_path = tmp / 'fomento_transit.zip'
zip_path.write_bytes(b'fake')
meta = {"etag": 'W/"abc"', 'last_downloaded_at': '2025-01-01T00:00:00Z', 'status': 'downloaded'}
meta_path = str(zip_path) + '.meta'
with open(meta_path, 'w', encoding='utf-8') as f:
    json.dump(meta, f)

os.environ['GTFS_DATA_DIR'] = str(tmp)
# import app now
from app import app
from app.core.gtfs_downloader import gtfs_downloader
from app.config import settings as settings_module
print('settings.GTFS_DATA_DIR:', settings_module.settings.GTFS_DATA_DIR)
print('gtfs_downloader._meta_path:', getattr(gtfs_downloader, '_meta_path', None))
print('expected meta path:', meta_path)
print('meta exists:', os.path.exists(meta_path))
print('gtfs_downloader.get_metadata():', gtfs_downloader.get_metadata())
