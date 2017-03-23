#!/usr/bin/env python3
import sys
import os
import zipfile
import urllib.request as request
import time
import getopt
import json
import datetime
import shutil
import subprocess
import xml.etree.cElementTree as ET
import xml.dom.minidom as minidom


def main(argv):
	## default values
	config_file = ''
	base_dir=os.path.abspath(os.getcwd())
	found_config = False
	cleanonly = False
	num_cycles = 3

	## first read terminal arguments
	try:
		opts, args = getopt.getopt(argv,"wc:h",["workingdir","configfile=","help", "clean=", "cycles="])
	except (getopt.GetoptError, err):
		print(str(err))
		print(help_str())
		sys.exit(SQLiteBenchmarker.EXIT_ERROR)
	for opt, arg in opts:
		if opt in ("-w", "--workingdir"):
			base_dir = os.path.abspath(arg)
		elif opt in ("-c", "--configfile"):
			config_file = os.path.abspath(arg)
			found_config = True
		elif opt == "--clean":
			cleanonly = True
			found_config = True
		elif opt == "--cycles":
			num_cycles = int(arg)
		else:
			print (help_str())
			sys.exit(SQLiteBenchmarker.EXIT_ERROR)

	if cleanonly:
		SQLiteBenchmarker.clean(base_dir)
		sys.exit(SQLiteBenchmarker.EXIT_CLEAN_ONLY)

	if not found_config:
		print (help_str())
		sys.exit(SQLiteBenchmarker.EXIT_ERROR)


	## start single run of benchmark for standalone execution
	print("\n__ Starting new benchmark __")
	bmk = SQLiteBenchmarker(base_dir=base_dir, config_file=config_file, num_cycles = num_cycles)
	c_result = bmk.compile()
	if c_result == SQLiteBenchmarker.EXIT_SUCCESS:
		bmk.run_benchmark()
	else:
		sys.exit(SQLiteBenchmarker.EXIT_ERROR)


