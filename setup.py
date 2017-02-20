from setuptools import setup

setup(name='FeLS',
      version='1.3.0',
      description='Fetch Landsat & Sentinel Data from google cloud',
      url='https://github.com/vascobnunes/fetchLandsatSentinelFromGoogleCloud',
      author='vascobnunes',
      author_email='vascobnunes@gmail.com',
      license='GPL',
      packages=['fels'],
      zip_safe=False,
      install_requires=['numpy'])