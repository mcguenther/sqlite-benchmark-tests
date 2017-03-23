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
import shutil
from sqlite_bmk import SQLiteBenchmarker


def main(argv):
	options_file = ''
	base_dir=os.path.abspath(os.getcwd())
	num_random = 30
	found_options = False
	cleanonly = False
	try:
		opts, args = getopt.getopt(argv,"o:whr:",["optionsfile=","workingdir","help", "num-random=", "clean"])
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
		elif opt in ("-r", "--num-random"):
			num_random = arg
			found_options = True
		elif opt == "--clean":
			cleanonly = True
		else:
			print (help_str())
			sys.exit(2)

	if cleanonly:
		ConfigCreator.clean(base_dir)
		sys.exit(1)

	if not found_options:
		print (help_str())
		sys.exit(2)

	generator = ConfigCreator(base_dir=base_dir,options_file=options_file)

	#non_default = generator.generate_non_default_single_option("SQLITE_TEMP_STORE")
	generator.generate_and_write_one_for_each_option()
	generator.generate_set_randomly(int(num_random))



class ConfigCreator:
	def __init__(self, base_dir, options_file):
		self.base_dir = base_dir
		self.options_file = options_file

		#print("base" + self.base_dir)
		#print("options_file" + self.options_file)
		with open(self.options_file) as json_data:
			json_data = json.load(json_data)
			self.options = self.parse_options(json_data)
			#print("avaliable options:\n" + str(self.options) + "\n")
		print('Finished initialising.')


	def parse_options(self, json):
		options = {}
		possible_options = {}
		if "compile-options" in json:
			#print("found correct file")
			json_options = json["compile-options"]

			# We allow
			#  - unary options (take effect on existence)
			#  - set options (can take a value out of a set of allowed values - includes binary options)
			#  - range options (can take any value inside a range, using a given step size)

			for option, value in json_options.items():
				val_dict = {}
				#print(option + "=" + str(value))
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


	def write_config(self,
		config,
		suffix = ""):
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
		if suffix is not "":
			config_file_name += suffix + "_"
		config_file_name += str(hash(json_conf))
		complete_path = os.path.join(config_folder, config_file_name)
		complete_path +=  ".cfg"
		#print(complete_path)
		with open(complete_path, 'w') as f:
			f.seek(0)
			f.write(json_conf)
			f.truncate()

	def generate_randomly(self):
		#print(self.options)
		rand_conf = {}
		for feature, f_desc in self.options.items():
			if f_desc is None:
				#unary option
				on = bool(random.getrandbits(1))
				if on:
					rand_conf[feature] = None
			else:
				possible_values = f_desc["values"]
				val = random.choice(possible_values)
				#print(str(feature) + " = " + str(val))
				rand_conf[feature] = val
		return rand_conf


	def generate_set_randomly(self,num):
		for i in range(num):
			self.generate_rand_and_write()


	def generate_rand_and_write(self):
		random_config = self.generate_randomly()
		self.write_config(random_config, suffix="rnd")


	def generate_and_write_one_for_each_option(self):
		for options in self.options:
			non_default_option = self.generate_non_default_single_option(options)
			self.write_config(non_default_option, suffix=options)


	def generate_non_default_single_option(self, option):
		if option not in self.options:
			raise ValueError('Can find no non-default value for option ' +
				option + " since it is not in the parsed set of options")
		option_desc = self.options[option]
		#print(option_desc)
		possible_vals= []

		if option_desc is None:
			# unary option
			possible_vals = [None]
		else:
			val_default = option_desc["default"]
			possible_vals = option_desc["values"]
			if val_default in possible_vals:
				possible_vals.remove(val_default)

		val = random.choice(possible_vals)
		#print(str(option) + " = " + str(val))
		rand_conf = {}
		rand_conf[option] = val
		return rand_conf

	def write_all_in_one_config_file(self):
		file_content = ''
		config_folder = os.path.join(self.base_dir, 'compile-configs')
		file_list = os.listdir(config_folder)
		file_num = len(file_list)
		for filename in file_list:
			abs_file = os.path.join(config_folder, filename)
			with open(abs_file) as json_data:
				config = json.load(json_data)
				compile_command = SQLiteBenchmarker.get_compile_string(config["features"])
				file_content += compile_command + "\n"

		with open(os.path.join(self.base_dir, 'all-in-one.cfg'), 'w') as f:
			f.seek(0)
			f.write(file_content)
			f.close()


	@staticmethod
	def clean(base_dir):
		cfg_path = os.path.join(base_dir, 'compile-configs')
		all_in_one_cmd_path = os.path.join(base_dir, 'all-in-one.cfg')
		try:
			if os.path.exists(cfg_path):
				shutil.rmtree(cfg_path)
			if os.path.exists(all_in_one_cmd_path):
				os.remove(all_in_one_cmd_path)
		except:
			print("Couldnt delete files")


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
