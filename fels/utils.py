from __future__ import absolute_import, division, print_function
import os
import shutil
import gzip
import json
import requests
import pkg_resources
import ubelt as ub
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
import geopandas
import shapely as shp


FELS_DEFAULT_OUTPUTDIR = os.environ.get('FELS_DEFAULT_OUTPUTDIR', '')
if not FELS_DEFAULT_OUTPUTDIR:
    FELS_DEFAULT_OUTPUTDIR = os.path.expanduser('~/data/fels')


def download_metadata_file(url, outputdir, program):
    """Download and unzip the catalogue files."""
    if outputdir is None:
        outputdir = FELS_DEFAULT_OUTPUTDIR
    zipped_index_path = os.path.join(outputdir, 'index_' + program + '.csv.gz')
    if not os.path.isfile(zipped_index_path):
        if not os.path.exists(os.path.dirname(zipped_index_path)):
            os.makedirs(os.path.dirname(zipped_index_path))
        print("Downloading Metadata file...")
        content = urlopen(url)
        with open(zipped_index_path, 'wb') as f:
            shutil.copyfileobj(content, f)
    index_path = os.path.join(outputdir, 'index_' + program + '.csv')
    if not os.path.isfile(index_path):
        print("Unzipping Metadata file...")
        with gzip.open(zipped_index_path) as gzip_index, open(index_path, 'wb') as f:
            shutil.copyfileobj(gzip_index, f)
    return index_path


def sort_url_list(cc_values, all_acqdates, all_urls):
    """Sort the url list by increasing cc_values and acqdate."""
    cc_values = sorted(cc_values)
    all_acqdates = sorted(all_acqdates, reverse=True)
    all_urls = [x for (y, z, x) in sorted(zip(cc_values, all_acqdates, all_urls))]
    urls = []
    for url in all_urls:
        urls.append('http://storage.googleapis.com/' + url.replace('gs://', ''))
    return urls


def download_file(url, destination_filename):
    """Function to download files using pycurl lib"""
    with requests.get(url, stream=True) as r:
        with open(destination_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)


def convert_wkt_to_scene(sat, geometry, include_overlap):
    '''
    Args:
        sat: 'S2', 'ETM', 'OLI_TIRS'
        geometry: WKT or GeoJSON string
        include_overlap: if True, use predicate 'intersects', else use predicate 'contains'

    Returns:
        List of scenes containing the geometry

    Example:
        >>> sat = 'S2'
        >>> geometry = json.dumps({
        >>>     'type': 'Polygon', 'coordinates': [[
        >>>         [40.4700, -74.2700],
        >>>         [41.3100, -74.2700],
        >>>         [41.3100, -71.7500],
        >>>         [40.4700, -71.7500],
        >>>         [40.4700, -74.2700],
        >>>     ]]})
        >>> include_overlap = True
        >>> convert_wkt_to_scene('S2', geometry, include_overlap)
        >>> convert_wkt_to_scene('LC', geometry, include_overlap)
    '''

    if sat == 'S2':
        path = pkg_resources.resource_filename(__name__, os.path.join('data', 'sentinel_2_index_shapefile.shp'))
    else:
        path = pkg_resources.resource_filename(__name__, os.path.join('data', 'WRS2_descending.shp'))

    try:
        feat = shp.geometry.shape(json.loads(geometry))
    except json.JSONDecodeError:
        feat = shp.wkt.loads(geometry)

    # gdf = geopandas.read_file(path)
    gdf = _memo_geopandas_read(path)

    if include_overlap:
        # TODO paramatarize thresh
        thresh = 0.0
        if thresh > 0:
            # Requires some minimum overlap
            overlap = gdf.geometry.intersection(feat).area / feat.area
            found = gdf[overlap > thresh]
        else:
            # Any amount of overlap is ok
            found = gdf[gdf.geometry.intersects(feat)]
    else:
        # This is the bottleneck when the downloaded data exists
        found = gdf[gdf.geometry.contains(feat)]

    if sat == 'S2':
        return found.Name.values
    else:
        return found.WRSPR.values


@ub.memoize
def _memo_geopandas_read(path):
    return geopandas.read_file(path)
