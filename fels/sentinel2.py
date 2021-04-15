from __future__ import absolute_import, division, print_function
import csv
import datetime
import os
import sys
import shutil
import glob
import numpy as np
import xml.etree.ElementTree as ET
from tempfile import NamedTemporaryFile
try:
    from urllib2 import urlopen
    from urllib2 import HTTPError
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen, HTTPError, URLError
try:
    from osgeo import gdal
except ImportError:
    raise ImportError("""Could not find the GDAL/OGR Python library bindings. Using conda \
(recommended) use: conda config --add channels conda-forge && conda install gdal""")


from fels.utils import *

def query_sentinel2_catalogue(collection_file, cc_limit, date_start, date_end, tile, latest=False):
    """Query the Sentinel-2 index catalogue and retrieve urls for the best images found."""
    print("Searching for Sentinel-2 images in catalog...")
    cc_values = []
    all_urls = []
    all_acqdates = []
    with open(collection_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            year_acq = int(row['SENSING_TIME'][0:4])
            month_acq = int(row['SENSING_TIME'][5:7])
            day_acq = int(row['SENSING_TIME'][8:10])
            acqdate = datetime.datetime(year_acq, month_acq, day_acq)
            if row['MGRS_TILE'] == tile and float(row['CLOUD_COVER']) <= cc_limit \
                    and date_start < acqdate < date_end:
                all_urls.append(row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))
                all_acqdates.append(acqdate)

    if latest and all_urls:
        return [sort_url_list(cc_values, all_acqdates, all_urls).pop()]
    return sort_url_list(cc_values, all_acqdates, all_urls)


def get_sentinel2_image(url, outputdir, overwrite=False, partial=False, noinspire=False, reject_old=False):
    """
    Collect the entire dir structure of the image files from the
    manifest.safe file and build the same structure in the output
    location.

    Returns:
        True if image was downloaded
        False if partial=False and image was not fully downloaded
            or if reject_old=True and it is old-format
            or if noinspire=False and INSPIRE file is missing
    """
    img = os.path.basename(url)
    target_path = os.path.join(outputdir, img)
    target_manifest = os.path.join(target_path, "manifest.safe")

    return_status = True
    if not os.path.exists(target_path) or overwrite:

        manifest_url = url + "/manifest.safe"

        if reject_old:
            # check contents of manifest before downloading the rest
            content = urlopen(manifest_url)
            with NamedTemporaryFile() as f:
                shutil.copyfileobj(content, f)
                if not is_new(f.name):
                    return False

        os.makedirs(target_path, exist_ok=True)
        content = urlopen(manifest_url)
        with open(target_manifest, 'wb') as f:
            shutil.copyfileobj(content, f)
        with open(target_manifest, 'r') as manifest_file:
            manifest_lines = manifest_file.read().split()
        for line in manifest_lines:
            if 'href' in line:
                rel_path = line[line.find('href=".')+7:]
                rel_path = rel_path[:rel_path.find('"')]
                abs_path = os.path.join(target_path, *rel_path.split('/')[1:])
                if not os.path.exists(os.path.dirname(abs_path)):
                    os.makedirs(os.path.dirname(abs_path))
                try:
                    download_file(url + rel_path, abs_path)
                except HTTPError as error:
                    print("Error downloading {} [{}]".format(url + rel_path, error))
                    continue
        granule = os.path.dirname(os.path.dirname(get_S2_image_bands(target_path, "B01")))
        for extra_dir in ("AUX_DATA", "HTML"):
            if not os.path.exists(os.path.join(target_path, extra_dir)):
                os.makedirs(os.path.join(target_path, extra_dir))
            if not os.path.exists(os.path.join(granule, extra_dir)):
                os.makedirs(os.path.join(granule, extra_dir))
        if not manifest_lines:
            print()
    elif reject_old and not is_new(target_manifest):
        print(f'Warning: old-format image {outputdir} exists')
        return_status = False

    if partial:
        tile_chk = check_full_tile(get_S2_image_bands(target_path, "B01"))
        if tile_chk == 'Partial':
            print("Removing partial tile image files...")
            shutil.rmtree(target_path)
            return_status = False
    if not noinspire:
        inspire_file = os.path.join(target_path, "INSPIRE.xml")
        if os.path.isfile(inspire_file):
            inspire_path = get_S2_INSPIRE_title(inspire_file)
            if os.path.basename(target_path) != inspire_path:
                os.rename(target_path, inspire_path)
        else:
            print(f"File {inspire_file} could not be found.")
            return_status = False

    return return_status


def get_S2_image_bands(image_path, band):
    image_name = os.path.basename(image_path)
    tile = image_name.split("_")[5]
    list_dirs = os.listdir(os.path.join(image_path, 'GRANULE'))
    match = [x for x in list_dirs if x.find(tile) > 0][0]
    list_files = os.path.join(image_path, 'GRANULE', match, 'IMG_DATA')
    files = glob.glob(list_files + "/*.jp2")
    match_band = [x for x in files if x.find(band) > 0][0]
    return match_band


