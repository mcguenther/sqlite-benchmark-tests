import os
import zipfile
import urllib
from git import Repo

## get source
source_exists = os.path.exists('./sqlite-source/sqlite3.c') 
zip_exists = os.path.isfile('sqlite-amalgamation-3160200.zip') 
print('\n')
if not source_exists:
	print('Getting sqlite source')
	if not zip_exists:
		#os.system("wget https://sqlite.org/2017/sqlite-amalgamation-3160200.zip")
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





print('Finished - exiting.')
