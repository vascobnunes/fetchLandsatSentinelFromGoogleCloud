# FeLS - Fetch Landsat & Sentinel Data from google cloud
Find and download Landsat and Sentinel-2 data from the public Google Cloud

The script downloads the index.csv file listing all available Landsat or Sentinel-2 tiles. 
Then searches the file for one scene that matches user parameters.
Once found, it downloads the image files.

Usage example:

 - UNIX:

`       python fetchFromGoogleCloud.py 203031 OLI_TIRS 2015-01-01 2015-06-30 -c 30 --output ~/LANDSAT --outputcatalogs /tmp`

`       python fetchFromGoogleCloud.py 44UPU S2 2016-10-01 2016-12-31 --output ~/SENTINEL2 --outputcatalogs /tmp`

 - WINDOWS:

`       python fetchFromGoogleCloud.py 203031 OLI_TIRS 2015-01-01 2015-06-30 -c 30 --output %TEMP%\LANDSAT --outputcatalogs %TEMP%\LANDSAT`

`       python fetchFromGoogleCloud.py 44UPU S2 2016-10-01 2016-12-31 --output %TEMP%\SENTINEL2 --outputcatalogs %TEMP%\SENTINEL2`

Options:

`         -h, --help            show this help message and exit`

`         -s SCENE, --scene=SCENE               TileID of scene (ex. 198030 for Landsat or 44UPU for Sentinel2)`

`         -d START_DATE, --start_date=START_DATE start date, fmt('2013-12-23')`

`         -f END_DATE, --end_date=END_DATE      end date, fmt('2013-12-23')`

`         -c CLOUDS, --cloudcover=CLOUDS        Set a limit to the cloud cover of the image`

`         -b BIRD, --sat=BIRD                   Which satellite are you looking for. Available options are: TM, ETM, OLI_TIRS, S2`

`         --output=OUTPUT                       Where to download files`

`         --outputcatalogs=OUTPUTCATALOGS       Where to download metadata catalog files`

Run the script with -h switch for more help usage.

Compatible with python 2.7 and 3.x.

You can read more about the public google access to Landsat and Sentinel-2 data here: https://cloud.google.com/storage/docs/public-datasets/
