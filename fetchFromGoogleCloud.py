import argparse
import csv
import datetime
import os
import subprocess
import sys
import tempfile


def downloadMetadataFile(url, outputdir, program, verbose=False):
    # This function downloads and unzips the catalogue files
    theZippedFile = os.path.join(outputdir, 'index_' + program + '.csv.gz')
    theFile = os.path.join(outputdir, 'index_' + program + '.csv')
    if not os.path.isfile(theZippedFile):
        print("Downloading Metadata file...")
        # download the file
        try:
            if verbose:
                subprocess.call('curl ' + url + ' -o ' + theZippedFile, shell=True)
            else:
                subprocess.call('curl ' + url + ' -o ' + theZippedFile, shell=True, stdout=open(os.devnull, 'wb'))
        except:
            print("Some error occurred when trying to download the Metadata file!")
    if not os.path.isfile(theFile):
        print("Unzipping Metadata file...")
        # unzip the file
        try:
            if sys.platform.startswith('win'):  # W32
                subprocess.call('7z e -so ' + theZippedFile + ' > ' + theFile, shell=True)  # W32
            else:  # UNIX (including OSX!)
                subprocess.call(['gunzip', theZippedFile])
        except:
            print("Some error occurred when trying to unzip the Metadata file!")
    return theFile


def findLandsatInCollectionMetadata(collection_file, cc_limit, date_start, date_end, wr2path, wr2row, sensor, latest = False):
    # This function queries the Landsat index catalogue and retrieves urls for the best images found
        
    print("Searching for Landsat-{0} images in catalog...".format(sensor))
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
            if int(row['WRS_PATH']) == int(wr2path) and int(row['WRS_ROW']) == int(wr2row) and row['SENSOR_ID'] == sensor and float(row['CLOUD_COVER']) <= cc_limit and date_start < acqdate < date_end:
                all_urls.append(row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))
                all_acqdates.append(acqdate)

    # sort url list by increasing cc_values and acqdate
    cc_values = sorted(cc_values)
    all_acqdates = sorted(all_acqdates, reverse=True)		
    all_urls = [x for (y, z, x) in sorted(zip(cc_values,all_acqdates, all_urls))]

    # if latest is True, take the last element of this sorted list
    if latest and (len(all_urls) > 0):
        url = [ 'http://storage.googleapis.com/' + all_urls[0].replace('gs://', '') ]
    else:
        url = []
        for i, u in enumerate(all_urls):
            url.append('http://storage.googleapis.com/' + u.replace('gs://', ''))
    
    return url


def findS2InCollectionMetadata(collection_file, cc_limit, date_start, date_end, tile, latest = False):
    # This function queries the sentinel2 index catalogue and retrieves an url for the best image found
        
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
            if row['MGRS_TILE'] == tile and float(row['CLOUD_COVER']) <= cc_limit and date_start < acqdate < date_end:
                all_urls.append(row['BASE_URL'])
                cc_values.append(float(row['CLOUD_COVER']))			
                all_acqdates.append(acqdate)
    
    # sort url list by increasing cc_values and acqdate
    cc_values = sorted(cc_values)
    all_acqdates = sorted(all_acqdates, reverse=True)	
    all_urls = [x for (y, z, x) in sorted(zip(cc_values, all_acqdates, all_urls))]

    if latest and (len(all_urls) > 0):
        url = [ 'http://storage.googleapis.com/' + all_urls[0].replace('gs://', '') ]
    else:
        url = []
        for i, u in enumerate(all_urls):
            url.append('http://storage.googleapis.com/' + u.replace('gs://', ''))
        
    return url


def downloadLandsatFromGoogleCloud(url, outputdir, verbose=False, overwrite=False):
    # this function downloads the Landsat image files
    img = url.split("/")[len(url.split("/")) - 1]
    possible_bands = ['B1.TIF', 'B2.TIF', 'B3.TIF', 'B4.TIF', 'B5.TIF', 'B6.TIF',
                      'B6_VCID_1.TIF', 'B6_VCID_2.TIF', 'B7.TIF', 'B8.TIF', 'B9.TIF', 'BQA.TIF', 'MTL.txt']
    for bands in possible_bands:
        completeUrl = url + "/" + img + "_" + bands
        destinationDir = os.path.join(outputdir, img)
        if not os.path.exists(destinationDir) or overwrite:
            os.makedirs(destinationDir)
            destinationFile = os.path.join(destinationDir, img + "_" + bands)
            try:
                if verbose:
                    subprocess.call('curl ' + completeUrl + ' -o ' + destinationFile, shell=True)
                else:
                    subprocess.call('curl ' + completeUrl + ' -o ' + destinationFile, shell=True, stdout=open(os.devnull, 'wb'))
            except:
                os.remove(destinationFile)
                continue


