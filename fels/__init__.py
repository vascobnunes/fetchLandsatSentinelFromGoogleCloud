# =============================================================================================
# Copyright 2018 dgketchum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================================

__dev__ = """
# Command to autogenerate this init file
mkinit -m fels --relative -w
"""

__version__ = '1.4.0'


from . import fels
from . import landsat
from . import sentinel2
from . import utils

from .fels import (convert_wkt_to_scene, get_parser, main, normalize_satcode,
                   run_fels,)
from .landsat import (LANDSAT_METADATA_URL, ensure_landsat_metadata,
                      ensure_landsat_sqlite_conn, get_landsat_image,
                      landsatdir_to_date, query_landsat_catalogue,
                      query_landsat_with_sqlite,)
from .sentinel2 import (SENTINEL2_METADATA_URL, check_full_tile,
                        ensure_sentinel2_metadata,
                        ensure_sentinel2_sqlite_conn, get_S2_INSPIRE_title,
                        get_S2_image_bands, get_sentinel2_image, is_new,
                        query_sentinel2_catalogue, query_sentinel2_with_sqlite,
                        safedir_to_datetime,)
from .utils import (FELS_DEFAULT_OUTPUTDIR, GLOBAL_SQLITE_CONNECTIONS,
                    download_file, download_metadata_file,
                    ensure_sqlite_csv_conn, sort_url_list,)

__all__ = ['FELS_DEFAULT_OUTPUTDIR', 'GLOBAL_SQLITE_CONNECTIONS',
           'LANDSAT_METADATA_URL', 'SENTINEL2_METADATA_URL', 'check_full_tile',
           'convert_wkt_to_scene', 'download_file', 'download_metadata_file',
           'ensure_landsat_metadata', 'ensure_landsat_sqlite_conn',
           'ensure_sentinel2_metadata', 'ensure_sentinel2_sqlite_conn',
           'ensure_sqlite_csv_conn', 'fels', 'get_S2_INSPIRE_title',
           'get_S2_image_bands', 'get_landsat_image', 'get_parser',
           'get_sentinel2_image', 'is_new', 'landsat', 'landsatdir_to_date',
           'main', 'normalize_satcode', 'query_landsat_catalogue',
           'query_landsat_with_sqlite', 'query_sentinel2_catalogue',
           'query_sentinel2_with_sqlite', 'run_fels', 'safedir_to_datetime',
           'sentinel2', 'sort_url_list', 'utils']
