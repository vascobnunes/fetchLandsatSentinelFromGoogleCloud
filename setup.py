try:
    from setuptools import setup

    setup_kwargs = {'entry_points': {'console_scripts': ['fels=fels.fels:main']}}
except ImportError:
    from distutils.core import setup

    setup_kwargs = {'scripts': ['bin/fels']}

tag = '1.3.7'

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
name='FeLS',
    version=tag,
    py_modules=['fels'],
    description='Fetch Landsat & Sentinel Data from google cloud',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/vascobnunes/fetchLandsatSentinelFromGoogleCloud',
    author='vascobnunes',
    author_email='vascobnunes@gmail.com',
    license='GPL',
    zip_safe=False,
    packages=['fels'],
    package_data={'fels.data': [
        'WRS2_descending.xml',
        'sentinel_2_index_shapefile.prj',
        'WRS2_descending.dbf',
        'sentinel_2_index_shapefile.sbn',
        'WRS2_descending.cpg',
        'WRS2_descending.shp',
        'WRS2_descending.shx',
        'WRS2_descending.sbx',
        '__init__.py',
        'sentinel_2_index_shapefile.cpg',
        'sentinel_2_index_shapefile.shp',
        'sentinel_2_index_shapefile.shx',
        'sentinel_2_index_shapefile.sbx',
        'WRS2_descending.prj',
        'WRS2_descending.sbn',
        'sentinel_2_index_shapefile.dbf',
        'source_metadata.txt',]
    },
    install_requires=['numpy', 'requests', 'shapely', 'geopandas',],
    dependency_links=['https://www.conan.io/source/Gdal/2.1.3/osechet/stable'],
    **setup_kwargs)
