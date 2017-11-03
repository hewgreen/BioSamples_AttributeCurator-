'''
generates input data for pipeline
producing four files attributes, samples, values and coexistences
see ./docs/documentation.md for details
'''
import os
import re
import csv
import sys
import math
import json
import time
import glob
import timeit
import string
import requests
import itertools
import pandas as pd
from tqdm import tqdm
from operator import add
from functools import wraps
from collections import Counter
from collections import Mapping
from pprint import pprint as pp
from multiprocessing import Process


def fn_timer(function):
	@wraps(function)
	def function_timer(*args, **kwargs):
		# dir(function)
		t0 = time.time()
		result_ = function(*args, **kwargs)
		t1 = time.time()
		print ("Total time running %s: %s seconds" %
				(function.__name__, str(t1-t0))
				)
		# outF.write('Total time running: ' + function.__name__ + ' ' + str(t1-t0) + '\n' + '\n')
		return result_
	return function_timer

# from concurrence 1

@fn_timer
def api_samples(parms):
	# BioSample API request module

	startpage = parms["start"]
	endpage = parms["end"]
	name = parms["name"]
	page_size = parms["size"]

	print("In api_samples", startpage, endpage)

	# counter_page = startpage

	# Open a file to write into it
	# `with` will close the file automatically
	with open(name + '.csv', 'w') as f:

		for counter_page in range(startpage, endpage + 1):

			# Initialize keys_list variable
			keys_list = []
			query_params = {
				"page": counter_page,
				"size": page_size,
			}

			# Request the API for the samples
			response = requests.get('http://www.ebi.ac.uk/biosamples/api/samples/', params=query_params)
			if response.status_code is not 200:
				# If the status code of the response is not 200 (OK), something is wrong with the API
				# Return the process
				print('Something wrong happening...')
				return

			# counter_page = counter_page + 1
			if counter_page % 100 == 0:
				print("Process " + name + " reached " + str(counter_page))

			# Looking through the JSON:
			# Get all samples on the page
			samples_in_page = response.json()['_embedded']['samples']

			# For each sample, get characteristics types and save them in the key_list variable
			for sample in samples_in_page:
				accession_no = sample['accession'] # added by MG to grab sampleIDs
				sample_characteristics = sample['characteristics']
				sample_keys = list(sample_characteristics.keys())
				sample_keys = [accession_no] + sample_keys
				keys_list.append(sample_keys)

			# Write the characteristics list into the file
			writer = csv.writer(f)
			writer.writerows(keys_list)

@fn_timer
def multithread_crawler():
	# Crawler script- get me a list of keys for every sample.

	# Splitting up the BioSamples Pages into equal chunks for multithreading
	numberOfParalelJobs = 8
	pageSize = 500
	query_params = {
		"size": pageSize,
	}
	rel = requests.get('http://www.ebi.ac.uk/biosamples/api/samples/', params=query_params)
	reply = rel.json()
	totalPageNumer = reply['page']['totalPages']

	startpoint = 0
	init = []
	for i in range(1, numberOfParalelJobs + 1):
		params = dict()
		params['run'] = i
		params['size'] = pageSize
		params['name'] = "Thread{}_results".format(str(i))
		params['start'] = startpoint

		endpoint = math.ceil(totalPageNumer / float(numberOfParalelJobs)) * i
		if endpoint < int(totalPageNumer):
			params['end'] = int(endpoint)
		else:
			params['end'] = totalPageNumer

		init.append(params)
		startpoint = int(endpoint) + 1

	processlist = []
	for entry in init:
		p = Process(target=api_samples, args=[entry])
		p.start()
		processlist.append(p)

	print("All process started")

	# Going through the process list, waiting for everything to finish
	for procs in processlist:
		procs.join()

	print("All finished")

	# combine results into samples file.
	
	filenames = []
	for f in glob.glob('Thread*_results.csv'):
		filenames.append(f)

	with open('./data/samples.csv', 'w') as outfile:
		for fname in filenames:
			with open(fname) as infile:
				for line in infile:
					outfile.write(line)

	# sys.exit()

