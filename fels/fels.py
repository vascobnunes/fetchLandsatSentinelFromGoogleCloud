"""
# FeLS - Fetch Landsat & Sentinel Data from Google Cloud
Find and download Landsat and Sentinel-2 data from the public Google Cloud

For more info see the
`FeLS GitHub Page <https://github.com/vascobnunes/fetchLandsatSentinelFromGoogleCloud>`_
"""
from __future__ import absolute_import, division, print_function
import argparse
import datetime
import geopandas
import json
import os
import pkg_resources
import shapely as shp
import ubelt
from fels.landsat import (
    get_landsat_image, query_landsat_catalogue, landsatdir_to_date,
    ensure_landsat_metadata)
from fels.sentinel2 import (
    query_sentinel2_catalogue, get_sentinel2_image, safedir_to_datetime,
    ensure_sentinel2_metadata)


@ubelt.memoize
def _memo_geopandas_read(path):
    return geopandas.read_file(path)


def convert_wkt_to_scene(sat, geometry, include_overlap, thresh=0.0):
    """
    Args:
        sat: 'S2', 'ETM', 'OLI_TIRS'
        geometry: WKT or GeoJSON string
        include_overlap: if True, use predicate 'intersects', else use predicate 'contains'
        thresh (float):
            the fraction of a tile that must intersect and overlap with a
            region.

    Returns:
        List of scenes containing the geometry

    Example:
        >>> sat = 'S2'
        >>> geometry = json.dumps({
        >>>     'type': 'Polygon', 'coordinates': [[
        >>>         [40.4700, -74.2700],
        >>>         [41.3100, -74.2700],
        >>>         [41.3100, -71.7500],
        >>>         [40.4700, -71.7500],
        >>>         [40.4700, -74.2700],
        >>>     ]]})
        >>> include_overlap = True
        >>> convert_wkt_to_scene('S2', geometry, include_overlap)
        >>> convert_wkt_to_scene('LC', geometry, include_overlap)
    """

    if sat == 'S2':
        path = pkg_resources.resource_filename(__name__, os.path.join('data', 'sentinel_2_index_shapefile.shp'))
    else:
        path = pkg_resources.resource_filename(__name__, os.path.join('data', 'WRS2_descending.shp'))

    if isinstance(geometry, dict):
        feat = shp.geometry.shape(geometry)
    elif isinstance(geometry, str):
        try:
            feat = shp.geometry.shape(json.loads(geometry))
        except json.JSONDecodeError:
            feat = shp.wkt.loads(geometry)
    else:
        raise TypeError(type(geometry))

    # gdf = geopandas.read_file(path)
    gdf = _memo_geopandas_read(path)

    if include_overlap:
        if thresh > 0:
            # Requires some minimum overlap
            overlap = gdf.geometry.intersection(feat).area / feat.area
            found = gdf[overlap > thresh]
        else:
            # Any amount of overlap is ok
            found = gdf[gdf.geometry.intersects(feat)]
    else:
        # This is the bottleneck when the downloaded data exists
        found = gdf[gdf.geometry.contains(feat)]

    if sat == 'S2':
        return found.Name.values
    else:
        return found.WRSPR.values


def normalize_satcode(sat):
    known = {'TM', 'ETM', 'OLI_TIRS', 'S2'}
    landsat_aliases = {
            'L5': 'TM',
            'L7': 'ETM',
            'L8': 'OLI_TIRS'
            }
    sat = sat.upper()
    sat = landsat_aliases.get(sat, sat)
    if sat not in known:
        print('warning sat = {!r}'.format(sat))
    return sat


