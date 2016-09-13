from astropy.io import fits
import os
import re

hdulist = fits.open('jwst_nircam_saturation_0049.fits')

must_have = ['DESCRIP', 'PEDIGREE', 'INSTRUME', 'DETECTOR', 'AUTHOR', 'USEAFTER']
# print (set(must_have).issubset(set(hdulist[0].header)))
# print (hdulist.info())
# print (hdulist[0].header)
# print (len(hdulist[4].header))
required_keywords = {}
f = open('required_keywords.txt', 'r')
curr_instrument = ""
for line in f:
    if line[-2:] == ":\n":
        instrument = line[:-2]
        curr_instrument = instrument
        if instrument not in required_keywords.keys():
            required_keywords[instrument] = {}
            print ("done")
        print (line[:-2])
    elif line == "\n":
        pass
    else:

    #print (line[len(line)-2:])
        line = re.sub('[(),\']', '', line)
        new_line = line.split()
        required_keywords[curr_instrument][new_line[0]] = new_line[1:]
print (required_keywords['NIRCam']['jwst_nircam_distortion'][0] == 'EXPOSURE.TYPE')
        #print (line.split())
#print (f.read())
#for word in f:
#    print (str(f))
print str(required_keywords['NIRCam'])

print (hdulist[0].header['DATE'])
print (hdulist[0].header['USEAFTER'])
directory = "/Users/javerbukh/Documents/JPipeline"
for filename in os.listdir(directory):
    if filename.endswith(".fits"):
        new_path = str(os.path.join(directory, filename))
        print(new_path)
        hdulist2 = fits.open(new_path)
        print (set(must_have).issubset(set(hdulist[0].header)))
        print (len(hdulist[0].header['DATE']))
        continue
    else:
        continue

# hdulist2 = fits.open('/grp/crds/jwst/references/jwst/' + hdulist[0].header['FILENAME'])
# print (hdulist2.info())
