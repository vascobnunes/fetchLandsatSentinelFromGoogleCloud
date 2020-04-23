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
                          "B11.TIF", 'BQA.TIF', 'MTL.txt']
    elif sat == "ETM":
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B6_VCID_1.TIF', 'B6_VCID_2.TIF', 'B7.TIF',
                          'B8.TIF', 'B9.TIF', 'BQA.TIF', 'MTL.txt']
    else:
        possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF',
                          'B6.TIF', 'B6_VCID_1.TIF', 'B6_VCID_2.TIF', 'B7.TIF',
                          'B8.TIF', 'B9.TIF', 'BQA.TIF', 'MTL.txt']

    target_path = os.path.join(outputdir, img)

    if not os.path.isdir(target_path):
        os.makedirs(target_path)
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


def get_sentinel2_image(url, outputdir, overwrite=False, partial=False, noinspire=False):
    """
    Collect the entire dir structure of the image files from the
    manifest.safe file and build the same structure in the output
    location."""
    img = os.path.basename(url)
    target_path = os.path.join(outputdir, img)
    target_manifest = os.path.join(target_path, "manifest.safe")
    if not os.path.exists(target_path) or overwrite:
        os.makedirs(target_path)
        manifest_url = url + "/manifest.safe"
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
    if partial:
        tile_chk = check_full_tile(get_S2_image_bands(target_path, "B01"))
        if tile_chk == 'Partial':
            print("Removing partial tile image files...")
            shutil.rmtree(target_path)
    if not noinspire:
        inspire_file = os.path.join(target_path, "INSPIRE.xml")
        if os.path.isfile(inspire_file):
            inspire_path = get_S2_INSPIRE_title(inspire_file)
            if os.path.basename(target_path) != inspire_path:
                os.rename(target_path, inspire_path)
        else:
            print(f"File {inspire_file} could not be found.")


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


def main():
    parser = argparse.ArgumentParser(description="Find and download Landsat and Sentinel-2 data from the public Google Cloud")
    parser.add_argument("scene", help="WRS2 coordinates of scene (ex 198030)")
    parser.add_argument("sat", help="Which satellite are you looking for", choices=['TM', 'ETM', 'OLI_TIRS', 'S2'])
    parser.add_argument("start_date", help="Start date, in format YYYY-MM-DD", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("end_date", help="End date, in format YYYY-MM-DD", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("-c", "--cloudcover", type=float, help="Set a limit to the cloud cover of the image", default=100)
    parser.add_argument("-o", "--output", help="Where to download files", default=os.getcwd())
    parser.add_argument("-e", "--excludepartial", help="Exclude partial tiles - only for Sentinel-2", default=False)
    parser.add_argument("--latest", help="Limit to the latest scene", action="store_true", default=False)
    parser.add_argument("--noinspire", help="Do not rename output image folder to the title collected from the inspire.xml file (only for S2 datasets)", action="store_true", default=False)
    parser.add_argument("--outputcatalogs", help="Where to download metadata catalog files", default=None)
    parser.add_argument("--overwrite", help="Overwrite files if existing locally", action="store_true", default=False)
    parser.add_argument("-l", "--list", help="List available download url's and exit without downloading", action="store_true", default=False)
    options = parser.parse_args()

    if not options.outputcatalogs:
        options.outputcatalogs = options.output

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
            for i, u in enumerate(url):
                if not options.list:
                    print("Downloading {} of {}...".format(i+1, len(url)))
                    get_sentinel2_image(u, options.output, options.overwrite, options.excludepartial, options.noinspire)
                else:
                    print(url[i])
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
                else:
                    print(url[i])


if __name__ == "__main__":
    main()