def get_parser():
    import fels
    version_info = {'version': fels.__version__}

    parser = argparse.ArgumentParser(
        prog='fels', description=(
            'Fels {version} - '
            'Find and download Landsat and Sentinel-2 data from the public Google Cloud'
        ).format(**version_info)
    )
    parser.add_argument('scene', nargs='?', help='WRS2 coordinates for Landsat (ex 198030) or MGRS for S2 (ex 52SDG). Mutually exclusive with --geometry', default=None)
    parser.add_argument('sat', help='Which satellite are you looking for', choices=['TM', 'ETM', 'OLI_TIRS', 'S2'], type=normalize_satcode, default='S2')
    parser.add_argument('start_date', help='Start date, in format YYYY-MM-DD. Left-exclusive.', default=('2010-01-01'))
    parser.add_argument('end_date', help='End date, in format YYYY-MM-DD. Right-exclusive.', default=('2020-01-01'))
    parser.add_argument('-g', '--geometry', help='Geometry to run search. Must be valid GeoJSON `geometry` or Well Known Text (WKT). This is only used if --scene is blank.', default=None)
    parser.add_argument('-i', '--includeoverlap', help='If -g is used, include scenes that overlap the geometry but do not completely contain it', action='store_true', default=False)
    parser.add_argument('--minoverlap', help='If -i is not used, include scenes that overlap the geometry but do not completely contain it', action='store_true', default=False)
    parser.add_argument('-c', '--cloudcover', type=float, help='Set a limit to the cloud cover of the image', default=100)
    parser.add_argument('-o', '--output', help='Where to download files', default=os.getcwd())
    parser.add_argument('-e', '--excludepartial', help='Exclude partial tiles - only for Sentinel-2', default=False)
    parser.add_argument('--latest', help='Limit to the latest scene', action='store_true', default=False)
    parser.add_argument('--noinspire', help='Do not rename output image folder to the title collected from the inspire.xml file (only for S2 datasets)', action='store_true', default=False)
    parser.add_argument('--outputcatalogs', help='Where to download metadata catalog files', default=None)
    parser.add_argument('--overwrite', help='Overwrite files if existing locally', action='store_true', default=False)
    parser.add_argument('-l', '--list', help='List available download urls and exit without downloading', action='store_true', default=False)
    parser.add_argument('-d', '--dates', help='List or return dates instead of download urls', action='store_true', default=False)
    parser.add_argument('-r', '--reject_old', help='For S2, skip redundant old-format (before Nov 2016) images', action='store_true', default=False)
    parser.add_argument('-t', '--thresh', help='Only select intersecting areas where the fraction of the tile that overlaps with the spatial region is greater than this threshol', default=0.0)
    parser.add_argument('--version', action='version', version='{version}'.format(**version_info))
    return parser


def main():
    """
    CLI entrypoint.
    """
    options = get_parser().parse_args()

    if not options.outputcatalogs:
        options.outputcatalogs = options.output

    urls_or_dates = _run_fels(options)

    if options.list:
        for u in urls_or_dates:
            print(u)


def run_fels(*args, **kwargs):
    """
    Python entrypoint.

    See main() for arguments. Additional options not present in argparse include

    Args:
        scene: for Landsat, can pass in a (path,row) tuple such as (115,34)
        sat: 'L5', 'L7', 'L8' are aliases for 'TM', 'ETM', 'OLI_TIRS'
        start_date: can pass in a datetime.date directly
        end_date: can pass in a datetime.date directly
        geometry: can pass in GeoJSON as a dict instead of a string

    Other differences from CLI:
        Returns the list of urls. Therefore, will not print them with list=True.

    Example:
        >>> # downloading a tile from the CLI
        >>> os.system('fels 203031 OLI_TIRS 2015-01-01 2015-06-30 -c 30 -o . --latest --outputcatalogs ~/data/fels/')
        >>> # downloading the same tile in Python
        >>> from datetime import date
        >>> from fels import run_fels
        >>> run_fels((203,31), 'L8', date(2015, 1, 1), date(2015, 6, 30), cloudcover=30, output='.', latest=True, outputcatalogs=os.path.expanduser('~/data/fels/'))
    """
    # Parse args via
    options = _get_options(*args, **kwargs)
    # call fels
    return _run_fels(options)


def _get_options(*args, **kwargs):
    """
    Example:
        >>> from fels.fels import *  # NOQA
        >>> kwargs = {
        >>>     'scene': '23KPQ',
        >>>     'sat': 'S2',
        >>>     'start_date': '2010-07-28',
        >>>     'end_date': '2020-07-29',
        >>> }
        >>> options = _get_options(**kwargs)
        >>> print('options = {!r}'.format(options))
        >>> options = _get_options(geometry='POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))')
        >>> print('options.__dict__ = {}'.format(ubelt.repr2(options.__dict__, nl=1)))
    """
    args_names = ['scene', 'sat', 'start_date', 'end_date']
    for key, val in zip(args_names, args):
        if key not in kwargs:
            kwargs[key] = val
    sat = kwargs.get('sat', 'S2')
    scene = kwargs.get('scene', None)
    start_date = kwargs.get('start_date', '2010-01-01')
    end_date = kwargs.get('end_date', '2020-01-01')

    # TODO: can make this logic simpler

    # fix alternate args
    if scene is not None:
        if isinstance(scene, tuple):
            assert len(scene) == 2
            scene = str(scene[0]).zfill(3) + str(scene[1]).zfill(3)
        kwargs['scene'] = scene

    print('start_date = {!r}'.format(start_date))
    if isinstance(end_date, datetime.date):
        end_date = kwargs['end_date'] = datetime.date.isoformat(end_date)
    if isinstance(start_date, datetime.date):
        start_date = kwargs['start_date'] = datetime.date.isoformat(start_date)
    if isinstance(end_date, datetime.datetime):
        end_date = kwargs['end_date'] = datetime.datetime.isoformat(end_date)
    if isinstance(start_date, datetime.datetime):
        start_date = kwargs['start_date'] = datetime.datetime.isoformat(start_date)

    if 'geometry' in kwargs:
        if isinstance(kwargs['geometry'], dict):
            kwargs['geometry'] = json.dumps(kwargs['geometry'])

    # get defaults from argparse

    kwargs['sat'] = sat

    print('start_date = {!r}'.format(start_date))
    defaults = get_parser().parse_args([scene, sat, start_date, end_date])

    # overwrite with user-defined kwargs

    for k in kwargs:
        assert k in defaults, k

    options_dict = vars(defaults)
    options_dict.update(kwargs)
    options_dict['sat'] = normalize_satcode(options_dict['sat'])
    options = argparse.Namespace(**options_dict)
    return options


