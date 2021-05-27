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

from .fels import (convert_wkt_to_scene, get_parser, main, run_fels,)
from .landsat import (get_landsat_image, landsatdir_to_date,
                      query_landsat_catalogue,)
from .sentinel2 import (check_full_tile, get_S2_INSPIRE_title,
                        get_S2_image_bands, get_sentinel2_image, is_new,
                        query_sentinel2_catalogue, safedir_to_datetime,)
from .utils import (download_file, download_metadata_file, sort_url_list,)

__all__ = ['check_full_tile', 'convert_wkt_to_scene', 'download_file',
           'download_metadata_file', 'fels', 'get_S2_INSPIRE_title',
           'get_S2_image_bands', 'get_landsat_image', 'get_parser',
           'get_sentinel2_image', 'is_new', 'landsat', 'landsatdir_to_date',
           'main', 'query_landsat_catalogue', 'query_sentinel2_catalogue',
           'run_fels', 'safedir_to_datetime', 'sentinel2', 'sort_url_list',
           'utils']
