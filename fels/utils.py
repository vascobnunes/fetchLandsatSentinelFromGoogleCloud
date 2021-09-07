from __future__ import absolute_import, division, print_function
import os
import shutil
import atexit
import csv
import gzip
import sqlite3
import ubelt
# try:
#     from urllib2 import urlopen
# except ImportError:
#     from urllib.request import urlopen


FELS_DEFAULT_OUTPUTDIR = os.environ.get('FELS_DEFAULT_OUTPUTDIR', '')
if not FELS_DEFAULT_OUTPUTDIR:
    FELS_DEFAULT_OUTPUTDIR = ubelt.get_app_cache_dir('fels')
    # FELS_DEFAULT_OUTPUTDIR = os.path.expanduser('~/data/fels')


def download_metadata_file(url, outputdir, program):
    """Download and unzip the catalogue files."""
    if outputdir is None:
        outputdir = FELS_DEFAULT_OUTPUTDIR
    zipped_index_path = os.path.join(outputdir, 'index_' + program + '.csv.gz')
    if not os.path.isfile(zipped_index_path):
        if not os.path.exists(os.path.dirname(zipped_index_path)):
            os.makedirs(os.path.dirname(zipped_index_path))
        print("Downloading Metadata file...")
        print('url = {!r}'.format(url))
        print('outputdir = {!r}'.format(outputdir))
        print('program = {!r}'.format(program))
        ubelt.download(url, fpath=zipped_index_path, chunksize=int(2 ** 22))
        # content = urlopen(url)
        # with open(zipped_index_path, 'wb') as f:
        #     shutil.copyfileobj(content, f)
    index_path = os.path.join(outputdir, 'index_' + program + '.csv')
    if not os.path.isfile(index_path):
        print("Unzipping Metadata file...")
        with gzip.open(zipped_index_path) as gzip_index, open(index_path, 'wb') as f:
            shutil.copyfileobj(gzip_index, f)
    return index_path


def sort_url_list(cc_values, all_acqdates, all_urls):
    """Sort the url list by increasing cc_values and acqdate."""
    cc_values = sorted(cc_values)
    all_acqdates = sorted(all_acqdates, reverse=True)
    all_urls = [x for (y, z, x) in sorted(zip(cc_values, all_acqdates, all_urls))]
    urls = []
    for url in all_urls:
        urls.append('http://storage.googleapis.com/' + url.replace('gs://', ''))
    return urls


def download_file(url, destination_filename):
    """Function to download files using pycurl lib"""
    ubelt.download(url, fpath=destination_filename)
    # with requests.get(url, stream=True) as r:
    #     with open(destination_filename, 'wb') as f:
    #         shutil.copyfileobj(r.raw, f)


GLOBAL_SQLITE_CONNECTIONS = {}


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
        if 1:
            print('col_stat = {!r}'.format(col_stat))
            print('sql_stat = {!r}'.format(sql_stat))
        # CSV file has a newer modified time, we have to update
        if col_stat.st_mtime > sql_stat.st_mtime:
            overwrite = True
    else:
        overwrite = True

    stamp_dpath = ubelt.ensuredir((os.path.dirname(collection_file), '.stamps'))
    base_name = os.path.basename(collection_file)

    stamp = ubelt.CacheStamp(base_name, dpath=stamp_dpath, depends=[
        fields, table_create_cmd, tablename],
        # product=[sql_fpath],
        verbose=3
    )
    if stamp.expired():
        overwrite = True

    if overwrite:
        # Update the SQL cache if the CSV file was modified.
        print('Computing (or recomputing) an sql cache')

        ubelt.delete(sql_fpath, verbose=3)
        print('Initial connection to sql_fpath = {!r}'.format(sql_fpath))
        conn = sqlite3.connect(sql_fpath)

        try:
            cur = conn.cursor()

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
                # Can we make an efficient date index with sqlite?
                create_index_cmd = ubelt.codeblock(
                    '''
                    CREATE INDEX {indexname} ON {tablename} ({index_cols_str});
                    ''').format(
                        index_cols_str=index_cols_str, tablename=tablename,
                        indexname=indexname)
                print('(SQL) >')
                print(create_index_cmd)
                _ = cur.execute(create_index_cmd)

            print('collection_file = {!r}'.format(collection_file))
            with open(collection_file) as csvfile:
                reader = csv.DictReader(csvfile)
                import tqdm
                for row in tqdm.tqdm(reader, desc='insert csv rows into sqlite cache', mininterval=3, maxinterval=30):
                    vals = [row[k] for k in fields]
                    cur.execute(insert_statement, vals)
            conn.commit()
        except Exception:
            raise
        else:
            GLOBAL_SQLITE_CONNECTIONS[sql_fpath] = conn
            stamp.renew()
        finally:
            conn.close()

    # hack to not reconnect each time
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
