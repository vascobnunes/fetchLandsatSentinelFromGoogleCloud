import argparse
import csv
import datetime
import os
import subprocess
import sys
import tempfile


def downloadMetadataFile(url, outputdir, program):
    # This function downloads and unzips the catalogue files
    theZippedFile = os.path.join(outputdir, 'index_' + program + '.csv.gz')
    theFile = os.path.join(outputdir, 'index_' + program + '.csv')
    if not os.path.isfile(theZippedFile):
        print("Downloading Metadata file...")
        # download the file
        try:
            subprocess.call('curl ' + url + ' -o ' + theZippedFile, shell=True)
        except:
            print("Some error occurred when trying to download the Metadata file!")
    if not os.path.isfile(theFile):
        print("Unzipping Metadata file...")
        # unzip the file
        try:
            if sys.platform.startswith('win'):  # W32
                subprocess.call('7z e -so ' + theZippedFile + ' > ' + theFile, shell=True)  # W32
            elif sys.platform.startswith('linux'):  # UNIX
                subprocess.call(['gunzip', theZippedFile])
        except:
            print("Some error occurred when trying to unzip the Metadata file!")
    return theFile


def findLandsatInCollectionMetadata(collection_file, cc_limit, date_start, date_end, wr2path, wr2row, sensor):
    # This function queries the Landsat index catalogue and retrieves an url for the best image found
    print("Searching for images in catalog...")
    cloudcoverlist = []
    cc_values = []
    with open(collection_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            year_acq = int(row['DATE_ACQUIRED'][0:4])
            month_acq = int(row['DATE_ACQUIRED'][5:7])
            day_acq = int(row['DATE_ACQUIRED'][8:10])
            acqdate = datetime.datetime(year_acq, month_acq, day_acq)
            if int(row['WRS_PATH']) == int(wr2path) and int(row['WRS_ROW']) == int(wr2row) and row['SENSOR_ID'] == sensor and float(row['CLOUD_COVER']) <= cc_limit and date_start < acqdate < date_end:
                cloudcoverlist.append(row['CLOUD_COVER'] + '--' + row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))
            else:
                url = ''
    for i in cloudcoverlist:
        if float(i.split('--')[0]) == min(cc_values):
            url = i.split('--')[1]
    if url != '':
        url = 'http://storage.googleapis.com/' + url.replace('gs://', '')
    return url


def findS2InCollectionMetadata(collection_file, cc_limit, date_start, date_end, tile):
    # This function queries the sentinel2 index catalogue and retrieves an url for the best image found
    print("Searching for images in catalog...")
    cloudcoverlist = []
    cc_values = []
    with open(collection_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            year_acq = int(row['SENSING_TIME'][0:4])
            month_acq = int(row['SENSING_TIME'][5:7])
            day_acq = int(row['SENSING_TIME'][8:10])
            acqdate = datetime.datetime(year_acq, month_acq, day_acq)
            if row['MGRS_TILE'] == tile and float(row['CLOUD_COVER']) <= cc_limit and date_start < acqdate < date_end:
                cloudcoverlist.append(row['CLOUD_COVER'] + '--' + row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))
            else:
                url = ''
    for i in cloudcoverlist:
        if float(i.split('--')[0]) == min(cc_values):
            url = i.split('--')[1]
    if url != '':
        url = 'http://storage.googleapis.com/' + url.replace('gs://', '')
    return url


def downloadLandsatFromGoogleCloud(url, outputdir):
    # this function downloads the Landsat image files
    img = url.split("/")[len(url.split("/")) - 1]
    possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF', 'B6.TIF',
                      'B6_VCID_1.TIF', 'B6_VCID_2.TIF', 'B7.TIF', 'B8.TIF', 'B9.TIF', 'BQA.TIF', 'MTL.txt']
    for bands in possible_bands:
        completeUrl = url + "/" + img + "_" + bands
        destinationDir = os.path.join(outputdir, img)
        if not os.path.exists(destinationDir):
            os.makedirs(destinationDir)
        destinationFile = os.path.join(destinationDir, img + "_" + bands)
        try:
            subprocess.call('curl ' + completeUrl + ' -o ' + destinationFile, shell=True)
        except:
            os.remove(destinationFile)
            continue


def downloadS2FromGoogleCloud(url, outputdir):
    # this function collects the entire dir structure of the image files from
    # the manifest.safe file and builds the same structure in the output
    # location
    img = url.split("/")[len(url.split("/")) - 1]
    manifest = url + "/manifest.safe"
    destinationDir = os.path.join(outputdir, img)
    if not os.path.exists(destinationDir):
        os.makedirs(destinationDir)
    destinationManifestFile = os.path.join(destinationDir, "manifest.safe")
    subprocess.call('curl ' + manifest + ' -o ' + destinationManifestFile, shell=True)
    readManifestFile = open(destinationManifestFile)
    tempList = readManifestFile.read().split()
    for l in tempList:
        if l.find("href") >= 0:
            completeUrl = l[7:l.find("><") - 2]
            # building dir structure
            dirs = completeUrl.split("/")
            for d in range(0, len(dirs) - 1):
                if dirs[d] != '':
                    destinationDir = os.path.join(destinationDir, dirs[d])
                    try:
                        os.makedirs(destinationDir)
                    except:
                        continue
            destinationDir = os.path.join(outputdir, img)
            # downloading files
            destinationFile = destinationDir + completeUrl
            try:
                subprocess.call('curl ' + url + completeUrl + ' -o ' + destinationFile, shell=True)
            except:
                continue


def main():
    parser = argparse.ArgumentParser(description="Find and download Landsat and Sentinel-2 data from the public Google Cloud")
    parser.add_argument("scene", help="WRS2 coordinates of scene (ex 198030)")
    parser.add_argument("sat", help="Which satellite are you looking for", choices=['TM', 'ETM', 'OLI_TIRS', 'S2'], default='OLI_TIRS')
    parser.add_argument("start_date", help="Start date, in format YYYY-MM-DD", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("end_date", help="End date, in format YYYY-MM-DD", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("-c", "--cloudcover", type=float, help="Set a limit to the cloud cover of the image", default=100)
    parser.add_argument("--output", help="Where to download files", default=tempfile.gettempdir())
    parser.add_argument("--outputcatalogs", help="Where to download metadata catalog files", default=tempfile.gettempdir())
    options = parser.parse_args()

    LANDSAT_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-landsat/index.csv.gz'
    SENTINEL2_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-sentinel-2/index.csv.gz'

    # Run functions
    if options.sat == 'S2':
        sentinel2_metadata_file = downloadMetadataFile(SENTINEL2_METADATA_URL, options.outputcatalogs, 'Sentinel')
        url = findS2InCollectionMetadata(sentinel2_metadata_file, options.cloudcover, options.start_date, options.end_date, options.scene)
        if url == '':
            print("No image was found with the criteria you chose! Please review your parameters and try again.")
        else:
            downloadS2FromGoogleCloud(url, options.output)
    else:
        landsat_metadata_file = downloadMetadataFile(LANDSAT_METADATA_URL, options.outputcatalogs, 'Landsat')
        url = findLandsatInCollectionMetadata(landsat_metadata_file, options.cloudcover,
                                              options.start_date, options.end_date, options.scene[0:3], options.scene[3:6], options.sat)
        if url == '':
            print("No image was found with the criteria you chose! Please review your parameters and try again.")
        else:
            downloadLandsatFromGoogleCloud(url, options.output)

if __name__ == "__main__":
    main()
