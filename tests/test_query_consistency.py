# -*- coding: utf-8 -*-
"""
Test that the python API and CLI return the same results for equivalent queries

CommandLine:
    pytest tests/test_query_consistency.py -s --verbose
"""
import json
import ubelt as ub
import datetime
import fels
from shapely import geometry
import ubelt


def _run_consistency_test(sensor,
                          sensor_alias,
                          start_date,
                          end_date,
                          geojson_geom,
                          expected_urls,
                          expected_dates
                          ):
    from fels.utils import FELS_DEFAULT_OUTPUTDIR
    outputcatalogs = FELS_DEFAULT_OUTPUTDIR + '-3'

    start_date_iso = start_date.isoformat()
    end_date_iso = end_date.isoformat()
    wkt_geometry = geometry.shape(geojson_geom).wkt
    geojson_geom_text = json.dumps(geojson_geom)
    cloudcover = 30

    # Store results from different variations on the same underlying call
    api_url_results = {}
    cli_url_results = {}
    # used to verify there are no extra urls in the cli results
    cli_nonurl_results = {}

    # Test python invocation
    api_urls1 = fels.run_fels(
        None, sensor, start_date_iso, end_date_iso, cloudcover=cloudcover,
        outputcatalogs=outputcatalogs,
        output='.', geometry=wkt_geometry, latest=True, list=True)
    api_url_results['1'] = api_urls1

    # python with friendly aliases
    api_urls2 = fels.run_fels(
        None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
        outputcatalogs=outputcatalogs,
        output='.', geometry=geojson_geom, latest=True, list=True)
    api_url_results['2'] = api_urls2

    # Using CSV is very slow, consider disabling this test
    TEST_CSV = False
    if TEST_CSV:
        api_urls3 = fels.run_fels(
            None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
            outputcatalogs=outputcatalogs, use_csv=True,
            output='.', geometry=geojson_geom, latest=True, list=True)
        api_url_results['3'] = api_urls3

    api_dates = fels.run_fels(
        None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
        outputcatalogs=outputcatalogs,
        output='.', geometry=geojson_geom, latest=True, dates=True,
        list=True)

    fmtdict = dict(
        sensor=sensor, sensor_alias=sensor_alias,
        start_date_iso=start_date_iso, end_date_iso=end_date_iso,
        outputcatalogs=outputcatalogs,
        cloudcover=cloudcover)

    # Test CLI invocation
    fmtdict1 = fmtdict.copy()
    fmtdict1['geometry'] = wkt_geometry
    cli_info1 = ub.cmd(ub.paragraph(
        '''
        fels {sensor} {start_date_iso} {end_date_iso} -c {cloudcover} -o .
        -g '{geometry}' --latest --list --outputcatalogs {outputcatalogs}
        ''').format(**fmtdict1), verbose=3)
    # The last lines of the CLI output should be our expected results
    cli_tail1 = cli_info1['out'].strip().split('\n')[-(len(expected_urls) + 1):]
    cli_nonurl_results['1'] = cli_tail1[0]
    cli_url_results['1'] = cli_tail1[1:]

    fmtdict2 = fmtdict.copy()
    fmtdict2['geometry'] = geojson_geom_text
    cli_info2 = ub.cmd(ub.paragraph(
        '''
        fels {sensor_alias} {start_date_iso} {end_date_iso} -c {cloudcover} -o .
        -g '{geometry}' --latest --list --outputcatalogs {outputcatalogs}
        ''').format(**fmtdict2), verbose=3)
    # The last lines of the CLI output should be our expected results
    cli_tail2 = cli_info2['out'].strip().split('\n')[-(len(expected_urls) + 1):]
    cli_nonurl_results['2'] = cli_tail2[0]
    cli_url_results['2'] = cli_tail2[1:]

    conditions = {
        'dates should match': api_dates == expected_dates,
    }
    for key, value in api_url_results.items():
        text = 'api-v{} urls should match'.format(key)
        conditions[text] = (value == expected_urls)

    for key, value in cli_url_results.items():
        text = 'cli-v{} urls should match'.format(key)
        conditions[text] = (value == expected_urls)

    for key, value in cli_nonurl_results.items():
        text = 'cli-v{} should not have more than have {} urls'.format(key, len(expected_urls))
        conditions[text] = (not value.startswith('http'))

    print('expected_dates = {!r}'.format(expected_dates))
    print('api_dates      = {!r}'.format(api_dates))
    print('expected_urls = {}'.format(ub.repr2(expected_urls, nl=1)))
    print('api_url_results = {}'.format(ub.repr2(api_url_results, nl=2)))
    print('cli_url_results = {}'.format(ub.repr2(cli_url_results, nl=2)))
    failed_conditions = [k for k, v in conditions.items() if not v]
    if failed_conditions:
        print('conditions = {}'.format(ub.repr2(conditions, nl=1)))
        print('failed_conditions = {!r}'.format(failed_conditions))
        print('cli_nonurl_results = {}'.format(ub.repr2(cli_nonurl_results, nl=2)))
        raise AssertionError('Test conditions failed: {}'.format(failed_conditions))


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
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150603_20170226_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150527_20170301_01_T1'
    ]
    expected_dates = [
        datetime.date(2015, 6, 3),
        datetime.date(2015, 5, 27)
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
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180104T175251_N0206_R098_T13TDE_20180104T191930.SAFE',
    ]
    expected_dates = [
        datetime.date(2018, 1, 4)
    ]
    _run_consistency_test(sensor, sensor_alias, start_date, end_date,
                          geojson_geom, expected_urls, expected_dates)
