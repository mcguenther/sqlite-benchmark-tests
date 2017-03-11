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

def main(argv):
	options_file = ''
	base_dir=os.path.abspath(os.getcwd())
	found_options = False
	try:
		opts, args = getopt.getopt(argv,"o:wh",["optionsfile=","workingdir","help"])
	except (getopt.GetoptError, err):
		print(str(err))
		print(help_str())
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-w", "--workingdir"):
			base_dir = os.path.abspath(arg)
		elif opt in ("-o", "--optionsfile"):
			options_file = os.path.abspath(arg)
			found_options = True
		else:
			print (help_str())
			sys.exit(2)


	if not found_options:
		print (help_str())
		sys.exit(2)

	generator = ConfigCreator(base_dir=base_dir,options_file=options_file)
	generator.generate_set_randomly(5)



class ConfigCreator:
	def __init__(self, base_dir, options_file):
		self.base_dir = base_dir
		self.options_file = options_file

		with open(self.options_file) as json_data:
			json_data = json.load(json_data)
			self.options = self.parse_options(json_data)
			print("avaliable options:\n" + str(self.options) + "\n")
		print('Finished initialising.')


	def parse_options(self, json):
		options = {}
		possible_options = {}
		if "compile-options" in json:
			print("found correct file")
			json_options = json["compile-options"]

			# We allow
			#  - unary options (take effect on existence)
			#  - set options (can take a value out of a set of allowed values - includes binary options)
			#  - range options (can take any value inside a range, using a given step size)

			for option, value in json_options.items():

				val_dict = {}
				print(option + "=" + str(value))
				if value is None:
					# unary option
						possible_options[option] = None
				else:
					val_type = value["type"]
					val_default = value["default"]
					val_dict["default"] = val_default
					if val_type == "list":
						vals = value["values"]
						val_dict["values"] = vals
						possible_options[option] = val_dict
					elif val_type == "range":
						max_val = value["max"]
						min_val = value["min"]
						stepsize = value["stepsize"]
						possible_values = list(range(min_val,max_val+stepsize,stepsize))
						val_dict["values"] = possible_values
						possible_options[option] = val_dict
					else:
						print("Found unsupported option: " + option + "=" + value)

		options = possible_options
		return options

	def generate_one_for_each_option(self):
		pass


	def write_config(self, config):
		#print('writing new config file')
		#print("generating config wrapper")
		config_wrapper = {}
		config_wrapper["features"] = config
		#print(str(config_wrapper))
		json_conf = json.dumps(config_wrapper, indent=4, sort_keys=True)
		#print("writing file")
		config_folder = os.path.join(self.base_dir, 'compile-configs')
		config_folder_exists = os.path.exists(config_folder)
		if not config_folder_exists:
			os.mkdir(config_folder)
		config_file_name = "config_"
		config_file_name += str(hash(json_conf))
		complete_path = os.path.join(config_folder, config_file_name)
		complete_path +=  ".cfg"
		print(complete_path)
		with open(complete_path, 'w') as f:
			f.seek(0)
			f.write(json_conf)
			f.truncate()

	def generate_randomly(self):
		#print(self.options)
		rand_conf = {}
		for feature, f_desc in self.options.items():
			possible_values = f_desc["values"]
			val = random.choice(possible_values)
			print(str(feature) + " = " + str(val))
			rand_conf[feature] = val
		return rand_conf


	def generate_set_randomly(self,num):
		for i in range(num):
			self.generate_rand_and_save()


	def generate_rand_and_save(self):
		random_config = self.generate_randomly()
		self.write_config(random_config)


def cur_milli():
	return time.time()*1000


def cur_milli_str():
	return str(int(round(cur_milli())))


def milli_str(milli):
	return str(int(round(milli)))

def help_str():
	return "USAGE: config-creator.py -o compile-options.json"

if __name__ == "__main__":
   main(sys.argv[1:])