def downloadS2FromGoogleCloud(url, outputdir, verbose=False, overwrite=False):
    # this function collects the entire dir structure of the image files from
    # the manifest.safe file and builds the same structure in the output
    # location
    img = url.split("/")[len(url.split("/")) - 1]
    manifest = url + "/manifest.safe"
    destinationDir = os.path.join(outputdir, img)
    destinationManifestFile = os.path.join(destinationDir, "manifest.safe")
    if not os.path.exists(destinationDir) or overwrite:
        os.makedirs(destinationDir)
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
                    if verbose:
                        subprocess.call('curl ' + url + completeUrl + ' -o ' + destinationFile, shell=True) # shell should be False? see http://stackoverflow.com/questions/3172470/actual-meaning-of-shell-true-in-subprocess
                    else:
                        subprocess.call('curl ' + url + completeUrl + ' -o ' + destinationFile, shell=True, stdout=open(os.devnull, 'wb'))
                except:
                    continue


def main():
    parser = argparse.ArgumentParser(description="Find and download Landsat and Sentinel-2 data from the public Google Cloud")
    parser.add_argument("scene", help="WRS2 coordinates of scene (ex 198030)")
    parser.add_argument("sat", help="Which satellite are you looking for", choices=['TM', 'ETM', 'OLI_TIRS', 'S2'])
    parser.add_argument("start_date", help="Start date, in format YYYY-MM-DD", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("end_date", help="End date, in format YYYY-MM-DD", type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'))
    parser.add_argument("-c", "--cloudcover", type=float, help="Set a limit to the cloud cover of the image", default=100)
    parser.add_argument("-o", "--output", help="Where to download files", default=tempfile.gettempdir())
    parser.add_argument("-e", "--excludepartial", help="Exclude partial tiles - only for Sentinel-2", action="store_true", default=False)
    parser.add_argument("--latest", help="Limit to the latest scene", action="store_true", default=False)
    parser.add_argument("--outputcatalogs", help="Where to download metadata catalog files", default=None)
    parser.add_argument("--overwrite", help="Overwrite files if existing locally", default=False)
    parser.add_argument("-v", "--verbose", help="Show download status", action="store_true", default=False)
    parser.add_argument("-l", "--list", help="List available download url's and exit without downloading", action="store_true", default=False)
    options = parser.parse_args()
    
    if not options.outputcatalogs:
        options.outputcatalogs = options.output

    LANDSAT_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-landsat/index.csv.gz'
    SENTINEL2_METADATA_URL = 'http://storage.googleapis.com/gcp-public-data-sentinel-2/index.csv.gz'

    # Run functions
    if options.sat == 'S2':
        sentinel2_metadata_file = downloadMetadataFile(SENTINEL2_METADATA_URL, options.outputcatalogs, 'Sentinel', options.verbose)
        url = findS2InCollectionMetadata(sentinel2_metadata_file, options.cloudcover, options.start_date, options.end_date, options.scene, options.latest)
        if len(url) == 0:
            print("No image was found with the criteria you chose! Please review your parameters and try again.")
        else:
            print("Found {0} files.".format(len(url)))
            for i, u in enumerate(url):
                if not options.list:
                    print("\nDownloading {0} of {1}...".format(i+1, len(url)))
                    downloadS2FromGoogleCloud(u, options.output, options.verbose, options.overwrite)
                else:
                    print(url[i])
    else:
        landsat_metadata_file = downloadMetadataFile(LANDSAT_METADATA_URL, options.outputcatalogs, 'Landsat', options.verbose)
        url = findLandsatInCollectionMetadata(landsat_metadata_file, options.cloudcover,
                                              options.start_date, options.end_date, options.scene[0:3], options.scene[3:6], options.sat, options.latest)
        if len(url) == 0:
            print("No image was found with the criteria you chose! Please review your parameters and try again.")
        else:
            print("Found {0} files.".format(len(url)))
            for i, u in enumerate(url):
                if not options.list:
                    print("\nDownloading {0} of {1}...".format(i+1, len(url)))
                    downloadLandsatFromGoogleCloud(u, options.output, options.verbose, options.overwrite)
                else:
                    print(url[i])

if __name__ == "__main__":
    main()