def _run_fels(options):
    """
    Search the catalogs for matching images, download them (if list==False) and return the list of urls.

    Example:
        >>> from fels.fels import *  # NOQA
        >>> kwargs = {
        >>>     'scene': '23KPQ',
        >>>     'sat': 'S2',
        >>>     'start_date': '2010-07-28',
        >>>     'end_date': '2020-07-29',
        >>>     'list': True,
        >>> }
        >>> options = _get_options(**kwargs)
        >>> _run_fels(options)

        >>> kwargs = {
        >>>     'sat': 'L8',
        >>>     'geometry': 'POLYGON((42 -72, 40 -72, 40 -70, 42 -70, 42 -72))',
        >>>     'list': True,
        >>> }
        >>> options = _get_options(**kwargs)
        >>> print('options.__dict__ = {}'.format(ubelt.repr2(options.__dict__, nl=1)))
        >>> _run_fels(options)
    """

    if not options.scene and options.geometry:
        scenes = convert_wkt_to_scene(options.sat, options.geometry, options.includeoverlap, options.thresh)
        if len(scenes) > 0:
            for i, s in enumerate(scenes):
                print(f'Converted WKT to scene: {s} [{i+1}/{len(scenes)}]')
        else:
            print('No matching scenes found for spatial region!')
    elif options.scene:
        scenes = [options.scene]

    # Run functions
    result = []
    for scene in scenes:

        if options.sat == 'S2':
            sentinel2_metadata_file = ensure_sentinel2_metadata(
                options.outputcatalogs)
            url = query_sentinel2_catalogue(
                sentinel2_metadata_file, options.cloudcover,
                options.start_date, options.end_date, scene, options.latest,
                use_sql=True)
            if not url:
                print('No image was found with the criteria you chose! Please review your parameters and try again.')
            else:
                print('Found {} files.'.format(len(url)))
                if not options.list:
                    valid_mask = []
                    for i, u in enumerate(url):
                        print('Downloading {} of {}...'.format(i + 1, len(url)))
                        ok = get_sentinel2_image(
                            u, options.output, options.overwrite,
                            options.excludepartial, options.noinspire,
                            options.reject_old)
                        if not ok:
                            print(f'Skipped {u}')
                        valid_mask.append(ok)
                    url = [u for u, m in zip(url, valid_mask) if m]
        else:
            landsat_metadata_file = ensure_landsat_metadata(
                options.outputcatalogs)

            url = query_landsat_catalogue(
                landsat_metadata_file, options.cloudcover, options.start_date,
                options.end_date, scene[0:3], scene[3:6], options.sat,
                options.latest, use_sql=True)

            if not url:
                print('No image was found with the criteria you chose! Please review your parameters and try again.')
            else:
                print('Found {} files.'.format(len(url)))
                for i, u in enumerate(url):
                    if not options.list:
                        print('Downloading {} of {}...'.format(i + 1, len(url)))
                        get_landsat_image(u, options.output, options.overwrite, options.sat)

        if options.dates:
            dirs = [u.split('/')[-1] for u in url]
            if options.sat == 'S2':
                datetimes = [safedir_to_datetime(d) for d in dirs]
                dates = [dt.dates() for dt in datetimes]
            else:
                dates = [landsatdir_to_date(d) for d in dirs]

            result.extend(dates)

        else:
            result.extend(url)

    return result


if __name__ == '__main__':
    main()