def get_S2_INSPIRE_title(image_inspire_xml):
    tree = ET.parse(image_inspire_xml)
    chartstring_element = tree.findall(
        ".//{http://www.isotc211.org/2005/gmd}identificationInfo/{http://www.isotc211.org/2005/gmd}MD_DataIdentification/{http://www.isotc211.org/2005/gmd}citation/{http://www.isotc211.org/2005/gmd}CI_Citation/{http://www.isotc211.org/2005/gmd}title/{http://www.isotc211.org/2005/gco}CharacterString")
    s2_file_inspire_title = chartstring_element[0].text
    return s2_file_inspire_title


def check_full_tile(image):
    gdalData = gdal.Open(image)
    if gdalData is None:
        sys.exit("ERROR: can't open raster")

    # get width and heights of the raster
    xsize = gdalData.RasterXSize
    ysize = gdalData.RasterYSize

    # process the raster
    band_i = gdalData.GetRasterBand(1)
    raster = band_i.ReadAsArray()

    # create dictionary for unique values count
    count = {}

    # count unique values for the given band
    for col in range(xsize):
        for row in range(ysize):
            cell_value = raster[row, col]

            # check if cell_value is NaN
            if cell_value == 0:
                # add cell_value to dictionary
                if cell_value in count:
                    count[cell_value] += 1
                else:
                    count[cell_value] = 1
                break
    for key in sorted(count.keys()):
        if count[key] is not None:
            return "Partial"


def is_new(safedir_or_manifest):
    '''
    Check if a S2 scene is in the new (after Nov 2016) format.

    If the scene is already downloaded, the safedir directory structure can be crawled to determine this.
    If not, download the manifest.safe first for an equivalent check.

    Example:
        >>> safedir = 'S2A_MSIL1C_20160106T021717_N0201_R103_T52SDG_20160106T094733.SAFE/'
        >>> manifest = os.path.join(safedir, 'manifest.safe')
        >>> assert is_new(safedir) == False
        >>> assert is_new(manifest) == False
    '''
    if os.path.isdir(safedir_or_manifest):
        safedir = safedir_or_manifest
        # if this file does not have the standard name (len==0), the scene is old format.
        # if it is duplicated (len>1), there are multiple granuledirs and we don't want that.
        return len(glob.glob(os.path.join(safedir, 'GRANULE', '*', 'MTD_TL.xml'))) == 1

    elif os.path.isfile(safedir_or_manifest):
        manifest = safedir_or_manifest
        with open(manifest, 'r') as f:
            lines = f.read().split()
        return len([l for l in lines if 'MTD_TL.xml' in l]) == 1

    else:
        raise ValueError(f'{safedir_or_manifest} is not a safedir or manifest')

def _dedupe(safedirs, to_return=None):
    '''
    Remove old-format scenes from a list of Google Cloud S2 safedirs

    WARNING: this heuristic is usually, but not always, true.
    Therefore, it is deprecated in favor of is_new, which requires parsing the actual content of the image.

    A failure case:
        https://console.cloud.google.com/storage/browser/gcp-public-data-sentinel-2/tiles/52/S/DG/S2A_MSIL1C_20160106T021702_N0201_R103_T52SDG_20160106T021659.SAFE
        https://console.cloud.google.com/storage/browser/gcp-public-data-sentinel-2/tiles/52/S/DG/S2A_MSIL1C_20160106T021717_N0201_R103_T52SDG_20160106T094733.SAFE

    These are the same scene. The first link is new-format. They *should* have the same sensing time, but the second one is offset by 15 ms for unknown reasons.

    Args:
        to_return: a list of other products (eg urls) indexed to safedirs.
            if provided, dedupe this as well.
    '''
    _safedirs = np.array(sorted(safedirs))
    datetimes = [safedir_to_datetime(s) for s in _safedirs]
    prods = [safedir_to_datetime(s, product=True) for s in _safedirs]
    # first sorted occurrence should be the earliest product discriminator
    _, idxs = np.unique(datetimes, return_index=True)
    if to_return is None:
        return _safedirs[idxs]
    else:
        return _safedirs[idxs], np.array(sorted(to_return))[idxs]


def safedir_to_datetime(string, product=False):
    '''
    Example:
        >>> from datetime import datetime
        >>> s = 'S2B_MSIL1C_20181010T021649_N0206_R003_T52SDG_20181010T064007.SAFE'
        >>> dt = safedir_to_datetime(s)
        >>> assert dt == datetime(2018, 10, 10, 2, 16, 49)

    References:
        https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/naming-convention
    '''
    if not product:
        dt_str = string.split('_')[2]  # this is the "datatake sensing time"
    else:
        dt_str = string.split('_')[6].strip(
            '.SAFE')  # this is the "Product Discriminator"
    d_str, t_str = dt_str.split('T')
    d = list(map(int, [d_str[:4], d_str[4:6], d_str[6:]]))
    t = list(map(int, [t_str[:2], t_str[2:4], t_str[4:]]))
    return datetime.datetime(*d, *t)
