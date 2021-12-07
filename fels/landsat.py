# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import csv
import datetime
import os
import socket
import time
import shutil
import ubelt
import dateutil
try:
    from urllib2 import urlopen
    from urllib2 import HTTPError
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen, HTTPError, URLError

from fels.utils import (
    sort_url_list, download_metadata_file, ensure_sqlite_csv_conn)


LANDSAT_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-landsat/index.csv.gz'


def ensure_landsat_metadata(outputdir=None):
    return download_metadata_file(LANDSAT_METADATA_URL, outputdir, 'Landsat')


def query_landsat_catalogue(collection_file, cc_limit, date_start, date_end,
                            wr2path, wr2row, sensor, latest=False,
                            use_csv=False):
    """
    Query the Landsat index catalogue and retrieve urls for the best images
    found.

    Example:
        >>> from fels.landsat import *  # NOQA
        >>> from fels import convert_wkt_to_scene
        >>> import dateutil
        >>> import json
        >>> collection_file = ensure_landsat_metadata()
        >>> cc_limit = 100
        >>> date_start = dateutil.parser.isoparse('2015-01-01')
        >>> date_end = dateutil.parser.isoparse('2016-01-01')
        >>> geometry = json.dumps({
        >>>     'type': 'Polygon', 'coordinates': [[
        >>>         [40.4700, -74.2700],
        >>>         [41.3100, -74.2700],
        >>>         [41.3100, -71.7500],
        >>>         [40.4700, -71.7500],
        >>>         [40.4700, -74.2700],
        >>>     ]]})
        >>> scenes = convert_wkt_to_scene('LC', geometry, True)
        >>> scene = scenes[0]
        >>> wr2path = scene[0:3]
        >>> wr2row = scene[3:6]
        >>> sensor = 'OLI_TIRS'
        >>> latest = False
        >>> results = query_landsat_catalogue(collection_file, cc_limit, date_start,
        >>>                         date_end, wr2path, wr2row, sensor,
        >>>                         latest, use_csv=False)
        >>> print('results = {}'.format(ubelt.repr2(results, nl=1)))
        results = [
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20151226_20170331_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20151108_20170402_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20151023_20170402_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20150209_20170413_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20150108_20180524_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20150124_20170413_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20151210_20170401_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20151124_20170401_01_T2',
            'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/141/112/LC08_L1GT_141112_20150225_20170412_01_T2',
        ]
    """
    print('Searching for Landsat-{} images in catalog...'.format(sensor))
    if use_csv:
        return _query_landsat_with_csv(
            collection_file, cc_limit, date_start, date_end, wr2path, wr2row,
            sensor, latest=latest)
    else:
        # Generally SQL is faster
        return _query_landsat_with_sqlite(
            collection_file, cc_limit, date_start, date_end, wr2path, wr2row,
            sensor, latest=latest)


def _query_landsat_with_csv(collection_file, cc_limit, date_start, date_end,
                            wr2path, wr2row, sensor, latest=False):
    if isinstance(date_start, str):
        date_start = dateutil.parser.isoparse(date_start)
    if isinstance(date_end, str):
        date_end = dateutil.parser.isoparse(date_end)
    cc_values = []
    all_urls = []
    all_acqdates = []
    with open(collection_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in ubelt.ProgIter(reader, desc='searching L8'):
            year_acq = int(row['DATE_ACQUIRED'][0:4])
            month_acq = int(row['DATE_ACQUIRED'][5:7])
            day_acq = int(row['DATE_ACQUIRED'][8:10])
            acqdate = datetime.datetime(year_acq, month_acq, day_acq)
            if int(row['WRS_PATH']) == int(wr2path) and int(row['WRS_ROW']) == int(wr2row) \
                    and row['SENSOR_ID'] == sensor and float(row['CLOUD_COVER']) <= cc_limit \
                    and date_start <= acqdate <= date_end:
                all_urls.append(row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))
                all_acqdates.append(acqdate)

    if latest and all_urls:
        return [sort_url_list(cc_values, all_acqdates, all_urls).pop()]
    return sort_url_list(cc_values, all_acqdates, all_urls)


