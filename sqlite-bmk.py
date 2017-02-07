#!/usr/bin/env python3
import sys
import os
import zipfile
import urllib
import time
import getopt

def main(argv):
	config_file = ''
	base_dir=os.path.abspath(os.getcwd())
	found_config = False
	try:
		opts, args = getopt.getopt(argv,"wc:h",["workingdir","configfile=","help"])
	except getopt.GetoptError, err:
		print(str(err))
		print help_str()
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-w", "--workingdir"):
			base_dir = os.path.abspath(arg)
		elif opt in ("-c", "--configfile"):
			config_file = os.path.abspath(arg)
			found_config = True
		else:
			print help_str()
			sys.exit(2)

	if not found_config:
		print help_str()
		sys.exit(2)

	bmk = SQLiteBenchmarker(base_dir=base_dir)
	bmk.set_config(config_file)
	bmk.compile()
	bmk.run_benchmark()


class SQLiteBenchmarker:
	def __init__(self, base_dir):
		self.base_dir = base_dir


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


	def set_config(self, file):
		pass

	def compile(self):
		## compile source
		print('Compiling source')
		os.chdir(os.path.join(self.base_dir, 'sqlite-source'))
		os.system("gcc -o sqlite3 shell.c sqlite3.c -lpthread -ldl")
		print('Finished compiling')


	def run_benchmark(self):
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
		self.last_start = cur_milli()
		print('##>>' + milli_str(self.last_start) + '>>') # print time in milliseconds
		os.system("python tpcc.py --reset --config=sqlite.config sqlite --debug") 
		self.last_finish = cur_milli() 
		print('##<<' + milli_str(self.last_finish) + '<<') # print time in milliseconds
		print('benchmark finished')

		#TODO create result JSON 
		self.write_result(0)

	def write_result(self, json):
		print('Appending result to original config file.')
		pass


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