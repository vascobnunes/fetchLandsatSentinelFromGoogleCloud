# FeLS - Fetch Landsat & Sentinel Data from google cloud
Find and download Landsat and Sentinel-2 data from the public Google Cloud

The script downloads the index.csv file listing all available Landsat or Sentinel-2 tiles. 
Then searches the file for one scene that matches user parameters.
Once found, it downloads the image files.

Small demo video: https://youtu.be/8zCs0nxl-rU

Install:

`       pip install fels`

Usage examples:

 - UNIX:

`       python fetchFromGoogleCloud.py 203031 OLI_TIRS 2015-01-01 2015-06-30 -c 30 -o ~/LANDSAT --latest --outputcatalogs /tmp`

`       python fetchFromGoogleCloud.py 44UPU S2 2016-10-01 2016-12-31 -o ~/SENTINEL2 -l --outputcatalogs /tmp`

 - WINDOWS:

`       python fetchFromGoogleCloud.py 203031 OLI_TIRS 2015-01-01 2015-06-30 -c 30 -o %TEMP%\LANDSAT --latest --outputcatalogs %TEMP%\LANDSAT`

`       python fetchFromGoogleCloud.py 44UPU S2 2016-10-01 2016-12-31 -o %TEMP%\SENTINEL2 -l --outputcatalogs %TEMP%\SENTINEL2`

Options:

`         -h, --help            show this help message and exit`

`         -s SCENE, --scene=SCENE               TileID of scene (ex. 198030 for Landsat or 44UPU for Sentinel2)`

`         -d START_DATE, --start_date=START_DATE start date, fmt('2013-12-23')`

`         -f END_DATE, --end_date=END_DATE      end date, fmt('2013-12-23')`

`         -o OUTPUT,                             Where to download files`

`         -c CLOUDS, --cloudcover=CLOUDS        Set a limit to the cloud cover of the image`

`         -b BIRD, --sat=BIRD                   Which satellite are you looking for. Available options are: TM, ETM, OLI_TIRS, S2`

`         -l LIST,                              Just list the urls found, don't download`

`         -e EXCLUDEPARTIAL,                    Exclude partial tiles - only for Sentinel-2`

`         --latest LATEST,                      Choose the most recent image(s) that meet(s) the search criteria`

`         --overwrite,                          Overwrite files if existing locally`

`         --outputcatalogs=OUTPUTCATALOGS       Where to download metadata catalog files`

Run the script with -h switch for more help usage.

Compatible with python 2.7 and 3.x.

You can read more about the public google access to Landsat and Sentinel-2 data here: https://cloud.google.com/storage/docs/public-datasets/

Contributors (THANK YOU!):
 - https://github.com/framioco
 - https://github.com/bendv
