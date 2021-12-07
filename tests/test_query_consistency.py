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
    outputcatalogs = FELS_DEFAULT_OUTPUTDIR

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

    latest = False

    # Test python invocation
    api_urls1 = fels.run_fels(
        None, sensor, start_date_iso, end_date_iso, cloudcover=cloudcover,
        outputcatalogs=outputcatalogs,
        output='.', geometry=wkt_geometry, latest=latest, list=True)
    api_url_results['1'] = api_urls1

    # python with friendly aliases
    api_urls2 = fels.run_fels(
        None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
        outputcatalogs=outputcatalogs,
        output='.', geometry=geojson_geom, latest=latest, list=True)
    api_url_results['2'] = api_urls2

    # Using CSV is very slow, consider disabling this test
    TEST_CSV = False
    if TEST_CSV:
        api_urls3 = fels.run_fels(
            None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
            outputcatalogs=outputcatalogs, use_csv=True,
            output='.', geometry=geojson_geom, latest=latest, list=True)
        api_url_results['3'] = api_urls3

    api_dates = fels.run_fels(
        None, sensor_alias, start_date, end_date, cloudcover=cloudcover,
        outputcatalogs=outputcatalogs,
        output='.', geometry=geojson_geom, latest=latest, dates=True,
        list=True)

    fmtdict = dict(
        sensor=sensor, sensor_alias=sensor_alias,
        start_date_iso=start_date_iso, end_date_iso=end_date_iso,
        outputcatalogs=outputcatalogs,
        cloudcover=cloudcover)
    if latest:
        fmtdict['latestflag'] = '--latest'
    else:
        fmtdict['latestflag'] = ''

    # Test CLI invocation
    fmtdict1 = fmtdict.copy()
    fmtdict1['geometry'] = wkt_geometry
    cli_info1 = ub.cmd(ub.paragraph(
        '''
        fels {sensor} {start_date_iso} {end_date_iso} -c {cloudcover} -o .
        -g '{geometry}' {latestflag} --list --outputcatalogs {outputcatalogs}
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
        -g '{geometry}' {latestflag} --list --outputcatalogs {outputcatalogs}
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

    print('expected_dates = {}'.format(ub.repr2(expected_dates, nl=1)))
    print('api_dates = {}'.format(ub.repr2(api_dates, nl=1)))
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
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150619_20170226_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150331_20170228_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150126_20170302_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150315_20180131_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150603_20170226_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/034/032/LC08_L1TP_034032_20150227_20170301_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150119_20180131_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150628_20170301_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150324_20170301_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150308_20170301_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150511_20170301_01_T1',
        'http://storage.googleapis.com/gcp-public-data-landsat/LC08/01/033/032/LC08_L1TP_033032_20150527_20170301_01_T1',
    ]
    expected_dates = [
        datetime.date(2015, 6, 19),
        datetime.date(2015, 3, 31),
        datetime.date(2015, 1, 26),
        datetime.date(2015, 3, 15),
        datetime.date(2015, 6, 3),
        datetime.date(2015, 2, 27),
        datetime.date(2015, 1, 19),
        datetime.date(2015, 6, 28),
        datetime.date(2015, 3, 24),
        datetime.date(2015, 3, 8),
        datetime.date(2015, 5, 11),
        datetime.date(2015, 5, 27),
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
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180213T174431_N0206_R098_T13TDE_20180213T223941.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180114T174701_N0206_R098_T13TDE_20180114T194428.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180104T175251_N0206_R098_T13TDE_20180104T191930.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180504T173911_N0206_R098_T13TDE_20180504T212111.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180613T173901_N0206_R098_T13TDE_20180613T224243.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180628T173859_N0206_R098_T13TDE_20180628T212011.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180626T174911_N0206_R141_T13TDE_20180626T212815.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180524T174051_N0206_R098_T13TDE_20180524T225950.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180621T174909_N0206_R141_T13TDE_20180621T212007.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180414T173901_N0206_R098_T13TDE_20180414T212337.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180129T174559_N0206_R098_T13TDE_20180129T194109.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180601T174909_N0206_R141_T13TDE_20180601T212135.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180611T174909_N0206_R141_T13TDE_20180611T224909.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180308T175151_N0206_R141_T13TDE_20180308T213017.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180117T180241_N0206_R141_T13TDE_20180117T193120.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180223T174321_N0206_R098_T13TDE_20180223T212125.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180422T174909_N0206_R141_T13TDE_20180422T210525.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180228T174239_N0206_R098_T13TDE_20180228T211354.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180517T175051_N0206_R141_T13TDE_20180517T212632.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180109T174709_N0206_R098_T13TDE_20180109T193934.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180611T174909_N0206_R141_T13TDE_20180611T213053.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180303T175229_N0206_R141_T13TDE_20180303T195213.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180313T175109_N0206_R141_T13TDE_20180313T212428.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180315T174101_N0206_R098_T13TDE_20180315T211702.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180623T173901_N0206_R098_T13TDE_20180623T224306.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180427T174911_N0206_R141_T13TDE_20180427T225312.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180608T173859_N0206_R098_T13TDE_20180608T211610.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2A_MSIL1C_20180325T173951_N0206_R098_T13TDE_20180326T003450.SAFE',
        'http://storage.googleapis.com/gcp-public-data-sentinel-2/tiles/13/T/DE/S2B_MSIL1C_20180618T173859_N0206_R098_T13TDE_20180618T210824.SAFE',
    ]
    expected_dates = [
        datetime.date(2018, 2, 13),
        datetime.date(2018, 1, 14),
        datetime.date(2018, 1, 4),
        datetime.date(2018, 5, 4),
        datetime.date(2018, 6, 13),
        datetime.date(2018, 6, 28),
        datetime.date(2018, 6, 26),
        datetime.date(2018, 5, 24),
        datetime.date(2018, 6, 21),
        datetime.date(2018, 4, 14),
        datetime.date(2018, 1, 29),
        datetime.date(2018, 6, 1),
        datetime.date(2018, 6, 11),
        datetime.date(2018, 3, 8),
        datetime.date(2018, 1, 17),
        datetime.date(2018, 2, 23),
        datetime.date(2018, 4, 22),
        datetime.date(2018, 2, 28),
        datetime.date(2018, 5, 17),
        datetime.date(2018, 1, 9),
        datetime.date(2018, 6, 11),
        datetime.date(2018, 3, 3),
        datetime.date(2018, 3, 13),
        datetime.date(2018, 3, 15),
        datetime.date(2018, 6, 23),
        datetime.date(2018, 4, 27),
        datetime.date(2018, 6, 8),
        datetime.date(2018, 3, 25),
        datetime.date(2018, 6, 18),
    ]
    _run_consistency_test(sensor, sensor_alias, start_date, end_date,
                          geojson_geom, expected_urls, expected_dates)
