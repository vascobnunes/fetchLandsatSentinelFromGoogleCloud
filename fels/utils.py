# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import atexit
import gzip
import os
import shutil
import sqlite3
import ubelt


# Set the default output dir to the XDG or System cache dir
# i.e. ~/.cache/fels $XDG_DATA_HOME/fels %APPDATA%/fels or ~/Library/Caches/fels
FELS_DEFAULT_OUTPUTDIR = os.environ.get('FELS_DEFAULT_OUTPUTDIR', '')
if not FELS_DEFAULT_OUTPUTDIR:
    FELS_DEFAULT_OUTPUTDIR = ubelt.get_app_cache_dir('fels')

GLOBAL_SQLITE_CONNECTIONS = {}


def download_metadata_file(url, outputdir, program):
    """Download and unzip the catalogue files."""
    if outputdir is None:
        outputdir = FELS_DEFAULT_OUTPUTDIR
    zipped_index_path = os.path.join(outputdir, 'index_' + program + '.csv.gz')
    index_path = os.path.join(outputdir, 'index_' + program + '.csv')
    if not os.path.isfile(index_path):
        if not os.path.isfile(zipped_index_path):
            if not os.path.exists(os.path.dirname(zipped_index_path)):
                os.makedirs(os.path.dirname(zipped_index_path))
            print('Downloading Metadata file...')
            print('url = {!r}'.format(url))
            print('outputdir = {!r}'.format(outputdir))
            ubelt.download(url, fpath=zipped_index_path, chunksize=int(2 ** 22))
        print('Unzipping Metadata file...')
        with gzip.open(zipped_index_path) as gzip_index, open(index_path, 'wb') as f:
            shutil.copyfileobj(gzip_index, f)
        # ubelt.delete(zipped_index_path)  # remove archive file?
    return index_path


def sort_url_list(cc_values, all_acqdates, all_urls):
    """
    Sort the url list, first by ascending cc_values, and then by descending
    acqdate. Also replaces the gs:// prefix with the google api http prefix.

    Args:
        cc_values (List[float]): cloud cover for each item
        all_acqdates (List[datetime.datetime]): datetime for each item
        all_urls (List[str]): url for each item

    Returns:
        List[str]: sorted and modified urls

    Example:
        >>> from fels.utils import *  # NOQA
        >>> import datetime
        >>> cc_values = [2.11, 1.85, 18.51, 2.85, 3.92, 18.32]
        >>> all_acqdates = [datetime.datetime(2015, 3, 31, 0, 0),
        >>>                 datetime.datetime(2015, 6, 19, 0, 0),
        >>>                 datetime.datetime(2015, 2, 27, 0, 0),
        >>>                 datetime.datetime(2015, 1, 26, 0, 0),
        >>>                 datetime.datetime(2015, 3, 15, 0, 0),
        >>>                 datetime.datetime(2015, 6, 3, 0, 0)]
        >>> all_urls = ['gs://test_url_{}'.format(i) for i in range(len(cc_values))]
        >>> sorted_urls = sort_url_list(cc_values, all_acqdates, all_urls)
        >>> print('sorted_urls = {}'.format(ubelt.repr2(sorted_urls, nl=1)))
        sorted_urls = [
            'http://storage.googleapis.com/test_url_1',
            'http://storage.googleapis.com/test_url_0',
            'http://storage.googleapis.com/test_url_3',
            'http://storage.googleapis.com/test_url_4',
            'http://storage.googleapis.com/test_url_5',
            'http://storage.googleapis.com/test_url_2',
        ]
    """
    # For implementation clarity, table-like list of dictionary rows
    rows = [
        {'cc': cc, 'date': date, 'url': url}
        for cc, date, url in zip(cc_values, all_acqdates, all_urls)
    ]
    # First group and sort by ascending cloudcover
    cc_to_rows = ubelt.group_items(rows, key=lambda row: row['cc'])
    cc_to_rows = ubelt.sorted_keys(cc_to_rows)

    sorted_urls = []
    for cc, group in cc_to_rows.items():
        # Then within each group, sort by descending date
        group = sorted(group, key=lambda row: (row['date'], row['url']), reverse=True)
        for row in group:
            url = row['url']
            new_url = 'http://storage.googleapis.com/' + url.replace('gs://', '')
            sorted_urls.append(new_url)
    return sorted_urls