class SQLiteBenchmarker:
	## exit flags
	EXIT_SUCCESS = 0
	EXIT_CLEAN_ONLY = 1
	EXIT_ERROR = 2

	def __init__(self, base_dir, config_file, num_cycles):
		self.base_dir = base_dir
		self.config_file = config_file
		self.num_cycles = num_cycles

		url_sqlite_source = "https://sqlite.org/2017/sqlite-amalgamation-3160200.zip"
		name_local_zip = "sqlite-amalgamation-3160200.zip"
		name_expected_folder_in_zip = 'sqlite-amalgamation-3160200'
		name_desired_folder_source = 'sqlite-source'
		name_expected_source_file = 'sqlite3.c'
		name_local_zip_benchmarking_tool = "py-tpcc-master.zip"
		name_desired_folder_benchmark = "benchmark"
		name_expected_sub_folder_inside_benchmark = "pytpcc"
		name_expected_benchmark_file = "tpcc.py"
		name_expected_benchmark_internal_config_file = "sqlite.config"
		name_local_bmk_db = 'sqlite_benchmark.db'

		## load configuration for compilation from file
		with open(self.config_file) as json_data:
			self.config = json.load(json_data)
			print("config:" + str(self.config))

		## get source for sqlite
		source_exists = os.path.isfile(os.path.join(self.base_dir, name_desired_folder_source, name_expected_source_file))
		zip_sqlite_exists = os.path.isfile(name_local_zip)

		if not source_exists:
			print('Getting sqlite source')
			if not zip_sqlite_exists:
				request.urlretrieve (url_sqlite_source, name_local_zip)
			zip_ref = zipfile.ZipFile(name_local_zip, 'r')
			zip_ref.extractall('./')
			zip_ref.close()
			os.remove(name_local_zip)
			os.rename(name_expected_folder_in_zip, name_desired_folder_source)

		## downloading and configuring benchmark TPC-C
		os.chdir(self.base_dir)
		path_to_bm_zip = os.path.join(self.base_dir, name_local_zip_benchmarking_tool)
		bm_exists = os.path.exists(os.path.join(
			self.base_dir, name_desired_folder_benchmark,
			name_expected_sub_folder_inside_benchmark,
			name_expected_benchmark_file))
		zip_bm_exists = os.path.exists(path_to_bm_zip)
		self.bm_path = os.path.join(self.base_dir, name_desired_folder_benchmark)
		self.bm_exec_path = os.path.join(self.bm_path, name_expected_sub_folder_inside_benchmark)
		self.bm_config_path = os.path.join(self.bm_exec_path, name_expected_benchmark_internal_config_file)
		self.db_path = os.path.join(self.base_dir, name_local_bmk_db)

		if not bm_exists:
			print('Getting benchmark')
			if not zip_bm_exists:
				request.urlretrieve ("https://github.com/apavlo/py-tpcc/archive/master.zip", path_to_bm_zip)
			bm_tmp_path = os.path.join(self.base_dir, 'benchmark-tmp')
			zip_ref = zipfile.ZipFile(path_to_bm_zip, 'r')
			zip_ref.extractall(bm_tmp_path)
			zip_ref.close()
			os.remove(path_to_bm_zip)
			print(os.path.join(self.base_dir, 'benchmark-tmp', 'py-tpcc-master'))
			os.rename(os.path.join(self.base_dir, 'benchmark-tmp', 'py-tpcc-master'), self.bm_path)
			os.rmdir(bm_tmp_path)

		print('Finished initialising.')


	def compile(self):
		""" Compiles the sqlite source according to the compile configuration """
		## compile source
		print('Compiling source')
		os.chdir(os.path.join(self.base_dir, 'sqlite-source'))
		compile_command = SQLiteBenchmarker.get_compile_string(self.config["features"])
		print("compiling: " + compile_command)
		c_result = os.system(compile_command)
		print('Finished compiling')
		return c_result

	def run_benchmark(self):
		""" Runs benchmark a given number of times on previousely compiled sqlite """

		## check if config dict has a field measurements
		if not hasattr(self.config, "measurements" ):
			self.config["measurements"] = []

		self.measurements = self.config["measurements"]

		## need to change dir to benchmark root for correct execution
		os.chdir(os.path.join(self.bm_path, 'pytpcc'))
		os.system('python tpcc.py --print-config sqlite > ' + self.bm_config_path)

		#adjust config
		filedata = None
		#read internal benchmarking config for sqlite
		with open(self.bm_config_path, 'r') as file :
			filedata = file.read()
		# Replace the target string for benchmark database
		filedata = filedata.replace('/tmp/tpcc.db', self.db_path)
		# Write the file out again
		with open(self.bm_config_path, 'w') as file:
			file.write(filedata)
		# let 'sqlite3' point to newly compiled file
		print('Adding folder of newly compiled binary to PATH')
		os.environ["PATH"] = os.path.join(os.path.abspath(self.base_dir), 'sqlite-source') \
								+ os.pathsep + os.environ["PATH"]
		## start benchmark
		print('starting benchmark')
		benchmark_command = "python tpcc.py --reset --config=sqlite.config sqlite --debug"

		## run benchmark self.num_cycles times
		for n in range(self.num_cycles):
			self.current_measurement = {}
			self.current_measurement["start_human_readable"] = datetime.datetime.now().isoformat()
			self.current_measurement["start"] = cur_milli()
			print('##>>' + milli_str(self.current_measurement["start"]) + '>>') # print time in milliseconds

			# comment in two below lines to run benchmark;
			# comment them out and comment in sleep ommand to fake benchmarking
			#proc = subprocess.Popen([benchmark_command], stdout=subprocess.PIPE, shell=True)
			#(out, err) = proc.communicate()
			time.sleep(0.1)

			self.current_measurement["finish"] = cur_milli()
			print('##<<' + milli_str(self.current_measurement["finish"]) + '<<') # print time in milliseconds
			self.current_measurement["cost_in_seconds"] = round((self.current_measurement["finish"] - self.current_measurement["start"])/100)/10
			self.config["measurements"].append(self.current_measurement)
			self.write_result()
			print("\f finished benchmark run #" + str(n))

		print('__ benchmark finished __\n\n')

	def write_result(self):
		""" writes result of last benchmark run to its corresponding config file """
		print('Appending result to original config file.')
		with open(self.config_file, 'w') as f:
			f.seek(0)
			f.write(json.dumps(self.config, indent=4, sort_keys=True))
			f.truncate()



	@staticmethod
	def write_all_in_one_result_file(base_dir):
		""" Writes all results, that are integrated in their respective
		config files, into one json file as well as a XML file for
		legacy systems"""
		file_content = {}
		results = []
		config_folder = os.path.join(base_dir, 'compile-configs')
		file_list = os.listdir(config_folder)

		## iterate over all configs, which carry their benchmark results
		for filename in file_list:
			abs_file = os.path.join(config_folder, filename)
			with open(abs_file) as json_data:
				config = json.load(json_data)

				## check if benchmark has successfull been run and extract info
				if "measurements" in config:
					features = config["features"]
					new_config = {}
					config_id = SQLiteBenchmarker.get_id_from_config(features)
					new_config["id"] = config_id
					cmd = SQLiteBenchmarker.get_compile_string(features)
					new_config["command"] = cmd
					new_config["measurements"] = config["measurements"]
					results.append(new_config)

		## write aggregated results object as json
		file_content["results"] = results
		with open(os.path.join(base_dir, 'all-in-one-results.json'), 'w') as f:
			f.seek(0)
			f.write(json.dumps(file_content, indent=4, sort_keys=True))
			f.close()

		## write a beautiful XML file
		root = ET.Element("results")

		# append one node for each compile configuration
		for n in range(len(results)):
			result = results[n]
			result_node = ET.SubElement(root, "result", id=result["id"])
			result_id_node = ET.SubElement(result_node, "id")
			result_id_node.text = result["id"]
			result_cmd_node = ET.SubElement(result_node, "command")
			result_cmd_node.text = result["command"]

			result_measurements_node = ET.SubElement(result_node, "measurements")
			measurements = result["measurements"]

			# add one node for each benchmark run
			for i in range(len(measurements)):
				measurement = measurements[i]
				measurement_node = ET.SubElement(result_measurements_node, "measurement", id=str(i))
				cost_in_seconds_node = ET.SubElement(measurement_node, "cost-in-seconds")
				cost_in_seconds_node.text = str(measurement["cost_in_seconds"])
				finish_node = ET.SubElement(measurement_node, "finish")
				finish_node.text = str(measurement["finish"])
				start_node = ET.SubElement(measurement_node, "start")
				start_node.text = str(measurement["start"])
				start_human_readable_node = ET.SubElement(measurement_node, "start-human-readable")
				start_human_readable_node.text = str(measurement["start_human_readable"])


		# take tree and make a pretty string (improve readability)
		xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")

		# write result
		with open(os.path.join(base_dir, 'all-in-one-results.xml'), 'w') as f:
			f.seek(0)
			f.write(xmlstr)
			f.close()

	@staticmethod
	def get_id_from_config(config):
		""" generates an identification string from a compile config """
		seperation_str = "%;%"
		value_seperator = ""

		id = seperation_str
		## iterate over all compile options and add something to the id string
		for option, value in config.items():
			if value is None:
				add_string = option
			else:
				add_string = option + value_seperator +  str(value)

			id += add_string + seperation_str
		return id

	@staticmethod
	def get_compile_string(features):
		""" takes a features dict and generates the command that will compile
		sqlite with the features in the given dict """
		compile_command = "gcc -o sqlite3 shell.c sqlite3.c -lpthread -ldl"

		for option, value in features.items():
			add_string = " -D"
			if value is None:
				add_string += option
			else:
				add_string += option + "=" + str(value)
			compile_command += add_string
		return compile_command

	@staticmethod
	def clean(base_dir):
		""" deletes all files that could be created by
		this class at some point """
		bmk_path = os.path.join(base_dir, 'benchmark')
		src_path = os.path.join(base_dir, 'sqlite-source')
		db_path = os.path.join(base_dir, 'sqlite_benchmark.db')
		all_in_one_results_xml_path = os.path.join(base_dir, 'all-in-one-results.xml')
		all_in_one_results_json_path = os.path.join(base_dir, 'all-in-one-results.json')
		all_in_one_results_json_path = os.path.join(base_dir, 'all-in-one-results.json')
		zip_source = os.path.join(base_dir, 'sqlite-amalgamation-3160200.zip')
		zip_bmk = os.path.join(base_dir, 'py-tpcc-master.zip')

		try:
			if os.path.exists(bmk_path):
				shutil.rmtree(bmk_path)
			if os.path.exists(src_path):
				shutil.rmtree(src_path)
			if os.path.exists(db_path):
				os.remove(db_path)
			if os.path.exists(all_in_one_results_xml_path):
				os.remove(all_in_one_results_xml_path)
			if os.path.exists(all_in_one_results_json_path):
				os.remove(all_in_one_results_json_path)
			if os.path.exists(zip_source):
				os.remove(zip_source)
			if os.path.exists(zip_bmk):
				os.remove(zip_bmk)
		except err:
			print("Could'nt delete files.")


def cur_milli():
	""" returns current time in milliseconds from some zero point in time """
	return time.time()*1000


def cur_milli_str():
	""" returns current time as a string of
	milliseconds from some zero point in time """
	return str(int(round(cur_milli())))


def milli_str(milli):
	""" returns a string of the result of rounding the in """
	return str(int(round(milli)))


def help_str():
	return "USAGE: sqlite-bmk.py -c compile-conf.json"

if __name__ == "__main__":
   main(sys.argv[1:])
