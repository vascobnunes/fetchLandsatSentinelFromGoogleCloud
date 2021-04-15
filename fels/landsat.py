from __future__ import absolute_import, division, print_function
import csv
import datetime
import os
import socket
import time
import shutil
try:
    from urllib2 import urlopen
    from urllib2 import HTTPError
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen, HTTPError, URLError


from fels.utils import *


def query_landsat_catalogue(collection_file, cc_limit, date_start, date_end, wr2path, wr2row,
                            sensor, latest=False):
    """Query the Landsat index catalogue and retrieve urls for the best images found."""
    print("Searching for Landsat-{} images in catalog...".format(sensor))
    cc_values = []
    all_urls = []
    all_acqdates = []
    with open(collection_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            year_acq = int(row['DATE_ACQUIRED'][0:4])
            month_acq = int(row['DATE_ACQUIRED'][5:7])
            day_acq = int(row['DATE_ACQUIRED'][8:10])
            acqdate = datetime.datetime(year_acq, month_acq, day_acq)
            if int(row['WRS_PATH']) == int(wr2path) and int(row['WRS_ROW']) == int(wr2row) \
                    and row['SENSOR_ID'] == sensor and float(row['CLOUD_COVER']) <= cc_limit \
                    and date_start < acqdate < date_end:
                all_urls.append(row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))
                all_acqdates.append(acqdate)

    if latest and all_urls:
        return [sort_url_list(cc_values, all_acqdates, all_urls).pop()]
    return sort_url_list(cc_values, all_acqdates, all_urls)

def get_landsat_image(url, outputdir, overwrite=False, sat="TM"):
    """Download a Landsat image file."""
    img = os.path.basename(url)
    if sat == "TM":
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B7.TIF', 'GCP.txt', 'VER.txt', 'VER.jpg',
                          'ANG.txt', 'BQA.TIF', 'MTL.txt']
    elif sat == "OLI_TIRS":
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B7.TIF', 'B8.TIF', 'B9.TIF', 'B10.TIF',
                          "B11.TIF", 'ANG.txt', 'BQA.TIF', 'MTL.txt']
    elif sat == "ETM":
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
        complete_url = url + "/" + img + "_" + band
        target_file = os.path.join(target_path, img + "_" + band)
        if os.path.exists(target_file) and not overwrite:
            print(target_file, "exists and --overwrite option was not used. Skipping image download")
            continue
        try:
            content = urlopen(complete_url, timeout=600)
        except HTTPError:
            print("Could not find", band, "band image file.")
            continue
        except URLError:
            print("Timeout, Restart=======>")
            time.sleep(10)
            get_landsat_image(url, outputdir, overwrite, sat)
            return
        with open(target_file, 'wb') as f:
            try:
                shutil.copyfileobj(content, f)
            except socket.timeout:
                print("Socket Timeout, Restart=======>")
                time.sleep(10)
                get_landsat_image(url, outputdir, overwrite, sat)
                return
            print("Downloaded", target_file)


def landsatdir_to_date(string, processing=False):
    '''
    Example:
        >>> from datetime import date
        >>> s = 'LE07_L1GT_115034_20160707_20161009_01_T2'
        >>> d = landsatdir_to_date(s)
        >>> assert d == date(2016, 07, 07)

    References:
        https://github.com/dgketchum/Landsat578#-1
    '''
    if not processing:
        d_str = string.split('_')[3]  # this is the acquisition date
    else:
        d_str = string.split('_')[4]  # this is the processing date
    d = list(map(int, [d_str[:4], d_str[4:6], d_str[6:]]))
    return datetime.date(*d)