def ensure_sqlite_csv_conn(collection_file, fields, table_create_cmd,
                           tablename='unnamed_table1', index_cols=[],
                           overwrite=False):
    """
    Returns a connection to a cache of a csv file
    """
    sql_fpath = collection_file + '.v001.sqlite'
    overwrite = False
    if os.path.exists(sql_fpath):
        sql_stat = os.stat(sql_fpath)
        col_stat = os.stat(collection_file)
        # CSV file has a newer modified time, we have to update
        if col_stat.st_mtime > sql_stat.st_mtime:
            overwrite = True
    else:
        overwrite = True

    stamp_dpath = ubelt.ensuredir((os.path.dirname(collection_file), '.stamps'))
    base_name = os.path.basename(collection_file)

    stamp = ubelt.CacheStamp(base_name, dpath=stamp_dpath, depends=[
        fields, table_create_cmd, tablename], verbose=3
    )
    if stamp.expired():
        overwrite = True

    if overwrite:
        # Update the SQL cache if the CSV file was modified.
        print('Computing (or recomputing) an sql cache')

        ubelt.delete(sql_fpath, verbose=3)
        print('Initial connection to sql_fpath = {!r}'.format(sql_fpath))
        conn = sqlite3.connect(sql_fpath)
        cur = conn.cursor()
        try:
            print('(SQL) >')
            print(table_create_cmd)
            cur.execute(table_create_cmd)

            keypart = ','.join(fields)
            valpart = ','.join('?' * len(fields))
            insert_statement = ubelt.codeblock(
                '''
                INSERT INTO {tablename}({keypart})
                VALUES({valpart})
                ''').format(keypart=keypart, valpart=valpart,
                            tablename=tablename)

            if index_cols:
                index_cols_str = ', '.join(index_cols)
                indexname = 'noname_index'
                # TODO: Can we make an efficient date index with sqlite?
                create_index_cmd = ubelt.codeblock(
                    '''
                    CREATE INDEX {indexname} ON {tablename} ({index_cols_str});
                    ''').format(
                        index_cols_str=index_cols_str, tablename=tablename,
                        indexname=indexname)
                print('(SQL) >')
                print(create_index_cmd)
                _ = cur.execute(create_index_cmd)

            import tqdm
            print('convert to sqlite collection_file = {!r}'.format(collection_file))
            with open(collection_file, 'r') as csvfile:

                # Read the total number of bytes in the CSV file
                csvfile.seek(0, 2)
                total_nbytes = csvfile.tell()

                # Read the header information
                csvfile.seek(0)
                header = csvfile.readline()
                header_nbytes = csvfile.tell()

                # Approximate the number of lines in the file
                # Measure the bytes in the first N lines and take the average
                num_lines_to_measure = 100
                csvfile.seek(0, 2)
                content_nbytes = total_nbytes - header_nbytes
                csvfile.seek(header_nbytes)
                for _ in range(num_lines_to_measure):
                    csvfile.readline()
                first_content_bytes = csvfile.tell() - header_nbytes
                appprox_bytes_per_line = first_content_bytes / num_lines_to_measure
                approx_num_rows = int(content_nbytes / appprox_bytes_per_line)

                # Select the indexes of the columns we want
                csv_fields = header.strip().split(',')
                field_to_idx = {field: idx for idx, field in enumerate(csv_fields)}
                col_indexes = [field_to_idx[k] for k in fields]

                prog = tqdm.tqdm(
                    iter(csvfile),
                    desc='insert csv rows into sqlite cache',
                    total=approx_num_rows, mininterval=1, maxinterval=15,
                    position=0, leave=True,
                )
                # Note: Manual iteration is 1.5x faster than DictReader
                for line in prog:
                    cols = line[:-1].split(',')
                    # Select the values to insert into the SQLite database
                    # Note: if this fails with an index error, its possible
                    # the CSV file was not fully downloaded
                    vals = [cols[idx] for idx in col_indexes]
                    cur.execute(insert_statement, vals)

            conn.commit()
        except Exception:
            raise
        else:
            GLOBAL_SQLITE_CONNECTIONS[sql_fpath] = conn
            stamp.renew()
        finally:
            cur.close()

    # cache SQLite connections
    if sql_fpath in GLOBAL_SQLITE_CONNECTIONS:
        conn = GLOBAL_SQLITE_CONNECTIONS[sql_fpath]
    else:
        conn = sqlite3.connect(sql_fpath)
        GLOBAL_SQLITE_CONNECTIONS[sql_fpath] = conn

    return conn


@atexit.register
def _close_global_conns():
    for conn in GLOBAL_SQLITE_CONNECTIONS.values():
        conn.close()
    GLOBAL_SQLITE_CONNECTIONS.clear()
