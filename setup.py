try:
    from setuptools import setup

    setup_kwargs = {'entry_points': {'console_scripts': ['fels=fels.fels:main']}}
except ImportError:
    from distutils.core import setup

    setup_kwargs = {'scripts': ['bin/fels']}

tag = '1.3.0'

setup(name='FeLS',
      version=tag,
      py_modules=['fels'],
      description='Fetch Landsat & Sentinel Data from google cloud',
      url='https://github.com/vascobnunes/fetchLandsatSentinelFromGoogleCloud',
      author='vascobnunes',
      author_email='vascobnunes@gmail.com',
      license='GPL',
      zip_safe=False,
      packages=['fels'],
      install_requires=['numpy'],
      dependency_links=['https://www.conan.io/source/Gdal/2.1.3/osechet/stable'],
      **setup_kwargs)
