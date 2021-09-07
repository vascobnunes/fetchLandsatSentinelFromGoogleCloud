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

                # One iterating through the file doesn't take too long
                # to get the exact number of rows
                # num_rows = sum(1 for _ in iter(csvfile))

                # But we can get a really good approximation by just measuring
                # the first few lines
                num_lines_to_measure = 100
                csvfile.seek(0, 2)
                content_nbytes = total_nbytes - header_nbytes
                csvfile.seek(header_nbytes)
                for _ in range(num_lines_to_measure):
                    csvfile.readline()
                first_content_bytes = csvfile.tell() - header_nbytes
                appprox_bytes_per_line = first_content_bytes / num_lines_to_measure
                approx_num_rows = int(content_nbytes / appprox_bytes_per_line)

                csv_fields = header.strip().split(',')
                # Select the indexes of the columns we want
                field_to_idx = {field: idx for idx, field in enumerate(csv_fields)}
                col_indexes = [field_to_idx[k] for k in fields]

                prog = tqdm.tqdm(
                    iter(csvfile),
                    desc='insert csv rows into sqlite cache',
                    total=approx_num_rows, mininterval=1, maxinterval=15,
                    position=0, leave=True,
                )
                # Note: Manual iteration is 1.5x faster than DictReader
                # 143,416.34it/s
                for line in prog:
                    cols = line[:-1].split(',')
                    # Select the values to insert into the SQLite database
                    vals = [cols[idx] for idx in col_indexes]
                    cur.execute(insert_statement, vals)

                # TODO: we can delete this code
                # verus 95,770.39it/s
                # csvfile.seek(0)
                # reader = csv.DictReader(csvfile)
                # prog = tqdm.tqdm(
                #     reader, desc='insert csv rows into sqlite cache',
                #     total=approx_num_rows, mininterval=3, maxinterval=30)
                # for row in prog:
                #     vals = [row[k] for k in fields]
                #     cur.execute(insert_statement, vals)

            conn.commit()
        except Exception:
            raise
        else:
            GLOBAL_SQLITE_CONNECTIONS[sql_fpath] = conn
            stamp.renew()
        finally:
            cur.close()

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
