import pydicom as dicom
import os
import sys
import csv
import pandas as pd
from os.path import exists
from clean_contusion_masks import calculate_og_contusion
from clean_contusion_masks import calculate_vesselness_contusion
from clean_contusion_masks import perform_lung_segmentations
from clean_contusion_masks import calculate_vesselness_contusion_over_full_lung
from clean_contusion_masks import calculate_vessel_percent

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

def series_was_processed_for_vessels(series_path):
	subdir_components = os.listdir(series_path)
	splitPath = series_path.split("/")
	subdir = splitPath[len(splitPath)-1]
	myCont_mask_filename = subdir + "_contusion.nii.gz"
	vesselness_lung_filename = subdir + "_vesselness.nii.gz"

	myCont_filepath = os.path.join(series_path, myCont_mask_filename)
	vesselness_filepath = os.path.join(series_path, vesselness_lung_filename)

	processed = exists(myCont_filepath) and exists(vesselness_filepath)
	return processed

def explore_patient(patient_path, output_dir, csvFile):
	series = os.listdir(patient_path)
	count = 0
	for i in range (len(series)):
		list_of_slices, scan_path = load_scan(i, patient_path)
		nifti_exists, nifti_name = check_if_diff_nifti(scan_path)
		if (nifti_exists):
			dcm = grab_dcm_file(scan_path)
			slice_path = os.path.join(scan_path,dcm)
			# read in the full path to the file as ds
			ds=dicom.read_file(slice_path)
			if (ds.SeriesInstanceUID in nifti_name):
				if not series_was_processed_for_vessels(scan_path):
					print("Patient ID: ", ds.PatientID)
					print("Accession ID: ", ds.AccessionNumber)
					print("StudyInstanceUID: ", ds.StudyInstanceUID)
					print("SeriesInstanceUID: ", ds.SeriesInstanceUID)
					try:
						perform_lung_segmentations(scan_path)
					except Exception as e:
						print("Exception occured: ", str(e))
				else:
					print("Skipping vessel segmentation for patient: ", ds.PatientID, " with series: ", ds.SeriesInstanceUID)
				
				# Now calculate the percent contusions
				contusion_no_vessel = calculate_vesselness_contusion(scan_path)
				# calculate contusion vesselness / full lung
				cont_no_vessel_over_full_lung = calculate_vesselness_contusion_over_full_lung(scan_path)
				# calculate % vessels in lung
				perc_vessels = calculate_vessel_percent(scan_path)

				print(ds.PatientID, ", ", ds.AccessionNumber, ", ", ds.SeriesInstanceUID, ", ", contusion_no_vessel, ", ", cont_no_vessel_over_full_lung, ", ", perc_vessels, file = csvFile)
				count = count + 1

	print("Count: ", count)

def main(folder_with_all_patients, output_dir):
	patients = os.listdir(folder_with_all_patients)
	csvName = os.path.join(output_dir, "calculated_contusions.csv")
	csvFile = open(csvName, 'w')
	print("PatientId,AccessionNum,SeriesInstanceUID,'%' cont wo vessels,'%' cont wo vessels over full lung,'%' vessels", file = csvFile)
	for patient_folder in patients:
		patient_folder_path = os.path.join(folder_with_all_patients, patient_folder)
		explore_patient(patient_folder_path, output_dir, csvFile)


if __name__ == '__main__':
	main(sys.argv[1], sys.argv[2])
