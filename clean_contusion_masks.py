import sys
import os
import SimpleITK as sitk
import csv
import numpy as np
import itk
from os.path import exists

def parseNotes(notes_file):
	labels = []
	with open(notes_file) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		row_chest_ct = next(csv_reader)
		if row_chest_ct[1].strip() == "1":
			row_labels = next(csv_reader)
			cols = len(row_labels)
			for col in range(1, cols):
				labels.append(row_labels[col].strip())
				if not row_labels[col].strip():
					labels.pop()
			labels = [int(i) for i in labels]
	return labels

def segment_lung(ct, lung_mask, outputLungFile):
	ctReader = sitk.ImageFileReader()
	ctReader.SetImageIO("NiftiImageIO")
	ctReader.SetFileName(ct)
	ct_image = ctReader.Execute()
	ct_array = sitk.GetArrayFromImage(ct_image)

	lungReader = sitk.ImageFileReader()
	lungReader.SetImageIO("NiftiImageIO")
	lungReader.SetFileName(lung_mask)
	lung_mask_image = lungReader.Execute()

	lung_mask_array = sitk.GetArrayFromImage(sitk.Cast(lung_mask_image, sitk.sitkFloat64))
	lung_mask_array = np.where(lung_mask_array > 0, 1, lung_mask_array)

	lung_array = ct_array * lung_mask_array
	lung_image = sitk.GetImageFromArray(lung_array)

	writer = sitk.ImageFileWriter();
	writer.SetFileName(outputLungFile);
	writer.Execute(lung_image);

def segment_blood_vessels(lung, outputVesselnessLungFile):
	lung_image = itk.imread(lung, itk.ctype("double"))
	lung_array = itk.GetArrayFromImage(lung_image)
	hessian_image = itk.hessian_recursive_gaussian_image_filter(
	    lung_image, sigma=1.5
	)
	del lung_image
	vesselness_filter = itk.Hessian3DToVesselnessMeasureImageFilter[itk.ctype("double")].New()
	vesselness_filter.SetInput(hessian_image)
	vesselness_filter.SetAlpha1(0.25) #alpha 1
	vesselness_filter.SetAlpha2(0.75) #alpha 2
	del hessian_image
	vessel_mask_array = itk.GetArrayFromImage(vesselness_filter)
	del vesselness_filter


	vessel_mask_array = np.where(vessel_mask_array > 0, 0, 1)
	lung_without_vessels_array = lung_array * vessel_mask_array
	vessel_image = itk.GetImageFromArray(lung_without_vessels_array)
	
	itk.imwrite(vessel_image, outputVesselnessLungFile)


def segment_contusion(vesselness_lung, outputImageFileName):
	lungReader = sitk.ImageFileReader()
	lungReader.SetImageIO("NiftiImageIO")
	lungReader.SetFileName(vesselness_lung)
	vesselness_image = lungReader.Execute()

	contusion = sitk.BinaryThreshold(vesselness_image,
	 lowerThreshold=-400, upperThreshold=-10, insideValue=1, outsideValue=0)
	# cc = sitk.ConnectedComponent(contusion)
	
	labels = []
	labels.append(1)

	writer = sitk.ImageFileWriter();
	writer.SetFileName(outputImageFileName);
	writer.Execute(contusion);

	return measure_contusion(contusion, labels)


def measure_contusion(diff_mask, labels):
	contusion_size = 0
	stats = sitk.LabelIntensityStatisticsImageFilter()
	stats.Execute(diff_mask, diff_mask)
	for l in stats.GetLabels():
		if l in labels:
			contusion_size = contusion_size + stats.GetPhysicalSize(l)
			#print("Label: {0} -> Size: {1}".format(l, stats.GetPhysicalSize(l)))
	return contusion_size

def measure_lung(lung_mask):
	reader = sitk.ImageFileReader()
	reader.SetImageIO("NiftiImageIO")
	reader.SetFileName(lung_mask)
	image = reader.Execute()

	lung_size = 0
	stats = sitk.LabelIntensityStatisticsImageFilter()
	stats.Execute(image, image)

	for l in stats.GetLabels():
		lung_size = lung_size + stats.GetPhysicalSize(l)
	return lung_size

