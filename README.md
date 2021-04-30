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

You can also use GeoJSON geometry to perform a search:

```
fels OLI_TIRS 2015-01-01 2015-06-30 -g '{"type":"Polygon","coordinates":[[[-122.71,37.54],[-122.71,37.90],[-121.99,37.90],[-121.99,37.54],[-122.71,37.54]]]}' -c 30 -o ~/LANDSAT --latest --outputcatalogs /tmp
```

or you can use Well Known Text (WKT) geometry:

```
fels OLI_TIRS 2015-01-01 2015-06-30 -g 'POINT (-105.2705 40.015)' -c 30 -o ~/LANDSAT --latest --outputcatalogs /tmp
```


### WINDOWS

```
fels OLI_TIRS 2015-01-01 2015-06-30 -s 203031 -c 30 -o %TEMP%\LANDSAT --latest --outputcatalogs %TEMP%\LANDSAT
```

```
fels S2 2016-10-01 2016-12-31 -s 44UPU -o %TEMP%\SENTINEL2 -l --outputcatalogs %TEMP%\SENTINEL2
```

### PYTHON


You can use the Python entrypoint `fels.run_fels` in the same way as the `fels` executable:

```python
# these commands are equivalent

# CLI
import os
os.system(('fels OLI_TIRS 2015-01-01 2015-06-30 -c 30 -o . -g "POINT (-105.2705 40.015)"'
           '--latest --outputcatalogs ~/data/fels/'))

os.system(('fels OLI_TIRS 2015-01-01 2015-06-30 -c 30 -o . -g \'{"type":"Point","coordinates":[-105.2705, 40.015]}\''
           '--latest --outputcatalogs ~/data/fels/'))

# python
from fels import run_fels
urls = run_fels(None, 'OLI_TIRS', '2015-01-01', '2015-06-30', cloudcover=30, output='.',
                geometry='POINT (-105.2705 40.015)',
                latest=True, outputcatalogs=os.path.expanduser('~/data/fels/'))
print(urls)

# python with friendly aliases
from datetime import date
urls = run_fels(None, 'L8', date(2015, 1, 1), date(2015, 6, 30), cloudcover=30, output='.',
                geometry={'type': 'Point', 'coordinates': [-105.2705, 40.015]},
                latest=True, outputcatalogs=os.path.expanduser('~/data/fels/'))
print(urls)
```

and import other useful utilities like:
```python
fels.safedir_to_datetime
fels.landsatdir_to_date
fels.convert_wkt_to_scene
```

## Usage

Run the script with `-h` switch for parameters:

```
usage: fels [-h] [-g GEOMETRY] [-c CLOUDCOVER] [-o OUTPUT] [-e EXCLUDEPARTIAL] [--latest]
            [--noinspire] [--outputcatalogs OUTPUTCATALOGS] [--overwrite] [-l] [-d] [-r]
            [scene] {TM,ETM,OLI_TIRS,S2} start_date end_date

Find and download Landsat and Sentinel-2 data from the public Google Cloud

positional arguments:
  scene                 WRS2 coordinates for Landsat (ex 198030) or MGRS for S2 (ex 52SDG). Mutually
                        exclusive with --geometry
  {TM,ETM,OLI_TIRS,S2}  Which satellite are you looking for
  start_date            Start date, in format YYYY-MM-DD. Left-exclusive.
  end_date              End date, in format YYYY-MM-DD. Right-exclusive.

optional arguments:
  -h, --help            show this help message and exit
  -g GEOMETRY, --geometry GEOMETRY
                        Geometry to run search. Must be valid GeoJSON `geometry` or Well Known Text (WKT).
                        This is only used if --scene is blank.
  -i, --includeoverlap  If -g is used, include scenes that overlap the geometry but do not
                        completely contain it
  -c CLOUDCOVER, --cloudcover CLOUDCOVER
                        Set a limit to the cloud cover of the image
  -o OUTPUT, --output OUTPUT
                        Where to download files
  -e EXCLUDEPARTIAL, --excludepartial EXCLUDEPARTIAL
                        Exclude partial tiles - only for Sentinel-2
  --latest              Limit to the latest scene
  --noinspire           Do not rename output image folder to the title collected from the inspire.xml file
                        (only for S2 datasets)
  --outputcatalogs OUTPUTCATALOGS
                        Where to download metadata catalog files
  --overwrite           Overwrite files if existing locally
  -l, --list            List available download urls and exit without downloading
  -d, --dates           List or return dates instead of download urls
  -r, --reject_old      For S2, skip redundant old-format (before Nov 2016) images

```

You can read more about the public google access to Landsat and Sentinel-2 data here: https://cloud.google.com/storage/docs/public-datasets/

Contributors (THANK YOU!):
 - https://github.com/framioco
 - https://github.com/bendv
 - https://github.com/GreatEmerald
