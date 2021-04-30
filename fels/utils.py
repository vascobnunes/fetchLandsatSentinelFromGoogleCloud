from __future__ import absolute_import, division, print_function
import os
import shutil
import gzip
import requests
try:
    from urllib2 import urlopen
    from urllib2 import HTTPError
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen, HTTPError, URLError


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


def download_file(url, destination_filename):
    """Function to download files using pycurl lib"""
    with requests.get(url, stream=True) as r:
        with open(destination_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