def stripID():
	# makes .temp files that strips the first column. This will remove sample id before passing to concurrence counter.

	filenames = []
	for f in glob.glob('Thread*_results.csv'):
		filenames.append(f)
	

	for fname in filenames:
		tempname = str(fname + '.temp')
		with open(fname, 'r') as infile:
			reader = csv.reader(infile)
			reader_list = list(reader)
			writer = csv.writer(open(tempname,'w'))
			for sample in reader_list:
				sample_ = sample[1:]
				writer.writerow(sample_)

	# removes 'Thread*_results.csv' files
	for f in glob.glob('Thread*_results.csv'):
		os.remove(f)

	for f in glob.glob('Thread*_results.csv.temp'):
		z = f[:-5]
		os.rename(f, z)

	# sys.exit()

# from concurrence 2

@fn_timer
def create_cooccurrence_matrix(params):

	in_filename = params['filename_in']
	out_filename = params['filename_out']

	types_letter = list(string.ascii_lowercase) # was initially outside of function?
	types_letter.insert(0, "#") # was initially outside of function?
	# tcd = {letter: {} for letter in types_letter} # probably not necessary
	
	tcd = {}

	with open(in_filename, 'r') as f:
		samples_type_list = f.readlines()

	line_counter = 0
	total_lines = len(samples_type_list)
	for type_list in samples_type_list:
		if line_counter % 50000 == 0:
			print('Line {} of {}'.format(line_counter, total_lines))
		types = [type_name.strip() for type_name in type_list.split(',') if type_name]
		types.sort()
		types_permutations = itertools.combinations(types, 2)
		for perm in types_permutations:
			(A, B) = perm
			# first_letter = str(A[0]).lower()
			# if first_letter not in string.ascii_lowercase:
			#     first_letter = "#"
			if A not in tcd:
				tcd[A] = {}

			if B not in tcd[A]:
				tcd[A][B] = 0

			tcd[A][B] += 1
		line_counter += 1

	with open(out_filename, 'w') as fout:
		json.dump(tcd, fout)

@fn_timer
def trigger_matrix():
	# generate a dictionary to check if we already saw the type
	# Type check dictionary

	params = dict()

	base_filename_in = 'Thread\d_results.csv'
	base_filename_out = 'cooccurrence_matrix{}.json'

	input_files = [f for f in os.listdir('./') if re.match(base_filename_in, f)]
	for i in range(len(input_files)):
		input_file = input_files[i]
		print('Working on {}'.format(input_file))
		params['filename_in'] = input_file
		params['filename_out'] = base_filename_out.format(i+1)

		start_time = timeit.default_timer()
		create_cooccurrence_matrix(params)
		print(timeit.default_timer() - start_time)

	# removes 'Thread*_results.csv.temp' files
	for f in glob.glob('Thread*_results.csv'):
		os.remove(f)

# from concurrence 3

@fn_timer
def flattenDict(d, join=add, lift=lambda x: x):
	_FLAG_FIRST = object() # was initially outside of function?
	results = []

	def visit(subdict, results, partial_key):
		for k, v in subdict.items():
			new_key = lift(k) if partial_key == _FLAG_FIRST else join(partial_key, lift(k))
			if isinstance(v, Mapping):
				visit(v, results, new_key)
			else:
				results.append((new_key, v))

	visit(d, results, _FLAG_FIRST)
	return results

