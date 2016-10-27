import subprocess
import datetime
import os, sys
import csv
import optparse

###########################################################################
class OptionParser (optparse.OptionParser):
 
	def check_required (self, opt):
	  option = self.get_option(opt)
 
	  # Assumes the option's 'default' is set to None!
	  if getattr(self.values, option.dest) is None:
		  self.error("%s option not supplied" % option)
 
#############################"Functions
def downloadLandsatMetadataFile(url,outputdir):
	theZippedFile=os.path.join(outputdir,'index.csv.gz')
	theFile=os.path.join(outputdir,'index.csv')
	if not os.path.isfile(theZippedFile):
		print "Downloading Landsat Metadata file..."
		#download the file
		try:
			subprocess.call('curl '+url+' -o '+theZippedFile, shell=True)	
		except:
			print "Some error occurred when trying to download the Landsat Metadata file!"
	if not os.path.isfile(theFile):
		print "Unzipping Landsat Metadata file..."
		#unzip the file
		try:
			subprocess.call(['gunzip',theZippedFile])
		except:
			print "Some error occurred when trying to unzip the Landsat Metadata file!"	
	return theFile

def find_in_collection_metadata(collection_file,cc_limit,date_start,date_end,wr2path,wr2row):
	print "Searching for images in catalog..."
	cloudcoverlist = []
	cc_values = []	
	with open(collection_file) as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			year_acq =int(row['DATE_ACQUIRED'][0:4])
			month_acq=int(row['DATE_ACQUIRED'][5:7])
			day_acq  =int(row['DATE_ACQUIRED'][8:10])
			acqdate=datetime.datetime(year_acq,month_acq, day_acq)
			if 	int(row['WRS_PATH'])==int(wr2path) and int(row['WRS_ROW'])==int(wr2row) and float(row['CLOUD_COVER'])<=cc_limit and date_start<acqdate<date_end:
				cloudcoverlist.append(row['CLOUD_COVER'] + '--' + row['BASE_URL'])
				cc_values.append(float(row['CLOUD_COVER']))				
			else:
				url=''
	for i in cloudcoverlist:
		if float(i.split('--')[0])==min(cc_values):
			url = i.split('--')[1]
	if url!='':
		url='http://storage.googleapis.com/'+url.replace('gs://','')	
	return url

def downloadFromGoogleCloud(url,outputdir):
	img=url.split("/")[len(url.split("/"))-1]
	possible_bands=['B1.TIF','B2.TIF','B3.TIF','B4.TIF','B5.TIF','B6.TIF','B7.TIF','B9.TIF','BQA.TIF','MTL.txt']
	for bands in possible_bands:
		completeUrl=url+"/"+img+"_"+bands
		destinationDir=os.path.join(outputdir,img)
		if not os.path.exists(destinationDir):
				os.makedirs(destinationDir)
		destinationFile=os.path.join(destinationDir,img+"_"+bands)
		try:
			subprocess.call('curl '+completeUrl+' -o '+destinationFile, shell=True)	
		except:
			continue
			
######################################################################################
###############					   main					########################
######################################################################################
 

def main():
	################Read arguments
	if len(sys.argv) == 1:
		prog = os.path.basename(sys.argv[0])
		print '	  '+sys.argv[0]+' [options]'
		print "	 Help : ", prog, " --help"
		print "		or : ", prog, " -h"
		print "example: python %s -s 203031 -b LC8 -d 20151001 -f 20151231 --output /tmp/LANDSAT"%sys.argv[0]

		sys.exit(-1)
	else:
		usage = "usage: %prog [options] "
		parser = OptionParser(usage=usage)
		parser.add_option("-s", "--scene", dest="scene", action="store", type="string", \
				help="WRS2 coordinates of scene (ex 198030)", default=None)
		parser.add_option("-d", "--start_date", dest="start_date", action="store", type="string", \
				help="start date, fmt('20131223')")
		parser.add_option("-f","--end_date", dest="end_date", action="store", type="string", \
				help="end date, fmt('20131223')")
		parser.add_option("-c","--cloudcover", dest="clouds", action="store", type="float", \
				help="Set a limit to the cloud cover of the image", default=100)				
		parser.add_option("-b","--sat", dest="bird", action="store", type="choice", \
				help="Which satellite are you looking for", choices=['LT5','LE7', 'LC8'], default='LC8')	
		parser.add_option("--output", dest="output", action="store", type="string", \
				help="Where to download files",default='/tmp/LANDSAT')
		parser.add_option("--outputcatalogs", dest="outputcatalogs", action="store", type="string", \
				help="Where to download metadata catalog files",default='/tmp/LANDSAT')					

		(options, args) = parser.parse_args()
		parser.check_required("-s")
		parser.check_required("-d")
		parser.check_required("-f")

	rep=options.output

	produit=options.bird
	path=options.scene[0:3]
	row=options.scene[3:6]
	year_start =int(options.start_date[0:4])
	month_start=int(options.start_date[4:6])
	day_start  =int(options.start_date[6:8])
	date_start=datetime.datetime(year_start,month_start, day_start)
	year_end =int(options.end_date[0:4])
	month_end=int(options.end_date[4:6])
	day_end  =int(options.end_date[6:8])
	date_end =datetime.datetime(year_end,month_end, day_end)
	landsatMetadataUrl='http://storage.googleapis.com/gcp-public-data-landsat/index.csv.gz'
	
	################Run functions for LANDSAT Download	
	LandsatMetadataFile=downloadLandsatMetadataFile(landsatMetadataUrl,options.outputcatalogs)
	url=find_in_collection_metadata(LandsatMetadataFile,options.clouds,date_start,date_end,path,row)
	downloadFromGoogleCloud(url,options.output)
	
if __name__ == "__main__":
	main()	