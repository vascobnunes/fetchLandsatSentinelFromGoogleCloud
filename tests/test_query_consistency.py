# -*- coding: utf-8 -*-
"""
Test that the python API and CLI return the same results for equivalent queries
"""
import json
import os
import ubelt as ub
import datetime
import fels
from shapely import geometry


def _run_consistency_test(sensor,
                          sensor_alias,
                          start_date,
                          end_date,
                          geojson_geom,
                          expected_urls,
                          expected_dates
                          ):
    outputcatalogs = os.path.expanduser('~/data/fels/')
    start_date_iso = start_date.isoformat()
    end_date_iso = end_date.isoformat()
    wkt_geometry = geometry.shape(geojson_geom).wkt
    geojson_geom_text = json.dumps(geojson_geom)
    cloudcover = 30

    # Test python invocation
    python_result1 = fels.run_fels(
        None, sensor, start_date_iso, end_date_iso, cloudcover=cloudcover,
        output='.', geometry=wkt_geometry, latest=True, list=True,
        outputcatalogs=outputcatalogs)

    # python with friendly aliases
    python_result2 = fels.run_fels(
        None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
        output='.', geometry=geojson_geom, latest=True, list=True,
        outputcatalogs=outputcatalogs)

    python_dates_result = fels.run_fels(
        None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
        output='.', geometry=geojson_geom, latest=True, dates=True,
        list=True, outputcatalogs=outputcatalogs)

    assert python_dates_result == expected_dates
    assert len(python_result1) == len(expected_urls), (
        'we expect {} results'.format(len(expected_urls)))
    assert python_result1 == python_result2

    fmtdict = dict(
        sensor=sensor, sensor_alias=sensor_alias,
        start_date_iso=start_date_iso, end_date_iso=end_date_iso,
        cloudcover=cloudcover, outputcatalogs=outputcatalogs)

    # Test CLI invocation
    fmtdict1 = fmtdict.copy()
    fmtdict1['geometry'] = wkt_geometry
    cli_result1 = ub.cmd(ub.paragraph(
        '''
        fels {sensor} {start_date_iso} {end_date_iso} -c {cloudcover} -o .
        -g '{geometry}' --latest --list --outputcatalogs {outputcatalogs}
        ''').format(**fmtdict1), verbose=3)

    # The last lines of the CLI output should be our expected results
    results = cli_result1['out'].strip().split('\n')[-(len(expected_urls) + 1):]
    assert not results[0].startswith('http')
    assert results[1:] == expected_urls

    fmtdict2 = fmtdict.copy()
    fmtdict2['geometry'] = geojson_geom_text
    cli_result2 = ub.cmd(ub.paragraph(
        '''
        fels {sensor_alias} {start_date_iso} {end_date_iso} -c {cloudcover} -o .
        -g '{geometry}' --latest --list --outputcatalogs {outputcatalogs}
        ''').format(**fmtdict2), verbose=3)
    # The last lines of the CLI output should be our expected results
    results = cli_result2['out'].strip().split('\n')[-(len(expected_urls) + 1):]
    assert not results[0].startswith('http')
    assert results[1:] == expected_urls


def test_query_consistency_l8():
    """
    Test an L8 invocation
    """
    sensor = 'OLI_TIRS'
    sensor_alias = 'L8'
    start_date = datetime.date(2015, 1, 1)
    end_date = datetime.date(2015, 6, 30)
    geojson_geom = {'type': 'Point', 'coordinates': [-105.2705, 40.015]}

    expected_urls = [
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150619_20170226_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150308_20170301_01_T1'
    ]
    expected_dates = [
        datetime.date(2015, 6, 19),
        datetime.date(2015, 3, 8)
    ]
    _run_consistency_test(sensor, sensor_alias, start_date, end_date,
                          geojson_geom, expected_urls, expected_dates)


def test_query_consistency_s2():
    """
    Test an S2 invocation
    """
    # Define variations of a test query and the results we expect from it
    sensor = 'S2'
    sensor_alias = 'S2'
    start_date = datetime.date(2018, 1, 1)
    end_date = datetime.date(2018, 6, 30)
    geojson_geom = {'type': 'Point', 'coordinates': [-105.2705, 40.015]}

    expected_urls = [
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180517T175051_N0206_R141_T13TDE_20180517T212632.SAFE',
    ]
    expected_dates = [
        datetime.date(2018, 5, 17)
    ]
    _run_consistency_test(sensor, sensor_alias, start_date, end_date,
                          geojson_geom, expected_urls, expected_dates)
