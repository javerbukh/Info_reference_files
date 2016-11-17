from astropy.io import fits
import os
import re
import csv
import argparse
import json
import asdf

def get_required_keywords_from_original():
    """
    Reads required_keywords.txt and organizes the values into a dictionary,
    then seperates the values into csv files, based on which instrument they are
    for
    """
    required_keywords = {}
    f = open('required_keywords.txt', 'r')
    curr_instrument = ""
    for line in f:
        if line[-2:] == ":\n":
            instrument = line[:-2]
            curr_instrument = instrument
            if instrument not in required_keywords.keys():
                required_keywords[instrument] = {}
            #print (line[:-2])
        elif line == "\n":
            pass
        else:
            line = re.sub('[(),\'|]', '', line)
            line = re.sub('\.', ' ', line)
            new_line = line.split(' ')
            final_line = []
            final_line.append(new_line[0])
            for l in range(1,len(new_line)):
                temp_word = str(new_line[l][:8])
                temp_word = re.sub('\n','',temp_word)
                if temp_word not in final_line:
                    final_line.append(temp_word)
            required_keywords[curr_instrument][final_line[0]] = final_line[1:]
    more_required = ['REFTYPE', 'DESCRIP', 'AUTHOR', 'PEDIGREE', 'HISTORY']
    for k,v in required_keywords.iteritems():
        path = 'required_keywords/' + k + '_required_keywords.csv'
        with open(path, 'wb') as csvfile:
            keywriter = csv.writer(csvfile, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
            for key,value in v.iteritems():
                keywriter.writerow([key]+value + more_required)

def change_style(instrument):
    if instrument.lower() == "miri":
        return "MIRI"
    elif instrument.lower() == "niriss":
        return "NIRISS"
    elif instrument.lower() == "nircam":
        return "NIRCam"
    elif instrument.lower() == "nirspec":
        return "NIRSpec"
    elif instrument.lower() == "fgs":
        return "FGS"
    else:
        return False

def check_usability(hdulist):
    """
    Checks to make sure all necessary headers are present
    """
    status = True

    if 'INSTRUME' in hdulist[0].header:
        if change_style(hdulist[0].header['INSTRUME']):
            pass
        else:
            print ("Not a valid value for INSTRUME: {}".format(hdulist[0].header['INSTRUME']))
            status = False
    else:
        print ("Missing INSTRUME header in file ")
        status = False
    if 'REFTYPE' in hdulist[0].header:
        pass
    else:
        print ("Missing REFTYPE header in file ")
        status = False

    return status

def get_file_headers(hdulist):
    """
    Returns header values for the most frequently accessed headers
    """
    if 'TELESCOP' in hdulist[0].header:
        get_instrume = hdulist[0].header['INSTRUME']
        get_telescop = hdulist[0].header['TELESCOP']
        get_reftype = hdulist[0].header['REFTYPE']
        return (get_instrume, get_telescop, get_reftype)
    else:
        get_instrume = hdulist[0].header['INSTRUME']
        get_telescop = False
        get_reftype = hdulist[0].header['REFTYPE']
        return (get_instrume, get_telescop, get_reftype)

def check_required_keys(instrument, filename, hdulist):
    """
    Checks to see that all the required keywords are present with the file.
    If not, it returns those values.
    If the file used to check these values is not present, that will be returned
    instead
    """
    check_if_filename_present = False
    not_found_req_keys= []
    missing_keys = []
    (get_instrume, get_telescop, get_reftype) = get_file_headers(hdulist)

    file_loc = "/grp/hst/cdbs/tools/jwst/required_keywords/" + change_style(instrument) + "_required_keywords.csv"
    with open(file_loc, 'rb') as csvfile:
        keyreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in keyreader:
            check_if_tests_in_filename = False
            #INSTRUME and REFTYPE have valid values
            if re.search(get_instrume.lower(),row[0]) != None and \
                    re.search(get_reftype.lower(),row[0]) != None:

                check_if_filename_present = True
                #TELESCOP exists and has a matching value
                if get_telescop and re.search(get_telescop.lower(),row[0]) != None:
                    if set(row[1:]).issubset(set(hdulist[0].header)):
                        print ("Required keywords are present")
                    else:
                        for key in row[1:]:
                            if key not in hdulist[0].header:
                                missing_keys.append(key)
                        print ("Missing keywords in {}: {}".format(filename, missing_keys))
                    break
                #TELESCOP exists but does not have a valid value or does not exist
                else:
                    for key in row[1:]:
                        if key not in hdulist[0].header:
                            missing_keys.append(key)
                    if missing_keys:
                        print ("Missing keywords in {}: {}".format(filename, missing_keys))
                    else:
                        if get_telescop:
                            print ("Check TELESCOP value: {}".format(hdulist[0].header["TELESCOP"]))
                        else:
                            print ("Set valid value for TELESCOP")
                    break

    if not check_if_filename_present:
        print ("ERROR: Could not find file to check required keys for {}".format(filename))
        if get_reftype:
            print ("The REFTYPE may be invalid: {}".format(get_reftype))

def read_and_check_valid_params(instrument, file_header):
    """
    Returns which paramters in the file are invalid, if any
    """
    non_valid_params = []
    file_loc = "/grp/hst/cdbs/tools/jwst/valid_params/" + change_style(instrument) + "_valid_params.csv"

    datetime1 = re.compile("([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1])T([0-1][0-9]|[2][0-3]):[0-5][0-9]:[0-5][0-9]")
    datetime2 = re.compile("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    inflight_datetime = re.compile("INFLIGHT ([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1]) ([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1])")

    with open(file_loc, 'rb') as csvfile:
        keyreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in keyreader:
            if row[0] in file_header:
                #In the cases of SUBSTRT or SUBSIZE
                if type(file_header[row[0]]) is int:
                    row[1:] = [int(x) for x in row[1:]]
                #If OR is present in value
                if type(file_header[row[0]]) is not int and "|" in file_header[row[0]]:
                    values = file_header[row[0]].split("|")
                    if values[0] in row[1:]:
                        pass
                    else:
                        non_valid_params.append((values[0], row[0]))

                    if values[1] in row[1:]:
                        pass
                    else:
                        non_valid_params.append((values[1], row[0]))
                #Valid value
                if (type(file_header[row[0]]) is int or "|" not in file_header[row[0]]) \
                    and file_header[row[0]] in row[1:]:
                    pass
                #Check USEAFTER
                elif row[0] == 'USEAFTER':
                    if re.match(datetime1, file_header[row[0]]):
                        pass
                    elif re.match(datetime2, file_header[row[0]]):
                        print ("Correct format but inaccurate dates in USEAFTER")
                        non_valid_params.append((file_header[row[0]], row[0]))
                    else:
                        non_valid_params.append((file_header[row[0]], row[0]))
                #Check PEDIGREE
                elif row[0] == 'PEDIGREE':
                    valid_options = ['SIMULATION', 'GROUND', 'DUMMY']
                    if (file_header[row[0]] in valid_options) or re.match(inflight_datetime, file_header[row[0]]):
                        pass
                    else:
                        non_valid_params.append((file_header[row[0]], row[0]))
                #Check's to see if certain headers are not empty
                elif row[0] in ['AUTHOR', 'DESCRIP', 'HISTORY']:
                        if file_header[row[0]] == "":
                            non_valid_params.append((file_header[row[0]], row[0]))
                #Not a valid value
                else:
                    non_valid_params.append((file_header[row[0]], row[0]))
            else:
                pass
        if not non_valid_params:
            print ("All parameters are valid")
        else:
            print ("Non-valid paramters (Format (Non-valid value, Header located in)): {}".format(non_valid_params))

def check_required_keys_json_asdf(file_type, file_header):
    if file_type == "json":
        required_keywords = ["title", "reftype", "pedigree", "author", "telescope", "exp_type",\
            "instrument", "useafter", "description", "HISTORY", "msaoper"]
    elif file_type == "asdf":
        required_keywords = ["title", "reftype", "pedigree", "author", "telescope", "exp_type",\
            "instrument", "useafter", "description", "history"]
    if set(required_keywords).issubset(set(file_header)):
        print ("All required keys are present")
        return True
    else:
        missing_keys = []
        for key in required_keywords:
            if key not in file_header:
                missing_keys.append(key)
        print ("Missing keys in file: {}".format(missing_keys))
        return False

def read_and_check_valid_params_json(instrument, file_header):
    """
    Returns which paramters in the file are invalid, if any
    """
    non_valid_params = []
    file_loc = "/grp/hst/cdbs/tools/jwst/valid_params/" + change_style(instrument) + "_valid_params.csv"

    datetime1 = re.compile("([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1])T([0-1][0-9]|[2][0-3]):[0-5][0-9]:[0-5][0-9]")
    datetime2 = re.compile("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    inflight_datetime = re.compile("INFLIGHT ([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1]) ([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1])")

    new_file_header = {}
    for header in file_header:
        if header == "description":
            new_file_header[header[:7].upper()] = file_header[header]
        else:
            new_file_header[header[:8].upper()] = file_header[header]
    file_header = new_file_header

    with open(file_loc, 'rb') as csvfile:
        keyreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in keyreader:
            if row[0].lower() in file_header or (row[0] == "HISTORY" and row[0] in file_header):
            #for header in file_header:
            #If OR is present in value
                if not type(file_header[row[0]]) is int and "|" in file_header[row[0]]:
                    values = file_header[row[0]].split("|")
                    if values[0] in row[1:]:
                        pass
                    else:
                        non_valid_params.append((values[0], row[0]))

                    if values[1] in row[1:]:
                        pass
                    else:
                        non_valid_params.append((values[1], row[0]))
                    #Valid value
                elif file_header[row[0]] in row[1:]:
                    pass
                #Check USEAFTER
                elif row[0] == 'USEAFTER':
                    if re.match(datetime1, file_header[row[0]]):
                        pass
                    elif re.match(datetime2, file_header[row[0]]):
                        print ("Correct format but inaccurate dates in USEAFTER")
                        non_valid_params.append((file_header[row[0]], row[0]))
                    else:
                        non_valid_params.append((file_header[row[0]], row[0]))
                #Check PEDIGREE
                elif row[0] == 'PEDIGREE':
                    valid_options = ['SIMULATION', 'GROUND', 'DUMMY']
                    if (file_header[row[0]] in valid_options) or re.match(inflight_datetime, file_header[row[0]]):
                        pass
                    else:
                        non_valid_params.append((file_header[row[0]], row[0]))
                #Check's to see if certain headers are not empty
                elif row[0] in ['AUTHOR', 'DESCRIP', 'HISTORY']:
                        if file_header[row[0]] == "":
                            non_valid_params.append((file_header[row[0]], row[0]))
                #Not a valid value
                else:
                    non_valid_params.append((file_header[row[0]], row[0]))
            else:
                pass
        if not non_valid_params:
            print ("All parameters are valid")
        else:
            print ("Non-valid paramters (Format (Non-valid value, Header located in)): {}".format(non_valid_params))

def read_and_check_valid_params_asdf(instrument, file_header):
    """
    Returns which paramters in the file are invalid, if any
    """
    non_valid_params = []
    file_loc = "/grp/hst/cdbs/tools/jwst/valid_params/" + change_style(instrument) + "_valid_params.csv"

    datetime1 = re.compile("([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1])T([0-1][0-9]|[2][0-3]):[0-5][0-9]:[0-5][0-9]")
    datetime2 = re.compile("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    inflight_datetime = re.compile("INFLIGHT ([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1]) ([1][9]|([2][0-1]))\d{2}-([0][0-9]|[1][0-2])-([0-2][0-9]|[3][0-1])")

    required_keywords = ["title", "reftype", "pedigree", "author", "telescope", "exp_type",\
        "instrument", "useafter", "description", "history"]
    new_file_header = {}
    for header in required_keywords:
        if header == "description":
            new_file_header[header[:7].upper()] = file_header.tree[header]
        else:
            new_file_header[header[:8].upper()] = file_header.tree[header]
    file_header = new_file_header

    with open(file_loc, 'rb') as csvfile:
        keyreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in keyreader:
            if row[0].lower() in file_header or (row[0] == "HISTORY" and row[0] in file_header):
            #for header in file_header:
                #If OR is present in value
                if not type(file_header[row[0]]) is int and "|" in file_header[row[0]]:
                    values = file_header[row[0]].split("|")
                    if values[0] in row[1:]:
                        pass
                    else:
                        non_valid_params.append((values[0], row[0]))

                    if values[1] in row[1:]:
                        pass
                    else:
                        non_valid_params.append((values[1], row[0]))
                #Valid value
                elif file_header[row[0]] in row[1:]:
                    pass
                #Check USEAFTER
                elif row[0] == 'USEAFTER':
                    if re.match(datetime1, file_header[row[0]]):
                        pass
                    elif re.match(datetime2, file_header[row[0]]):
                        print ("Correct format but inaccurate dates in USEAFTER")
                        non_valid_params.append((file_header[row[0]], row[0]))
                    else:
                        non_valid_params.append((file_header[row[0]], row[0]))
                #Check PEDIGREE
                elif row[0] == 'PEDIGREE':
                    valid_options = ['SIMULATION', 'GROUND', 'DUMMY']
                    if (file_header[row[0]] in valid_options) or re.match(inflight_datetime, file_header[row[0]]):
                        pass
                    else:
                        non_valid_params.append((file_header[row[0]], row[0]))
                #Check's to see if certain headers are not empty
                elif row[0] in ['AUTHOR', 'DESCRIP', 'HISTORY']:
                        if file_header[row[0]] == "":
                            non_valid_params.append((file_header[row[0]], row[0]))
                #Not a valid value
                else:
                    non_valid_params.append((file_header[row[0]], row[0]))
            else:
                pass
        if not non_valid_params:
            print ("All parameters are valid")
        else:
            print ("Non-valid paramters (Format (Non-valid value, Header located in)): {}".format(non_valid_params))
################################################################################
# Main
################################################################################

parser = argparse.ArgumentParser()
parser.add_argument("chosen_directory", help="the directory of fits files to be run")
args = parser.parse_args()

directory = args.chosen_directory
#directory = "/grp/crds/jwst/references/jwst/"
#irectory = "/user/rmiller/CDBS/testfile"
#directory = "/Users/javerbukh/Documents/Info_reference_files"
for filename in os.listdir(directory):
    new_path = str(os.path.join(directory, filename))
    if filename.endswith(".fits"):
        print ("Checking {}".format(filename))
        try:
            hdulist = fits.open(new_path)
        except e:
            print ("NOT A VALID FILE")
            break
        if check_usability(hdulist):
            instrument_team = hdulist[0].header['INSTRUME']
            check_required_keys(instrument_team, filename, hdulist)
            read_and_check_valid_params(instrument_team, hdulist[0].header)
        print ("------------------------------------------------------------\n")
    elif filename.endswith(".json"):
        print ("Checking {}".format(filename))
        try:
            json_file = json.load(open(new_path))
        except e:
            print ("NOT A VALID FILE")
            break
        if check_required_keys_json_asdf("json", json_file):
            read_and_check_valid_params_json(json_file["instrument"], json_file)
        print ("------------------------------------------------------------\n")
    elif filename.endswith(".asdf"):
        print ("Checking {}".format(filename))
        try:
            asdf_file = asdf.open(new_path)
        except e:
            print ("NOT A VALID FILE")
            break
        if check_required_keys_json_asdf("asdf", asdf_file.tree):
            read_and_check_valid_params_asdf(asdf_file.tree["instrument"], asdf_file)
        print ("------------------------------------------------------------\n")
    else:
        continue
