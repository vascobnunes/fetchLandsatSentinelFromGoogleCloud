from __future__ import absolute_import, division, print_function
import os
import shutil
import gzip
import atexit
import json
import requests
import pkg_resources
import ubelt as ub
import csv
import sqlite3
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
import geopandas
import shapely as shp


FELS_DEFAULT_OUTPUTDIR = os.environ.get('FELS_DEFAULT_OUTPUTDIR', '')
if not FELS_DEFAULT_OUTPUTDIR:
    FELS_DEFAULT_OUTPUTDIR = ub.get_app_cache_dir('fels')
    # FELS_DEFAULT_OUTPUTDIR = os.path.expanduser('~/data/fels')


def download_metadata_file(url, outputdir, program):
    """Download and unzip the catalogue files."""
    if outputdir is None:
        outputdir = FELS_DEFAULT_OUTPUTDIR
    zipped_index_path = os.path.join(outputdir, 'index_' + program + '.csv.gz')
    if not os.path.isfile(zipped_index_path):
        if not os.path.exists(os.path.dirname(zipped_index_path)):
            os.makedirs(os.path.dirname(zipped_index_path))
        print("Downloading Metadata file...")
        print('url = {!r}'.format(url))
        print('outputdir = {!r}'.format(outputdir))
        print('program = {!r}'.format(program))
        ub.download(url, fpath=zipped_index_path)
        # content = urlopen(url)
        # with open(zipped_index_path, 'wb') as f:
        #     shutil.copyfileobj(content, f)
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

    if isinstance(geometry, dict):
        feat = shp.geometry.shape(geometry)
    elif isinstance(geometry, str):
        try:
            feat = shp.geometry.shape(json.loads(geometry))
        except json.JSONDecodeError:
            feat = shp.wkt.loads(geometry)
    else:
        raise TypeError(type(geometry))

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


GLOBAL_SQLITE_CONNECTIONS = {}


def ensure_sqlite_csv_conn(collection_file, fields, table_create_cmd,
                           tablename='unnamed_table1', index_cols=[],
                           overwrite=False):
    """
    Returns a connection to a cache of a csv file
    """
    import ubelt as ub
    sql_fpath = collection_file + '.v001.sqlite'
    overwrite = False
    if os.path.exists(sql_fpath):
        sql_stat = os.stat(sql_fpath)
        col_stat = os.stat(collection_file)
        if 1:
            print('col_stat = {!r}'.format(col_stat))
            print('sql_stat = {!r}'.format(sql_stat))
        # CSV file has a newer modified time, we have to update
        if col_stat.st_mtime > sql_stat.st_mtime:
            overwrite = True
    else:
        overwrite = True

    stamp_dpath = ub.ensuredir((os.path.dirname(collection_file), '.stamps'))
    base_name = os.path.basename(collection_file)

    stamp = ub.CacheStamp(base_name, dpath=stamp_dpath, depends=[
        fields, table_create_cmd, tablename],
        # product=[sql_fpath],
        verbose=3
    )
    if stamp.expired():
        overwrite = True

    if overwrite:
        # Update the SQL cache if the CSV file was modified.
        print('Computing (or recomputing) an sql cache')

        ub.delete(sql_fpath, verbose=3)
        print('Initial connection to sql_fpath = {!r}'.format(sql_fpath))
        conn = sqlite3.connect(sql_fpath)

        try:
            cur = conn.cursor()

            print('(SQL) >')
            print(table_create_cmd)
            cur.execute(table_create_cmd)

            keypart = ','.join(fields)
            valpart = ','.join('?' * len(fields))
            insert_statement = ub.codeblock(
                '''
                INSERT INTO {tablename}({keypart})
                VALUES({valpart})
                ''').format(keypart=keypart, valpart=valpart,
                            tablename=tablename)

            if index_cols:
                index_cols_str = ', '.join(index_cols)
                indexname = 'noname_index'
                # Can we make an efficient date index with sqlite?
                create_index_cmd = ub.codeblock(
                    '''
                    CREATE INDEX {indexname} ON {tablename} ({index_cols_str});
                    ''').format(
                        index_cols_str=index_cols_str, tablename=tablename,
                        indexname=indexname)
                print('(SQL) >')
                print(create_index_cmd)
                _ = cur.execute(create_index_cmd)

            print('collection_file = {!r}'.format(collection_file))
            with open(collection_file) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in ub.ProgIter(reader,
                                       desc='insert csv rows into sqlite cache',
                                       freq=10000, adjust=False):
                    vals = [row[k] for k in fields]
                    cur.execute(insert_statement, vals)
            conn.commit()
        except Exception:
            raise
        else:
            GLOBAL_SQLITE_CONNECTIONS[sql_fpath] = conn
            stamp.renew()
        finally:
            conn.close()

    # hack to not reconnect each time
    if sql_fpath in GLOBAL_SQLITE_CONNECTIONS:
        conn = GLOBAL_SQLITE_CONNECTIONS[sql_fpath]
    else:
        conn = sqlite3.connect(sql_fpath)
        GLOBAL_SQLITE_CONNECTIONS[sql_fpath] = conn

    return conn


@atexit.register
def _close_global_conns():
    for conn in GLOBAL_SQLITE_CONNECTIONS.values():
        conn.close()
    GLOBAL_SQLITE_CONNECTIONS.clear()