def _query_landsat_with_sqlite(collection_file, cc_limit, date_start, date_end,
                               wr2path, wr2row, sensor, latest=False):
    conn = _ensure_landsat_sqlite_conn(collection_file)
    cur = conn.cursor()

    try:
        result = cur.execute(
            '''
            SELECT BASE_URL, CLOUD_COVER, DATE_ACQUIRED from landsat WHERE

            WRS_PATH=? AND WRS_ROW=? AND SENSOR_ID=? AND CLOUD_COVER <= ?
            and
            date(DATE_ACQUIRED) BETWEEN date(?) AND date(?)
            ''', (
                int(wr2path),
                int(wr2row),
                sensor,
                cc_limit,
                date_start,
                date_end,
            ))
        cc_values = []
        all_urls = []
        all_acqdates = []
        for found in result:
            all_urls.append(found[0])
            cc_values.append(found[1])
            all_acqdates.append(dateutil.parser.isoparse(found[2]))
    finally:
        cur.close()

    if latest and all_urls:
        return [sort_url_list(cc_values, all_acqdates, all_urls).pop()]
    return sort_url_list(cc_values, all_acqdates, all_urls)


def _ensure_landsat_sqlite_conn(collection_file):
    tablename = 'landsat'
    fields = ['SCENE_ID', 'SENSOR_ID', 'PRODUCT_ID', 'BASE_URL',
              'DATE_ACQUIRED', 'WRS_PATH', 'WRS_ROW', 'CLOUD_COVER']
    index_cols = ['WRS_ROW', 'WRS_PATH']
    table_create_cmd = ubelt.codeblock(
        '''
        CREATE TABLE landsat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            SCENE_ID TEXT NOT NULL,
            SENSOR_ID TEXT NOT NULL,
            PRODUCT_ID TEXT NOT NULL,
            BASE_URL TEXT NOT NULL,
            DATE_ACQUIRED TEXT NOT NULL,
            WRS_PATH INTEGER NOT NULL,
            WRS_ROW INTEGER NOT NULL,
            CLOUD_COVER REAL NOT NULL
        );
        ''')
    conn = ensure_sqlite_csv_conn(
        collection_file, fields, table_create_cmd, tablename,
        index_cols=index_cols, overwrite=False)
    return conn


def get_landsat_image(url, outputdir, overwrite=False, sat='TM'):
    """Download a Landsat image file."""
    img = os.path.basename(url)
    if sat == 'TM':
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B7.TIF', 'GCP.txt', 'VER.txt', 'VER.jpg',
                          'ANG.txt', 'BQA.TIF', 'MTL.txt']
    elif sat == 'OLI_TIRS':
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B7.TIF', 'B8.TIF', 'B9.TIF', 'B10.TIF',
                          'B11.TIF', 'ANG.txt', 'BQA.TIF', 'MTL.txt']
    elif sat == 'ETM':
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6_VCID_1.TIF', 'B6_VCID_2.TIF', 'B7.TIF',
                          'B8.TIF', 'ANG.txt', 'BQA.TIF', 'MTL.txt']
    else:
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B6_VCID_1.TIF', 'B6_VCID_2.TIF', 'B7.TIF',
                          'B8.TIF', 'B9.TIF', 'ANG.txt', 'BQA.TIF', 'MTL.txt']

    target_path = os.path.join(outputdir, img)

    os.makedirs(target_path, exist_ok=True)
    for band in possible_bands:
        complete_url = url + '/' + img + '_' + band
        target_file = os.path.join(target_path, img + '_' + band)
        if os.path.exists(target_file) and not overwrite:
            print(target_file, 'exists and --overwrite option was not used. Skipping image download')
            continue
        try:
            content = urlopen(complete_url, timeout=600)
        except HTTPError:
            print('Could not find', band, 'band image file.')
            continue
        except URLError:
            print('Timeout, Restart=======>')
            time.sleep(10)
            get_landsat_image(url, outputdir, overwrite, sat)
            return
        with open(target_file, 'wb') as f:
            try:
                shutil.copyfileobj(content, f)
            except socket.timeout:
                print('Socket Timeout, Restart=======>')
                time.sleep(10)
                get_landsat_image(url, outputdir, overwrite, sat)
                return
            print('Downloaded', target_file)


def landsatdir_to_date(string, processing=False):
    """
    Example:
        >>> from datetime import date
        >>> s = 'LE07_L1GT_115034_20160707_20161009_01_T2'
        >>> d = landsatdir_to_date(s)
        >>> assert d == date(2016, 7, 7)

    References:
        https://github.com/dgketchum/Landsat578#-1
    """
    if not processing:
        d_str = string.split('_')[3]  # this is the acquisition date
    else:
        d_str = string.split('_')[4]  # this is the processing date
    d = list(map(int, [d_str[:4], d_str[4:6], d_str[6:]]))
    return datetime.date(*d)