def measure_og_contusion(original_contusion_filepath, lung_mask_filepath):
	reader = sitk.ImageFileReader()
	reader.SetImageIO("NiftiImageIO")
	reader.SetFileName(lung_mask_filepath)
	lung_mask = reader.Execute()
	lung_mask_array = sitk.GetArrayFromImage(sitk.Cast(lung_mask, sitk.sitkFloat64))

	del reader
	del lung_mask

	lung_mask_array = np.where(lung_mask_array > 0, 1, 0) # make all labels equal to 1

	# lung_image = sitk.GetImageFromArray(lung_mask_array)
	# writer = sitk.ImageFileWriter();
	# writer.SetFileName("verify_lung_mask.nii.gz");
	# writer.Execute(lung_image);

	reader2 = sitk.ImageFileReader()
	reader2.SetImageIO("NiftiImageIO")
	reader2.SetFileName(original_contusion_filepath)
	og_contusion = reader2.Execute()

	stats = sitk.LabelIntensityStatisticsImageFilter()
	stats.Execute(og_contusion, og_contusion)
	labels2 = stats.GetLabels()
	og_contusion_array = sitk.GetArrayFromImage(sitk.Cast(og_contusion, sitk.sitkFloat64))
	del reader2
	del og_contusion

	og_contusion_array = np.where(og_contusion_array > 0, 1, 0) # make all labels equal to 1

	contusion_mask_only_array = lung_mask_array - og_contusion_array
	contusion_mask_only_array = np.where(contusion_mask_only_array <= 0, 0, 1) # make all labels equal to 1
	del lung_mask_array
	del og_contusion_array

	contusion_image = sitk.GetImageFromArray(contusion_mask_only_array)
	# writer = sitk.ImageFileWriter();
	# writer.SetFileName("verify_contusion_mask.nii.gz");
	# writer.Execute(contusion_image);

	stats2 = sitk.LabelIntensityStatisticsImageFilter()
	stats2.Execute(contusion_image, contusion_image)

	contusion_size = 0
	for l in stats2.GetLabels():
		contusion_size = contusion_size + stats.GetPhysicalSize(l)
	return contusion_size


def measure_vesselless_lung(vesselness_filepath):
	reader = sitk.ImageFileReader()
	reader.SetImageIO("NiftiImageIO")
	reader.SetFileName(vesselness_filepath)
	vesslness_lung = reader.Execute()

	vesslness_lung_array = sitk.GetArrayFromImage(sitk.Cast(vesslness_lung, sitk.sitkFloat64))
	del reader
	del vesslness_lung

	vesslness_lung_array = np.where(vesslness_lung_array != 0, 1, 0) # make everything other than 0 equal to 1 - hence masking the segmented image
	vesselness_lung_mask = sitk.GetImageFromArray(vesslness_lung_array)

	# writer = sitk.ImageFileWriter();
	# writer.SetFileName("verify_vesselness_lung_mask.nii.gz");
	# writer.Execute(vesselness_lung_mask);

	stats = sitk.LabelIntensityStatisticsImageFilter()
	stats.Execute(vesselness_lung_mask, vesselness_lung_mask)
	labels = stats.GetLabels()

	lung_size = 0
	for l in stats.GetLabels():
		lung_size = lung_size + stats.GetPhysicalSize(l)
	return lung_size

def measure_vessels(vesselness_filepath, lung_mask_filepath, vessel_mask_filepath):
	reader = sitk.ImageFileReader()
	reader.SetImageIO("NiftiImageIO")
	reader.SetFileName(vesselness_filepath)
	vesslness_lung = reader.Execute()
	vessel_withBckgrnd_array = sitk.GetArrayFromImage(sitk.Cast(vesslness_lung, sitk.sitkFloat64))
	del reader
	del vesslness_lung

	reader = sitk.ImageFileReader()
	reader.SetImageIO("NiftiImageIO")
	reader.SetFileName(lung_mask_filepath)
	lung_mask_image = reader.Execute()
	lung_mask_array = sitk.GetArrayFromImage(sitk.Cast(lung_mask_image, sitk.sitkFloat64))
	del reader
	del lung_mask_image

	vessel_withBckgrnd_array = np.where(vessel_withBckgrnd_array == 0, 2, 0) # make everything that's 0 equal to 1 - hence masking the vessels
	vessel_only_array = lung_mask_array * vessel_withBckgrnd_array
	vessel_only_array = np.where(vessel_only_array > 0, 1, 0) 

	vessel_mask = sitk.GetImageFromArray(vessel_only_array)

	writer = sitk.ImageFileWriter();
	writer.SetFileName(vessel_mask_filepath);
	writer.Execute(vessel_mask);

	stats = sitk.LabelIntensityStatisticsImageFilter()
	stats.Execute(vessel_mask, vessel_mask)
	labels = stats.GetLabels()

	vessel_size = 0
	for l in stats.GetLabels():
		vessel_size = vessel_size + stats.GetPhysicalSize(l)

	# LabelIntensityStatImageFilter seems to only support ints and nifti writer does not
	vessel_only_array = np.where(vessel_only_array == 0, 0.0, 1.0) # make everything that's 0 equal to 1 - hence masking the vessels
	vessel_mask = sitk.GetImageFromArray(vessel_only_array)

	writer = sitk.ImageFileWriter();
	writer.SetFileName(vessel_mask_filepath);
	writer.Execute(vessel_mask);
	return vessel_size


