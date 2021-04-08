"""TODO module documentation"""
from __future__ import absolute_import, division, print_function
import argparse
import csv
import datetime
import os
import socket
import sys
import tempfile
import requests
import time
import shutil
import glob
import gzip
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


def download_metadata_file(url, outputdir, program):
    """Download and unzip the catalogue files."""
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


def download_file(url, destination_filename):
    """Function to download files using pycurl lib"""
    with requests.get(url, stream=True) as r:
        with open(destination_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)


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


def get_parser():
    parser = argparse.ArgumentParser(description="Find and download Landsat and Sentinel-2 data from the public Google Cloud")
    parser.add_argument("scene", help="WRS2 coordinates of scene (ex 198030)")
    parser.add_argument("sat", help="Which satellite are you looking for", choices=['TM', 'ETM', 'OLI_TIRS', 'S2'])
    parser.add_argument("start_date", help="Start date, in format YYYY-MM-DD. Left-exclusive.", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("end_date", help="End date, in format YYYY-MM-DD. Right-exclusive.", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("-c", "--cloudcover", type=float, help="Set a limit to the cloud cover of the image", default=100)
    parser.add_argument("-o", "--output", help="Where to download files", default=os.getcwd())
    parser.add_argument("-e", "--excludepartial", help="Exclude partial tiles - only for Sentinel-2", default=False)
    parser.add_argument("--latest", help="Limit to the latest scene", action="store_true", default=False)
    parser.add_argument("--noinspire", help="Do not rename output image folder to the title collected from the inspire.xml file (only for S2 datasets)", action="store_true", default=False)
    parser.add_argument("--outputcatalogs", help="Where to download metadata catalog files", default=None)
    parser.add_argument("--overwrite", help="Overwrite files if existing locally", action="store_true", default=False)
    parser.add_argument("-l", "--list", help="List available download urls and exit without downloading", action="store_true", default=False)
    parser.add_argument("-d", "--dates", help="List or return dates instead of download urls", action="store_true", default=False)
    parser.add_argument("-r", "--reject_old", help="For S2, skip redundant old-format (before Nov 2016) images", action="store_true", default=False)
    return parser


def main():
    '''
    CLI entrypoint.
    '''
    options = get_parser().parse_args()

    if not options.outputcatalogs:
        options.outputcatalogs = options.output
    
    urls_or_dates = _run_fels(options)

    if options.list:
        for u in urls_or_dates:
            print(u)


def run_fels(*args, **kwargs):
    '''
    Python entrypoint.

    See main() for arguments. Additional options not present in argparse include
    Args:
        scene: for Landsat, can pass in a (path,row) tuple such as (115,34)
        sat: 'L5', 'L7', 'L8' are aliases for 'TM', 'ETM', 'OLI_TIRS'
        start_date: can pass in a datetime.date directly
        end_date: can pass in a datetime.date directly

    Other differences from CLI:
        Returns the list of urls. Therefore, will not print them with list=True.

    Example:
        >>> # downloading a tile from the CLI
        >>> os.system('fels 203031 OLI_TIRS 2015-01-01 2015-06-30 -c 30 -o . --latest --outputcatalogs ~/data/fels/')
        >>> # downloading the same tile in Python
        >>> from datetime import date
        >>> from fels import run_fels
        >>> run_fels((203,31), 'L8', date(2015, 1, 1), date(2015, 6, 30), cloudcover=30, output='.', latest=True, outputcatalogs=os.path.expanduser('~/data/fels/'))
    '''

    assert len(args) == 4
    scene, sat, start_date, end_date = args
    
    # fix alternate args

    if isinstance(scene, tuple):
        assert len(scene) == 2
        scene = str(scene[0]).zfill(3) + str(scene[1]).zfill(3)

    landsats = {
            'L5': 'TM',
            'L7': 'ETM',
            'L8': 'OLI_TIRS'
            }
    if sat in landsats:
        sat = landsats[sat]
    
    if isinstance(end_date, datetime.date):
        end_date = end_date.strftime('%Y-%m-%d')
    if isinstance(start_date, datetime.date):
        start_date = start_date.strftime('%Y-%m-%d')

    # get defaults from argparse

    defaults = get_parser().parse_args([scene, sat, start_date, end_date])

    # overwrite with user-defined kwargs

    for k in kwargs:
        assert k in defaults, k

    options_dict = vars(defaults)
    options_dict.update(kwargs)
    options = argparse.Namespace(**options_dict)

    # call fels
    return _run_fels(options)


def _run_fels(options):
    '''
    Search the catalogs for matching images, download them (if list==False) and return the list of urls.
    '''

    LANDSAT_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-landsat/index.csv.gz'
    SENTINEL2_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-sentinel-2/index.csv.gz'

    # Run functions
    if options.sat == 'S2':
        sentinel2_metadata_file = download_metadata_file(SENTINEL2_METADATA_URL, options.outputcatalogs, 'Sentinel')
        url = query_sentinel2_catalogue(sentinel2_metadata_file, options.cloudcover, options.start_date, options.end_date, options.scene, options.latest)
        if not url:
            print("No image was found with the criteria you chose! Please review your parameters and try again.")
        else:
            print("Found {} files.".format(len(url)))
            if not options.list:
                valid_mask = []
                for i, u in enumerate(url):
                    print("Downloading {} of {}...".format(i+1, len(url)))
                    ok = get_sentinel2_image(u, options.output, options.overwrite, options.excludepartial, options.noinspire, options.reject_old)
                    if not ok:
                        print(f'Skipped {u}')
                    valid_mask.append(ok)
                url = [u for u,m in zip(url, valid_mask) if m]
    else:
        landsat_metadata_file = download_metadata_file(LANDSAT_METADATA_URL, options.outputcatalogs, 'Landsat')
        url = query_landsat_catalogue(landsat_metadata_file, options.cloudcover, options.start_date,
                                      options.end_date, options.scene[0:3], options.scene[3:6],
                                      options.sat, options.latest)
        if not url:
            print("No image was found with the criteria you chose! Please review your parameters and try again.")
        else:
            print("Found {} files.".format(len(url)))
            for i, u in enumerate(url):
                if not options.list:
                    print("Downloading {} of {}...".format(i+1, len(url)))
                    get_landsat_image(u, options.output, options.overwrite, options.sat)

    if options.dates:
        dirs = [u.split('/')[-1] for u in url]
        if options.sat == 'S2':
            datetimes = [safedir_to_datetime(d) for d in dirs]
            dates = [dt.dates() for dt in datetimes]
        else:
            dates = [landsatdir_to_date(d) for d in dirs]

        return dates

    else:
        return url

if __name__ == "__main__":
    main()