@fn_timer
def combine_threads():

	basename = 'cooccurrence_matrix\d+\.json'
	output_name = './data/coexistences.json'

	files_folder = './'
	files = [f for f in os.listdir(files_folder) if re.match(basename, f)]

	final_matrix = Counter({})

	for f in files:
		print('Combining results from {}'.format(f))
		with open(f, 'r') as fin:
			partial_matrix = json.load(fin)
			partial_matrix_flatten = Counter(dict(flattenDict(partial_matrix, join=lambda a, b: a + '_' + b)))
			final_matrix += partial_matrix_flatten
		with open(output_name, 'w') as fout:
			json.dump(final_matrix, fout, sort_keys=True, indent=4)

	for f in glob.glob('cooccurrence_matrix*.json'):
		os.remove(f)

def get_solr_facets():
	try:
		# this module gets facets from solr and returns a dict, df and csv file
		# print("facets_name,facets_count")
		results = []
		#the inital search for facets
		q = "*:*"
		facet = "crt_type_ft"
		query_params = {
			"q" : q,
			"wt" : "json",
			"rows": 0,
			"facet": "true",
			"facet.field": facet,
			"facet.limit": -1,
			"facet.sort": "count",
			"facet.mincount": "1"
		}
		response = requests.get('http://cocoa.ebi.ac.uk:8989/solr/merged/select', params=query_params)
		facets = response.json()['facet_counts']['facet_fields'][facet]

		 # selects data to build dict and strips '_facet' no fancy regex because solr strips other underscores
		facets_name_raw = facets[::2]
		facets_name = [s.replace('_facet', '') for s in facets_name_raw ]
		facets_count = facets[1::2]

		facets_dict = {}
		for i in range(len(facets_name)):
			facets_dict[facets_name[i]] = facets_count[i]

		facets_df = pd.DataFrame.from_dict(facets_dict, orient = 'index')
		facets_df.reset_index(inplace=True)
		facets_df.columns = ['facet','frequency']

		# facets_list = facets_dict.keys() # list if needed

		facets_df.to_csv('./data/attributes.csv', encoding='utf-8')
		print('cocoa query succesful')

	except:
		print('cocoa failed to launch')

		# try:
		# 	print('cocoa failed to launch. Trying beans...')


		# 	results = []
		# 	#the inital search for facets
		# 	q = "*:*"
		# 	facet = "crt_type_ft"
		# 	query_params = {
		# 	    "q" : q,
		# 	    "wt" : "json",
		# 	    "rows": 0,
		# 	    "facet": "true",
		# 	    "facet.field": facet,
		# 	    "facet.limit": -1,
		# 	    "facet.sort": "count",
		# 	    "facet.mincount": "1"
		# 	}
		# 	response = requests.get('http://beans.ebi.ac.uk:8989/solr/merged/select', params=query_params)
		# 	facets = response.json()['facet_counts']['facet_fields'][facet]

		# 	 # selects data to build dict and strips '_facet' no fancy regex because solr strips other underscores
		# 	facets_name_raw = facets[::2]
		# 	facets_name = [s.replace('_facet', '') for s in facets_name_raw ]
		# 	facets_count = facets[1::2]

		# 	facets_dict = {}
		# 	for i in range(len(facets_name)):
		# 		facets_dict[facets_name[i]] = facets_count[i]

		# 	facets_df = pd.DataFrame.from_dict(facets_dict, orient = 'index')
		# 	facets_df.reset_index(inplace=True)
		# 	facets_df.columns = ['facet','frequency']

		# 	# facets_list = facets_dict.keys() # list if needed

		# 	facets_df.to_csv('./data/attributes.csv', encoding='utf-8')


		# 	print('beans success. WARNING: not using cocoa data!!!')
		# except:
		# 	print('cocoa and beans failed to launch.')


if __name__ == "__main__":





	# generates attributes.csv

	get_solr_facets()

	# generates 'samples.csv' and 'coexistences.json'

	# multithread_crawler()
	# stripID()
	# trigger_matrix()
	# combine_threads()

	# generates values

	# Trish has written a program to do this. I need her to send it to me.
	# I may truncate the results her program generates to speed up its progress
	# We could adjust this later if we need to in v1.1













