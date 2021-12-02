import pydicom as dicom
import os
import sys
import csv
import pandas as pd
import shutil
from clean_contusion_masks import calculate_contusion

def parseCsv(input_file):
	df = pd.read_csv(input_file)
	return df

def load_scan(scan_num, patient_path):
    list_of_scans = os.listdir(patient_path)
    scan_path = os.path.join(patient_path,list_of_scans[scan_num])
    list_of_slices = os.listdir(scan_path)
    return list_of_slices, scan_path

def check_if_diff_nifti(series_path):
	for file in os.listdir(series_path):
		if "_diff.nii.gz" in file:
			return True, file
	return False, ""

def grab_dcm_file(series_path):
	for file in os.listdir(series_path):
		if ".dcm" in file:
			return file


def explore_patient(patient_path,csv_file, logFile, patient_destination_dir):
	data_frame = parseCsv(csv_file)
	series = os.listdir(patient_path)

	any_series_exists = False
	for i in range (len(series)):
		list_of_slices, scan_path = load_scan(i, patient_path)
		dcm = grab_dcm_file(scan_path)
		slice_path = os.path.join(scan_path,dcm)
		# read in the full path to the file as ds
		ds=dicom.read_file(slice_path)
		print("Patient ID: ", ds.PatientID, file = logFile)
		print("AccessionNumber: ", ds.AccessionNumber, file = logFile)
		print("StudyInstanceUID: ", ds.StudyInstanceUID, file = logFile)
		print("SeriesInstanceUID: ", ds.SeriesInstanceUID, file = logFile)
		exists = ds.SeriesInstanceUID in data_frame['series_instance'].to_list()
		print("Found in csv: ", exists, file = logFile)
		any_series_exists = any_series_exists and exists

	if not any_series_exists:
		# move the patient directory to the destination
		print("MOVING PATIENT....", file = logFile)
		shutil.move(patient_path, patient_destination_dir)
	
	return data_frame


def main(folder_with_all_patients, csv_file, destination_dir):
	patients = os.listdir(folder_with_all_patients)
	logFile = open('move_unprocessed_patients.log', 'w')
	for patient_folder in patients:
		print("******************************************************", file = logFile)
		print("*********************New Patient**********************", file = logFile)
		print("******************************************************", file = logFile)
		patient_destination_dir = os.path.join(destination_dir, patient_folder)
		df = explore_patient(os.path.join(folder_with_all_patients, patient_folder), csv_file, logFile, patient_destination_dir)
		#df.to_csv('cv_processed_11_13.csv', index=False)
		

if __name__ == '__main__':
	main(sys.argv[1], sys.argv[2], sys.argv[3])
