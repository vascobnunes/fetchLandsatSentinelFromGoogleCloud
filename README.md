# FeLS - Fetch Landsat & Sentinel Data from Google Cloud
Find and download Landsat and Sentinel-2 data from the public Google Cloud

The script downloads the index.csv file listing all available Landsat or
Sentinel-2 tiles, then searches the file for one scene that matches user
parameters. Once found, it downloads the image files.

Small demo video: https://youtu.be/8zCs0nxl-rU

Developed with/for Python 2.7 and 3.3+
You may either install the package through pip:

```
pip install fels
```

or if using a conda environment, the following steps are recommended to create
and install dependencies:

```
conda create --name fetchLSGC python=3
```

Switch to the new environment (`source activate fetchLSGC` in Linux), and
install the gdal dependency from conda-forge

```
conda config --add channels conda-forge
conda install gdal
```

## Examples

### LINUX

```
fels OLI_TIRS 2015-01-01 2015-06-30 -s 203031 -c 30 -o ~/LANDSAT --latest --outputcatalogs /tmp
```

```
fels S2 2016-10-01 2016-12-31 -s 44UPU -o ~/SENTINEL2 -l --outputcatalogs /tmp
```

You can also use GeoJSON geomerty to perform a search:

```
fels OLI_TIRS 2015-01-01 2015-06-30 -g '{"type":"Polygon","coordinates":[[[-122.71,37.54],[-122.71,37.90],[-121.99,37.90],[-121.99,37.54],[-122.71,37.54]]]}' -c 30 -o ~/LANDSAT --latest --outputcatalogs /tmp

```

or you can use Well Known Text (WKT) geometry (note the addition `--wkt` flag):

```
fels OLI_TIRS 2015-01-01 2015-06-30 -g 'POINT (-105.2705 40.015)' --wkt -c 30 -o ~/LANDSAT --latest --outputcatalogs /tmp
```


### WINDOWS

```
fels OLI_TIRS 2015-01-01 2015-06-30 -s 203031 -c 30 -o %TEMP%\LANDSAT --latest --outputcatalogs %TEMP%\LANDSAT
```

```
fels S2 2016-10-01 2016-12-31 -s 44UPU -o %TEMP%\SENTINEL2 -l --outputcatalogs %TEMP%\SENTINEL2
```

## Usage

Run the script with `-h` switch for parameters:

```
usage: fels [-h] [-s SCENE] [-g GEOMETRY] [-c CLOUDCOVER] [-o OUTPUT] [-e EXCLUDEPARTIAL] [--latest] [--noinspire] [--outputcatalogs OUTPUTCATALOGS] [--overwrite] [-l]
            {TM,ETM,OLI_TIRS,S2} start_date end_date

Find and download Landsat and Sentinel-2 data from the public Google Cloud

positional arguments:
  {TM,ETM,OLI_TIRS,S2}  Which satellite are you looking for
  start_date            Start date, in format YYYY-MM-DD
  end_date              End date, in format YYYY-MM-DD

optional arguments:
  -h, --help            show this help message and exit
  -s SCENE, --scene SCENE
                        WRS2 coordinates of scene (ex 198030)
  -g GEOMETRY, --geometry GEOMETRY
                        Geometry to run search. Must be valid Well Known Text (WKT). This is only used if --scene is blank.
  -c CLOUDCOVER, --cloudcover CLOUDCOVER
                        Set a limit to the cloud cover of the image
  -o OUTPUT, --output OUTPUT
                        Where to download files
  -e EXCLUDEPARTIAL, --excludepartial EXCLUDEPARTIAL
                        Exclude partial tiles - only for Sentinel-2
  --latest              Limit to the latest scene
  --noinspire           Do not rename output image folder to the title collected from the inspire.xml file (only for S2 datasets)
  --outputcatalogs OUTPUTCATALOGS
                        Where to download metadata catalog files
  --overwrite           Overwrite files if existing locally
  -l, --list            List available download url's and exit without downloading
```

You can read more about the public google access to Landsat and Sentinel-2 data here: https://cloud.google.com/storage/docs/public-datasets/

Contributors (THANK YOU!):
 - https://github.com/framioco
 - https://github.com/bendv
 - https://github.com/GreatEmerald
