#!/usr/bin/env python3
import sys
import os
import zipfile
import urllib
import time
import getopt
import json
import datetime

def main(argv):
	config_file = ''
	base_dir=os.path.abspath(os.getcwd())
	found_config = False
	try:
		opts, args = getopt.getopt(argv,"wc:h",["workingdir","configfile=","help"])
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
		else:
			print (help_str())
			sys.exit(2)

	if not found_config:
		print (help_str())
		sys.exit(2)

	bmk = SQLiteBenchmarker(base_dir=base_dir, config_file=config_file)
	bmk.compile()
	bmk.run_benchmark()


class SQLiteBenchmarker:
	def __init__(self, base_dir, config_file):
		self.base_dir = base_dir
		self.config_file = config_file

		with open(self.config_file) as json_data:
			self.config = json.load(json_data)
			print("config:\n" + str(self.config) + "\n")

		## get source
		source_exists = os.path.isfile(os.path.join(self.base_dir, 'sqlite-source', 'sqlite3.c'))
		zip_sqlite_exists = os.path.isfile('sqlite-amalgamation-3160200.zip')

		if not source_exists:
			print('Getting sqlite source')
			if not zip_sqlite_exists:
				urllib.urlretrieve ("https://sqlite.org/2017/sqlite-amalgamation-3160200.zip", "sqlite-amalgamation-3160200.zip")
			zip_ref = zipfile.ZipFile('sqlite-amalgamation-3160200.zip', 'r')
			zip_ref.extractall('./')
			zip_ref.close()
			os.remove("sqlite-amalgamation-3160200.zip")
			os.rename('sqlite-amalgamation-3160200', 'sqlite-source')

		## downloading and configuring benchmark TPC-C
		os.chdir(self.base_dir)
		path_to_bm_zip = os.path.join(self.base_dir, 'py-tpcc-master.zip')
		bm_exists = os.path.exists(os.path.join(self.base_dir, 'benchmark', 'pytpcc', 'tpcc.py'))
		zip_bm_exists = os.path.exists(path_to_bm_zip)
		self.bm_path = os.path.join(self.base_dir, 'benchmark')
		bm_exec_path = os.path.join(self.bm_path, 'pytpcc')
		self.bm_config_path = os.path.join(bm_exec_path, 'sqlite.config')
		self.db_path = os.path.join(self.base_dir, 'sqlite_benchmark.db')

		if not bm_exists:
			print('Getting benchmark')
			if not zip_bm_exists:
				urllib.urlretrieve ("https://github.com/apavlo/py-tpcc/archive/master.zip", path_to_bm_zip)
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
		os.system(compile_command)
		print('Finished compiling')


	def run_benchmark(self):
		self.measurements = {}
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
		self.measurements["start_human_readable"] = datetime.datetime.now().isoformat()
		self.measurements["start"] = cur_milli()
		print('##>>' + milli_str(self.measurements["start"]) + '>>') # print time in milliseconds

		#os.system("python tpcc.py --reset --config=sqlite.config sqlite --debug")
		time.sleep(1.5)
		self.measurements["finish"] = cur_milli()
		print('##<<' + milli_str(self.measurements["finish"]) + '<<') # print time in milliseconds
		self.measurements["cost_in_seconds"] = round((self.measurements["finish"] - self.measurements["start"])/100)/10
		print('benchmark finished')
		self.config["measurements"] = self.measurements

		self.write_result()

	def write_result(self):
		print('Appending result to original config file.')
		with open(self.config_file, 'w') as f:
			f.seek(0)
			f.write(json.dumps(self.config, indent=4, sort_keys=True))
			f.truncate()


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
