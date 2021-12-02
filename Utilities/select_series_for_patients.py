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


def explore_patient(patient_path,csv_file, logFile, selectedSeriesFile):
	data_frame = parseCsv(csv_file)
	series = os.listdir(patient_path)
	data_frame['series_instance'] = ""
	data_frame['percent_contusion'] = 0
	count = 0
	scans_to_delete = []
	for i in range (len(series)):
		list_of_slices, scan_path = load_scan(i, patient_path)
		dcm = grab_dcm_file(scan_path)
		slice_path = os.path.join(scan_path,dcm)
		# read in the full path to the file as ds
		ds=dicom.read_file(slice_path)
		row = data_frame.index[data_frame['anon_mrn'] == ds.PatientID]
		print("Patient ID: ", ds.PatientID, file = logFile)
		print("AccessionNumber: ", ds.AccessionNumber, file = logFile)
		print("SeriesInstanceUID: ", ds.SeriesInstanceUID, file = logFile)
		print("Number of slices: ", len(list_of_slices), file = logFile)
		if len(list_of_slices) > 150:
			if hasattr(ds, 'SliceThickness') and ds.SliceThickness < 2.5:
				print("Slice Thickness: ", ds.SliceThickness, file=logFile)
				print(ds.PatientID, ",", ds.SeriesInstanceUID, file = selectedSeriesFile)
		else:
			scans_to_delete.append(scan_path)
		count = count + 1

	for i in range(len(scans_to_delete)):
		shutil.rmtree(scans_to_delete[i])
		


	print("Count: ", count, file = logFile)
	return data_frame


def main(folder_with_all_patients, csv_file):
	patients = os.listdir(folder_with_all_patients)
	logFile = open('ct_metadata_selector.log', 'w')
	selectedSeriesFile = open('patient_to_selected_series.csv', 'w')
	for patient_folder in patients:
		print("******************************************************", file = logFile)
		print("*********************New Patient**********************", file = logFile)
		print("******************************************************", file = logFile)
		df = explore_patient(os.path.join(folder_with_all_patients, patient_folder), csv_file, logFile, selectedSeriesFile)
		df.to_csv('patient_to_selected_series.csv', index=False)
		

if __name__ == '__main__':
	main(sys.argv[1], sys.argv[2])
