import json
import numpy as np
import shutil
import os
from PIL import Image, ImageDraw

# Get the current working directory
cwd = os.getcwd()

# Define the parent directory of the current working directory
parent_dir = os.path.dirname(cwd)

# Heerlen or ZL
REGION = "Heerlen_2018_HR_output"

# Define image and mask folders
image_folder = os.path.join(parent_dir, "data", REGION, "images_positive")  # Replace "directory_to_specify" with the actual directory
json_folder = os.path.join(parent_dir, "annotations")  # Replace "directory_to_specify" with the actual directory

# Define output folders
mask_output_folder = os.path.join(parent_dir, "data_NL", REGION, "masks_positive")  # Replace "directory_to_specify" with the actual directory
image_output_folder = os.path.join(parent_dir, "data_NL", REGION, "images_positive")  # Replace "directory_to_specify" with the actual directory

# create the output folders if they don't exist already
if not os.path.exists(mask_output_folder):
    os.makedirs(mask_output_folder)
if not os.path.exists(image_output_folder):
    os.makedirs(image_output_folder)

# fetch all the json files in the directory "json_folder"
json_files = [pos_json for pos_json in os.listdir(json_folder) if pos_json.endswith('.json')]

print(f"json_files: {json_files}")

# Iterate over each JSON file
for json_file in json_files:
    with open(json_file) as f:
        data = json.load(f)

    # Define the upsample factor
    upsample_factor = 30

    # Iterate over each image in the JSON file
    for image in data['images']:
        image_id = image['id']
        width = image['width']
        height = image['height']
        file_name = image['file_name']

        # Create a blank mask for this image, upscaled by the upsample factor
        mask = Image.new('L', (width * upsample_factor, height * upsample_factor), 0)  # 'L' for 8-bit pixels, black and white

        # Iterate over each annotation in the JSON file
        for annotation in data['annotations']:
            # Check if the annotation belongs to the current image
            if annotation['image_id'] == image_id:
                # Draw the polygon annotation on the mask
                draw = ImageDraw.Draw(mask)
                segmentation = [point * upsample_factor for point in annotation['segmentation'][0]]

                # Reshape the segmentation to a list of tuples, each representing a vertex of the polygon
                polygon = list(map(tuple, np.reshape(segmentation, (-1, 2))))
                # Draw the polygon on the mask
                draw.polygon(polygon, outline=1, fill=255)  # fill with white (255)

        # Downsample the mask to the original size, this will perform a simple anti-aliasing
        mask = mask.resize((width, height), Image.ANTIALIAS)

        # Convert the mask to a numpy array
        mask_array = np.array(mask)

        # Threshold the mask to ensure it's binary
        mask_array = np.where(mask_array > 128, 255, 0)

        # Convert the mask back to a PIL image
        mask = Image.fromarray(mask_array.astype('uint8'), 'L')

        # Calculate the coordinates of the center crop
        left = (width - 200) // 2
        top = (height - 200) // 2
        right = (width + 200) // 2
        bottom = (height + 200) // 2

        # Crop the center part from the original mask
        center_crop = mask.crop((left, top, right, bottom))

        # Create a new mask that is all zeros
        center_crop_mask = Image.new('L', (width, height), 0)

        # Paste the center crop into the new mask
        center_crop_mask.paste(center_crop, (left, top))

        # Save the mask image, with a name based on the image file name
        center_crop_mask.save(f'{file_name}')

        # After creating each mask, check if the corresponding image exists
        image_file_path = os.path.join(image_folder, f'{file_name}')

        # Check if the image exists
        assert os.path.exists(image_file_path), f"The image {image_file_path} does not exist."

        # move the mask to the output folder and copy the image to the other output folder
        if os.path.exists(image_file_path):
            # If the image exists, move the mask to the output folder
            shutil.move(f'{file_name}', os.path.join(mask_output_folder, f'{file_name}'))
            # And copy the image to the other output folder
            shutil.copy2(image_file_path, os.path.join(image_output_folder, f'{file_name}'))

        # number of masks created
    print(f"Number of masks created: {len(data['images'])}")