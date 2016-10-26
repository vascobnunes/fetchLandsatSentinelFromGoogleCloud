# fetchLandsatSentinelFromGoogleCloud
Find and download Landsat and Sentinel-2 data from the public Google Cloud

(CURRENTLY ONLY WORKS FOR LANDSAT DATA)

The script downloads the index.csv file listing all available landsat tiles. 
Then searches the file for one scene that matches user parameters.
Once found, it downloads the files for the bands (pancromatic bands are skipped here).

Usage example:

`       python fetchFromGoogleCloud.py -s 203031 -b LC8 -d 20140101 -f 20140630 -c 30 --output /LANDSAT --outputcatalogs /tmp`

Options:

`         -h, --help            show this help message and exit`

`         -s SCENE, --scene=SCENE               WRS2 coordinates of scene (ex 198030)`

`         -d START_DATE, --start_date=START_DATE start date, fmt('20131223')`

`         -f END_DATE, --end_date=END_DATE      end date, fmt('20131223')`

`         -c CLOUDS, --cloudcover=CLOUDS        Set a limit to the cloud cover of the image`

`         -b BIRD, --sat=BIRD                   Which satellite are you looking for`

`         --output=OUTPUT                       Where to download files`

`         --outputcatalogs=OUTPUTCATALOGS       Where to download metadata catalog files`

You can read more about the public google access to Landsat and Sentinel-2 data here: https://cloud.google.com/storage/docs/public-datasets/