def calculate_og_contusion(path):
	subdir_components = os.listdir(path)
	splitPath = path.split("/")
	subdir = splitPath[len(splitPath)-1]
	original_contusion_mask_filename = subdir + "_segmentation_contusion.nii.gz"
	fused_mask_filename = subdir + "_segmentation_contusion_fused.nii.gz"

	lung_mask_filepath = os.path.join(path, fused_mask_filename)
	original_contusion_filepath = os.path.join(path, original_contusion_mask_filename)	
	if exists(lung_mask_filepath) and exists(original_contusion_filepath):
		lung_size = measure_lung(lung_mask_filepath)
		if (lung_size > 0):
			# create contusion mask from original contusion and measure volume
			cont_og_size = measure_og_contusion(original_contusion_filepath, lung_mask_filepath)
			perc_cont_og = (cont_og_size/lung_size) * 100
			return perc_cont_og
	return 0



def calculate_vesselness_contusion(path):
	subdir_components = os.listdir(path)
	splitPath = path.split("/")
	subdir = splitPath[len(splitPath)-1]
	myCont_mask_filename = subdir + "_contusion.nii.gz"
	vesselness_lung_filename = subdir + "_vesselness.nii.gz"

	myCont_filepath = os.path.join(path, myCont_mask_filename)
	vesselness_filepath = os.path.join(path, vesselness_lung_filename)
	if exists(myCont_filepath) and exists(vesselness_filepath):
		vesslness_lung_size = measure_vesselless_lung(vesselness_filepath)
		if (vesslness_lung_size > 0):
			reader = sitk.ImageFileReader()
			reader.SetImageIO("NiftiImageIO")
			reader.SetFileName(myCont_filepath)
			vesselness_cont_mask = reader.Execute()

			labels = []
			labels.append(1)

			vesselness_cont_size = measure_contusion(vesselness_cont_mask, labels)
			perc_cont_vesselness = (vesselness_cont_size / vesslness_lung_size) * 100
			return perc_cont_vesselness
	return 0

def calculate_vesselness_contusion_over_full_lung(path):
	subdir_components = os.listdir(path)
	splitPath = path.split("/")
	subdir = splitPath[len(splitPath)-1]
	myCont_mask_filename = subdir + "_contusion.nii.gz"
	fused_mask_filename = subdir + "_segmentation_contusion_fused.nii.gz"

	lung_mask_filepath = os.path.join(path, fused_mask_filename)
	myCont_filepath = os.path.join(path, myCont_mask_filename)
	if exists(myCont_filepath) and exists(lung_mask_filepath):
		lung_size = measure_lung(lung_mask_filepath)
		if (lung_size > 0):
			reader = sitk.ImageFileReader()
			reader.SetImageIO("NiftiImageIO")
			reader.SetFileName(myCont_filepath)
			vesselness_cont_mask = reader.Execute()

			labels = []
			labels.append(1)

			vesselness_cont_size = measure_contusion(vesselness_cont_mask, labels)
			perc_cont_vesselness = (vesselness_cont_size / lung_size) * 100
			return perc_cont_vesselness
	return 0

def calculate_vessel_percent(path):
	subdir_components = os.listdir(path)
	splitPath = path.split("/")
	subdir = splitPath[len(splitPath)-1]
	vessel_mask_filename = subdir + "_vessels_mask.nii.gz"
	vesselness_lung_filename = subdir + "_vesselness.nii.gz"
	fused_mask_filename = subdir + "_segmentation_contusion_fused.nii.gz"

	lung_mask_filepath = os.path.join(path, fused_mask_filename)
	vessel_mask_filepath = os.path.join(path, vessel_mask_filename)
	vesselness_filepath = os.path.join(path, vesselness_lung_filename)
	if exists(lung_mask_filepath) and exists(vesselness_filepath):
		lung_size = measure_lung(lung_mask_filepath)
		if (lung_size > 0):
			vessel_size = measure_vessels(vesselness_filepath, lung_mask_filepath, vessel_mask_filepath)

			perc_vessels = (vessel_size / lung_size) * 100
			return perc_vessels
	return 0


def perform_lung_segmentations(path):
	subdir_components = os.listdir(path)
	splitPath = path.split("/")
	subdir = splitPath[len(splitPath)-1]
	myCont_mask_filename = subdir + "_contusion.nii.gz"
	vesselness_lung_filename = subdir + "_vesselness.nii.gz"
	lung_filename = subdir + "_lung_only.nii.gz"
	ct_filename = subdir + "-series.nii.gz"
	original_contusion_mask_filename = subdir + "_segmentation_contusion.nii.gz"
	fused_mask_filename = subdir + "_segmentation_contusion_fused.nii.gz"

	myCont_filepath = os.path.join(path, myCont_mask_filename)
	vesselness_filepath = os.path.join(path, vesselness_lung_filename)
	lung_only_filepath = os.path.join(path, lung_filename)
	ct_filepath = os.path.join(path, ct_filename)
	lung_mask_filepath = os.path.join(path, fused_mask_filename)

	print("Series being processed: ", subdir)
	segment_lung(ct_filepath, lung_mask_filepath, lung_only_filepath)
	segment_blood_vessels(lung_only_filepath, vesselness_filepath)
	print("done...")
	print()


def main(parent_folder):
	for subdir in os.listdir(parent_folder):
		path = os.path.join(parent_folder, subdir)
		perform_lung_segmentations(path)



if __name__ == '__main__':
	main(sys.argv[1])
