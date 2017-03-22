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

def main(argv):
	config_file = ''
	base_dir=os.path.abspath(os.getcwd())
	found_config = False
	cleanonly = False
	num_cycles = 3
	try:
		opts, args = getopt.getopt(argv,"wc:h",["workingdir","configfile=","help", "clean=", "cycles="])
	except (getopt.GetoptError, err):
		print(str(err))
		print(help_str())
		sys.exit(2)
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
			sys.exit(2)

	if cleanonly:
		SQLiteBenchmarker.clean(base_dir)
		sys.exit(1)

	if not found_config:
		print (help_str())
		sys.exit(2)

	print("\n__ Starting new benchmark __")
	bmk = SQLiteBenchmarker(base_dir=base_dir, config_file=config_file, num_cycles = num_cycles)
	c_result = bmk.compile()
	if c_result is 0:
		bmk.run_benchmark()
	else:
		sys.exit(2)


class SQLiteBenchmarker:
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

		with open(self.config_file) as json_data:
			self.config = json.load(json_data)
			print("config:" + str(self.config))

		## get source
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
		## compile source
		print('Compiling source')
		os.chdir(os.path.join(self.base_dir, 'sqlite-source'))
		compile_command = "gcc -o sqlite3 shell.c sqlite3.c -lpthread -ldl"
		features = self.config["features"]
		for option, value in features.items():
			add_string = " -D"
			if value is None:
				add_string += option
			else:
				add_string += option + "=" + str(value)
			compile_command += add_string
		print("compiling: " + compile_command)
		c_result = os.system(compile_command)
		print('Finished compiling')
		return c_result

	def run_benchmark(self):
		if not hasattr(self.config, "measurements" ):
			self.config["measurements"] = []
		self.measurements = self.config["measurements"]
		os.chdir(os.path.join(self.bm_path, 'pytpcc'))
		os.system('python tpcc.py --print-config sqlite > ' + self.bm_config_path)
		#adjust config
		filedata = None
		#read config
		with open(self.bm_config_path, 'r') as file :
			filedata = file.read()
		# Replace the target string
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

		for n in range(self.num_cycles):
			self.current_measurement = {}
			self.current_measurement["start_human_readable"] = datetime.datetime.now().isoformat()
			self.current_measurement["start"] = cur_milli()
			print('##>>' + milli_str(self.current_measurement["start"]) + '>>') # print time in milliseconds
			proc = subprocess.Popen([benchmark_command], stdout=subprocess.PIPE, shell=True)
			(out, err) = proc.communicate()
			#time.sleep(1)
			self.current_measurement["finish"] = cur_milli()
			print('##<<' + milli_str(self.current_measurement["finish"]) + '<<') # print time in milliseconds
			self.current_measurement["cost_in_seconds"] = round((self.current_measurement["finish"] - self.current_measurement["start"])/100)/10
			self.config["measurements"].append(self.current_measurement)
			self.write_result()
			print("\f finished benchmark run #" + str(n))

		print('__ benchmark finished __\n\n')

	def write_result(self):
		print('Appending result to original config file.')
		with open(self.config_file, 'w') as f:
			f.seek(0)
			f.write(json.dumps(self.config, indent=4, sort_keys=True))
			f.truncate()


	@staticmethod
	def clean(base_dir):
		bmk_path = os.path.join(base_dir, 'benchmark')
		src_path = os.path.join(base_dir, 'sqlite-source')
		db_path = os.path.join(base_dir, 'sqlite_benchmark.db')
		try:
			if os.path.exists(bmk_path):
				shutil.rmtree(bmk_path)
			if os.path.exists(src_path):
				shutil.rmtree(src_path)
			if os.path.exists(db_path):
				os.remove(db_path)
		except err:
			print("Couldnt delete files.")


def cur_milli():
	return time.time()*1000


def cur_milli_str():
	return str(int(round(cur_milli())))


def milli_str(milli):
	return str(int(round(milli)))


def help_str():
	return "USAGE: sqlite-bmk.py -c compile-conf.json"

if __name__ == "__main__":
   main(sys.argv[1:])
