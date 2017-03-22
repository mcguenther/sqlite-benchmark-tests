#!/usr/bin/env python3
import sys
import os
import zipfile
import urllib
import time
import getopt
import json
import datetime
import random
from sqlite_bmk import SQLiteBenchmarker
from config_creator import ConfigCreator

#import sqlite-bmk
#import config-creator

def main(argv):
	options_file = ''
	base_dir=os.path.abspath(os.getcwd())
	num_random = 100
	num_cycles = 3
	found_options = False
	try:
		opts, args = getopt.getopt(argv,"o:hf:r:c:",["optionsfile=", "help", "fresh-start", "clean=", "random=", "cycles="])
	except (getopt.GetoptError, err):
		print(str(err))
		print(help_str())
		sys.exit(2)
	#print(opts)
	for opt, arg in opts:
		if opt in ("-o", "--optionsfile"):
			options_file = os.path.abspath(arg)
			found_options = True
		elif opt == "--clean":
			clean_all(base_dir)
			sys.exit(1)
			found_options = True
		elif opt in ("-f", "--fresh-start"):
			clean_all(base_dir)
			found_options = True
		elif opt in ("-r", "--random"):
			num_random = int(arg)
			found_options = True
		elif opt in ("-c", "--cycles"):
			num_cycles = int(arg)
		else:
			print (help_str())
			sys.exit(2)

	if not found_options:
		print (help_str())
		sys.exit(2)

	generator = ConfigCreator(base_dir=base_dir,options_file=options_file)
	generator.generate_and_write_one_for_each_option()
	generator.generate_set_randomly(int(num_random))

	config_folder = os.path.join(base_dir, "compile-configs")
	file_list = os.listdir(config_folder)
	i = 1
	file_num = len(file_list)
	for filename in file_list:
		abs_file = os.path.join(config_folder, filename)
		print("\n\n__ Starting new benchmark " + str(i) + "/" + str(file_num) + " (" + str(round(100*i/file_num)) + "%) __")
		print("config file \"" + filename + "\"")
		bmk = SQLiteBenchmarker(base_dir=base_dir, config_file=abs_file, num_cycles = num_cycles)
		c_result = bmk.compile()
		i += 1
		if c_result is 0:
			bmk.run_benchmark()
		else:
			continue


def help_str():
	return "USAGE: config-creator.py -o compile-options.json"

def clean_all(base_dir):
	ConfigCreator.clean(base_dir)
	SQLiteBenchmarker.clean(base_dir)

if __name__ == "__main__":
	main(sys.argv[1:])
