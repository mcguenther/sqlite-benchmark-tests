#!/usr/bin/env python3
import os
import zipfile
import urllib

base_dir = os.path.abspath(os.getcwd())


## get source
source_exists = os.path.isfile(os.path.join(base_dir, 'sqlite-source', 'sqlite3.c'))
zip_sqlite_exists = os.path.isfile('sqlite-amalgamation-3160200.zip') 
print('\n')
if not source_exists:
	print('Getting sqlite source')
	if not zip_sqlite_exists:
		urllib.urlretrieve ("https://sqlite.org/2017/sqlite-amalgamation-3160200.zip", "sqlite-amalgamation-3160200.zip")
	zip_ref = zipfile.ZipFile('sqlite-amalgamation-3160200.zip', 'r')
	zip_ref.extractall('./')
	zip_ref.close()
	os.remove("sqlite-amalgamation-3160200.zip")
	os.rename('sqlite-amalgamation-3160200', 'sqlite-source')

	## compile source
	print('Compiling source')
	os.chdir('./sqlite-source')
	os.system("gcc -o sqlite3 shell.c sqlite3.c -lpthread -ldl")



## downloading and configuring benchmark TPC-C
os.chdir(base_dir)
path_to_bm_zip = os.path.join(base_dir, 'py-tpcc-master.zip')
bm_exists = os.path.exists(os.path.join(base_dir, 'benchmark', 'pytpcc', 'tpcc.py'))
zip_bm_exists = os.path.exists(path_to_bm_zip)
bm_path = os.path.join(base_dir, 'benchmark')
bm_exec_path = os.path.join(bm_path, 'pytpcc')
bm_config_path = os.path.join(bm_exec_path, 'sqlite.config')
db_path = os.path.join(base_dir, 'sqlite_benchmark.db')

if not bm_exists:
	print('Getting benchmark')
	if not zip_bm_exists:
		urllib.urlretrieve ("https://github.com/apavlo/py-tpcc/archive/master.zip", path_to_bm_zip)
	bm_tmp_path = os.path.join(base_dir, 'benchmark-tmp')
	zip_ref = zipfile.ZipFile(path_to_bm_zip, 'r')
	zip_ref.extractall(bm_tmp_path)
	zip_ref.close()
	os.remove(path_to_bm_zip)
	print(os.path.join(base_dir, 'benchmark-tmp', 'py-tpcc-master'))
	os.rename(os.path.join(base_dir, 'benchmark-tmp', 'py-tpcc-master'), bm_path)
	os.rmdir(bm_tmp_path)


os.chdir(os.path.join(bm_path, 'pytpcc'))
os.system('python tpcc.py --print-config sqlite > ' + bm_config_path)

#adjust config
filedata = None
#read config
with open(bm_config_path, 'r') as file :
	filedata = file.read()
# Replace the target string
filedata = filedata.replace('/tmp/tpcc.db', db_path)

# Write the file out again
with open(bm_config_path, 'w') as file:
	file.write(filedata)

# let 'sqlite3' point to newly compiled file
print('Adding folder of newly compiled binary to PATH')
os.environ["PATH"] = os.path.join(os.path.abspath(base_dir), 'sqlite-source') + os.pathsep + os.environ["PATH"]
print('testing custom sqlite3')
print(os.environ["PATH"] )

## start benchmark
print('starting benchmark')
os.system("python tpcc.py --reset --config=sqlite.config sqlite --debug")  


print('Finished - exiting.')
