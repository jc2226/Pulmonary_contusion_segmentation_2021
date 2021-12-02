import os
import sys
import shutil

def create_batch(batch_size, patient_path, destination_dir):
	list_of_studies = os.listdir(patient_path)
	logFile = open('create_batch.log', 'w')
	for i in range(batch_size):
		fpath = os.path.join(patient_path, list_of_studies[i])
		if os.path.isdir(fpath):
			print("Moving study: ", list_of_studies[i], file=logFile)
			shutil.move(fpath)

if __name__ == '__main__':
	create_batch(sys.argv[1], sys.argv[2], sys.argv[3])



