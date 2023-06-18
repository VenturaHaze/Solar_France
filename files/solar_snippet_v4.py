import os  # Import the os module for handling file paths
import numpy as np  # Import numpy for array manipulation
import scipy.ndimage as ndi  # Import the ndimage module from SciPy for image processing
from PIL import Image, ImageEnhance, ImageFilter, ImageOps  # Import the Image module from PIL for handling images
import math
from skimage.measure import regionprops_table
import time
import random

def find_largest_white_patch(mask):
    """Function to find the largest white patch in a binary mask
    :param mask: Binary mask, where white pixels (solar PVs) are 1 and black pixels are 0
    :return: Center (x,y coordinates wihtin mask) and bounding box of the largest white patch
    """
    mask_labeled, num_features = ndi.label(mask)  # Label connected components in the mask

    patch_sizes = np.bincount(mask_labeled.flat)[1:]  # Count the size of each connected component
    largest_patch = np.argmax(patch_sizes) + 1  # Find the label of the largest connected component
    largest_patch_pixels = np.nonzero(mask_labeled == largest_patch)  # Get the pixel coordinates of the largest connected component

    center = np.mean(np.column_stack(largest_patch_pixels), axis=0).astype(np.int32)  # Calculate the center of the largest connected component
    bounding_box = (np.min(largest_patch_pixels[1]), np.min(largest_patch_pixels[0]), np.max(largest_patch_pixels[1]), np.max(largest_patch_pixels[0]))  # Calculate the bounding box of the largest connected component

    return tuple(center), bounding_box  # Return the center and bounding box

def find_random_white_patch(mask, min_pixel_count=200):
    """
    Function to find a random white patch from the list sorted by their size in a binary mask,
    excluding patches with less than min_pixel_count pixels.
    :param mask: Binary mask, where white pixels (solar PVs or buildings) are 1 and black pixels are 0
    :param min_pixel_count: Minimum number of pixels in a patch to be considered for random selection (default: 100)
    :return: Center (x,y coordinates within mask) and bounding box of the randomly selected white patch
    """
    mask_labeled, num_features = ndi.label(mask)  # Label connected components in the mask

    # if num features <= 1 , execute if statement
    if num_features <= 1:
        # If there are no valid patches, randomly select a center and bounding box
        height, width = mask.shape
        # Define the boundaries for the center part of the image
        center_start_x = width // 2 - 100
        center_end_x = width // 2 + 100
        center_start_y = height // 2 - 100
        center_end_y = height // 2 + 100
        # Generate a random center within the center 200x200 part of the image
        center = (random.randint(center_start_x, center_end_x), random.randint(center_start_y, center_end_y))

        # OR Generate a random bounding box around the center
        # center = (random.randint(0, width - 1), random.randint(0, height - 1))

        # bounding box = (left, top, right, bottom)
        bounding_box = (center[0] - 30, center[1] - 30, center[0] + 30, center[1] + 30)
    else:
        patch_sizes = np.bincount(mask_labeled.flat)[1:]  # Count the size of each connected component
        valid_patches_indices = np.where(patch_sizes >= min_pixel_count)[0]  # Filter patches based on the minimum pixel count

        # If there are valid patches, randomly select a patch from the valid patches
        total_white_pixels = np.sum(patch_sizes[valid_patches_indices])  # Calculate the total number of white pixels in the valid patches
        probabilities = patch_sizes[valid_patches_indices] / total_white_pixels  # Calculate the proportional probabilities

        # Randomly choose a patch from the valid_patches_indices list using proportional probabilities
        selected_patch = np.random.choice(valid_patches_indices, p=probabilities) + 1

        # Alternative: randomly choose a patch from the valid patches, by simple random sampling, wihtout probabilities
        # selected_patch = np.random.choice(valid_patches_indices) + 1

        selected_patch_pixels = np.nonzero(mask_labeled == selected_patch)  # Get the pixel coordinates of the selected patch

        center = np.mean(np.column_stack(selected_patch_pixels), axis=0).astype(np.int32)  # Calculate the center of the selected patch
        bounding_box = (np.min(selected_patch_pixels[1]), np.min(selected_patch_pixels[0]), np.max(selected_patch_pixels[1]), np.max(selected_patch_pixels[0]))  # Calculate the bounding box of the selected patch

    return tuple(center), bounding_box  # Return the center and bounding box

def crop_solar_panel(image, mask):
    """Function to crop a solar panel from the image and its mask
    :param image: Image to crop
    :param mask: Mask to crop
    :return: Cropped image and mask
    """
    mask_np = mask.copy()  # Create a copy of the mask

    # Convert the mask to a numpy array
    try:
        labeled_mask, num_features = ndi.label(mask_np)  # Label connected components in the mask
        largest_cc = np.argmax(np.bincount(labeled_mask.flat)[1:]) + 1  # Find the label of the largest connected component
        largest_cc_mask = (labeled_mask == largest_cc).astype(np.uint8) * 255  # Create a binary mask of the largest connected component
    # handle edge case where there are no white pixels in the mask
    except:
        # Return empty image and mask instead of raising an error
        empty_image = Image.new("RGB", (1, 1))
        empty_mask = Image.new("1", (1, 1))
        return empty_image, empty_mask

    white_pixels = np.nonzero(largest_cc_mask)  # Get the pixel coordinates of white pixels in the largest connected component mask
    bounding_box = (np.min(white_pixels[1]), np.min(white_pixels[0]), np.max(white_pixels[1]), np.max(white_pixels[0]))  # Calculate the bounding box of the largest connected component
    cropped_image = image.crop(bounding_box)  # Crop the image using the bounding box
    cropped_mask = Image.fromarray(largest_cc_mask[bounding_box[1]:bounding_box[3], bounding_box[0]:bounding_box[2]])  # Crop the mask using the bounding box

    # show both the cropped image and mask
    # cropped_image.show()
    # cropped_mask.show()

    return cropped_image, cropped_mask  # Return the cropped image and mask

def find_angle(mask):
    # Show mask
    # mask.show()

    try:
        mask_array = np.array(mask)
        binary_mask = (mask_array == 255).astype(int)
        props = regionprops_table(binary_mask, properties=['orientation'])
        angle = props['orientation'][0]
    # except index error when there are no white pixels in the mask and value error when there is only one white pixel in the mask
    except:
        angle = 0
    return angle

def paste_solar_panel(target_image, target_mask, target_mask_np, cropped_image, cropped_mask, target_location, target_bounding_box):
    """This function takes a target image and its corresponding mask, a cropped image of a solar panel with its
    corresponding mask, the location where the solar panel should be pasted, and the bounding box of the target area.
    It then aligns the cropped image with the target image by calculating the angle difference between them and
    rotating the cropped image and mask accordingly. Finally, it pastes the cropped image and mask onto the target
    image and mask, and returns the modified target mask.
    :param target_image: Target image
    :param target_mask: Target mask
    :param target_mask_np: Target mask as a numpy array
    :param cropped_image: Cropped image
    :param cropped_mask: Cropped mask
    :param location: Location where the cropped image should be pasted
    :param bounding_box: Bounding box of the target area
    :return: Modified target mask
    """

    # Get the bounding box coordinates
    x_min, y_min, x_max, y_max = target_bounding_box

    # Calculate the center of the bounding box
    center_x = (x_max + x_min) // 2
    center_y = (y_max + y_min) // 2

    # Calculate the position where the cropped image should be pasted
    paste_x = center_x - cropped_image.size[0] // 2
    paste_y = center_y - cropped_image.size[1] // 2

    # Introduce randomness to the paste position
    paste_x += random.randint(-25, 25)
    paste_y += random.randint(-25, 25)

    # Ensure the paste position is within the bounding box
    paste_x = max(x_min, min(paste_x, x_max - cropped_image.size[0]))
    paste_y = max(y_min, min(paste_y, y_max - cropped_image.size[1]))

    # Calculate the angle difference between target_mask and cropped_mask
    target_angle = find_angle(target_mask)
    cropped_angle = find_angle(cropped_mask)
    rotation = np.degrees(target_angle - cropped_angle)

    #############################
    # Apply random transformations
    #############################
    # Introduce randomness to the paste angle
    rotation += random.randint(-10, 10)

    # Rotate the cropped image and mask to align with the target mask
    cropped_image = cropped_image.rotate(rotation, resample=Image.BICUBIC, expand=True)
    cropped_mask = cropped_mask.rotate(rotation, resample=Image.BICUBIC, expand=True)

    # Apply random brightness to the cropped image
    if random.random() < 0.3:
        brightness = ImageEnhance.Brightness(cropped_image)
        cropped_image = brightness.enhance(random.uniform(0.9, 1.1))

    # Apply random contrast to the cropped image
    if random.random() < 0.3:
        contrast = ImageEnhance.Contrast(cropped_image)
        cropped_image = contrast.enhance(random.uniform(0.9, 1.1))

    # Apply random hue to the cropped image
    if random.random() < 0.3:
        hue_factor = random.uniform(-0.05, 0.05)
        cropped_image = ImageEnhance.Color(cropped_image).enhance(1 + hue_factor)

    # Apply random zoom to the cropped image & mask
    if random.random() < 0.3:
        zoom_factor = random.uniform(0.85, 1.1)
        resized_image_size = tuple([int(dim * zoom_factor) for dim in cropped_image.size])
        resized_mask_size = tuple([int(dim * zoom_factor) for dim in cropped_mask.size])
        try:
            cropped_image = cropped_image.resize(resized_image_size, resample=Image.BICUBIC)
            cropped_mask = cropped_mask.resize(resized_mask_size, resample=Image.BICUBIC)

        except:
            pass

    # Apply Gaussian blur or sharpening to the cropped image
    if random.random() < 0.3:
        if random.random() < 0.7:
            cropped_image = cropped_image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0, 0.3)))
        else:
            #
            cropped_image = ImageEnhance.Sharpness(cropped_image).enhance(random.uniform(0, 0.3))

    # make sure that cropped mask is only 0 or 255
    cropped_mask = np.array(cropped_mask)
    cropped_mask = np.where(cropped_mask > 50, 255, 0)
    cropped_mask = Image.fromarray(cropped_mask.astype('uint8'), 'L')

    # Clear the target mask, i.e. fill it with 0s, that is, remove the building segmentations
    target_mask_np.fill(0)

    # Convert the array back to an image, since we need to paste the cropped mask onto the cleared target mask
    target_mask = Image.fromarray(target_mask_np.astype(np.uint8))

    # Paste the cropped image and mask onto the target image and mask
    target_image.paste(cropped_image, (paste_x, paste_y), mask=cropped_mask)
    target_mask.paste(cropped_mask, (paste_x, paste_y), mask=cropped_mask)

    return target_mask

def modify_images(source_image, source_mask, target_image, target_mask):
    """
    Function to modify the target images and masks by pasting a solar panel from the source images and masks
    :param source_image: Source image -> this is the cropped image of the solar panel
    :param source_mask: Source mask -> this is the cropped mask of the solar panel
    :param target_image: Target image -> this is the image that will be modified
    :param target_mask: Target mask -> this is the mask that will be modified
    :return: Modified target image and mask, now with a solar panel pasted onto it
    """
    if np.sum(target_mask) == 0:  # If there are no white pixels in the target mask, raise an exception
        raise ValueError("No white pixels in building mask.")

    source_mask_np = np.array(source_mask, dtype=np.uint8)  # Convert the source mask to a numpy array
    source_mask_np[source_mask_np > 0] = 255  # Set all non-zero values to 255

    target_mask_np = np.array(target_mask, dtype=np.uint8)  # Convert the target mask to a numpy array
    target_mask_np[target_mask_np > 0] = 255  # Set all non-zero values to 255

    # random sample from white patches with at minimum min_pixel_count pixels of white pixels on the target mask
    # experimented with the min_pixel_count parameter and 1500 seems to work well, given the 400x400 size of the target images
    MIN_PIXEL_COUNT = 1500
    target_location, target_bounding_box = find_random_white_patch(target_mask_np, min_pixel_count=MIN_PIXEL_COUNT)

    # alternative: always use the largest patch
    # target_location, target_bounding_box = find_largest_white_patch(target_mask_np)

    # Replace white values outside the bounding box with black values
    x_min, y_min, x_max, y_max = target_bounding_box
    target_mask_np[0:y_min, :] = 0
    target_mask_np[y_max:, :] = 0
    target_mask_np[:, 0:x_min] = 0
    target_mask_np[:, x_max:] = 0

    target_mask = Image.fromarray(target_mask_np)

    # Crop the solar panel from the source image and its mask
    cropped_image, cropped_mask = crop_solar_panel(source_image, source_mask_np)

    # Paste the solar panel onto the target image and its mask
    target_mask = paste_solar_panel(target_image, target_mask, target_mask_np, cropped_image, cropped_mask, target_location, target_bounding_box)

    # keep only 200x200 center of the images and masks, rest should be black padding
    target_image = target_image.crop((100, 100, 300, 300))
    target_mask = target_mask.crop((100, 100, 300, 300))

    # padding to resize to 400x400
    target_image = ImageOps.expand(target_image, border=100, fill='black')
    target_mask = ImageOps.expand(target_mask, border=100, fill='black')

    # Return the modified target image and its mask
    return target_image, target_mask

class ImageProcessor:
    def __init__(self, solar_images, solar_masks, solar_image_dirs, solar_mask_dirs, building_image_dir, building_mask_dir):
        self.parent_dir = os.path.dirname(os.getcwd())
        self.building_image_dir = building_image_dir
        self.building_mask_dir = building_mask_dir

        # building image files
        self.building_image_files = [os.path.join(self.building_image_dir, image) for image in sorted(os.listdir(self.building_image_dir)) if
                                     image.endswith('.png')]
        # building mask files
        self.building_mask_files = [os.path.join(self.building_image_dir, mask) for mask in sorted(os.listdir(self.building_mask_dir)) if
                                    mask.endswith('.png')]
        # solar image files
        self.solar_image_files = [os.path.join(image_dir, image) for image_dir in solar_image_dirs for image in
                                  solar_images if os.path.exists(os.path.join(image_dir, image))]

        # solar mask files
        self.solar_mask_files = [os.path.join(mask_dir, mask) for mask_dir in solar_mask_dirs for mask in solar_masks if
                                 os.path.exists(os.path.join(mask_dir, mask))]

        # ToDo: clean code to account for double names in folders, that is modify
        print(f"Number of unique solar images available: {len(self.solar_image_files)}")

    def filter_solar_files(self, expressions):
        if not isinstance(expressions, list):
            expressions = [expressions]

        self.solar_image_files = [image_file for image_file in self.solar_image_files if
                                  any(exp in image_file for exp in expressions)]
        self.solar_mask_files = [mask_file for mask_file in self.solar_mask_files if
                                 any(exp in mask_file for exp in expressions)]

    def process_sample_images(self, solar_images, solar_masks, building_images, building_masks):
        # Randomly select one training image and its corresponding mask file from the lists
        solar_index = random.randint(0, len(solar_images) - 1)
        solar_image_path = solar_images[solar_index]
        solar_mask_path = solar_masks[solar_index]

        building_index = random.randint(0, len(building_images) - 1)
        building_image_path = building_images[building_index]
        building_mask_path = building_masks[building_index]
        # print(building_image_path, building_mask_path)

        source_image = Image.open(solar_image_path).convert("RGB")
        source_mask = Image.open(solar_mask_path).convert("L")
        target_image = Image.open(building_image_path).convert("RGB")
        target_mask = Image.open(building_mask_path).convert("L")


        modified_target_image, modified_target_mask = modify_images(source_image, source_mask, target_image,
                                                                    target_mask)
        # modified_target_image.show(), modified_target_mask.show()


        # Remove the used items from the lists
        solar_images.pop(solar_index)
        solar_masks.pop(solar_index)
        building_images.pop(building_index)
        building_masks.pop(building_index)

        return modified_target_image, modified_target_mask

    def process_all_images(self, factor, output_dirs):
        start_time = time.time()
        output_image_dir, output_mask_dir = output_dirs

        # make output directories, if they don't exist
        os.makedirs(output_image_dir, exist_ok=True)
        os.makedirs(output_mask_dir, exist_ok=True)

        # Copy the lists
        solar_images = self.solar_image_files.copy()
        solar_masks = self.solar_mask_files.copy()
        building_images = self.building_image_files.copy()
        building_masks = self.building_mask_files.copy()

        # Calculate how many times to loop over the solar images list
        number_generated = math.ceil(len(solar_images) * factor)
        print(f"Number of solar images to be generated: {number_generated}")
        loops = number_generated

        # Counter for saving images/masks
        counter = 1

        for _ in range(loops):
            # Check if the solar_images list is empty, if so, reset it
            if not solar_images:
                solar_images = self.solar_image_files.copy()
                solar_masks = self.solar_mask_files.copy()

            # Check if the building_images list is empty, if so, reset it
            if not building_images:
                building_images = self.building_image_files.copy()
                building_masks = self.building_mask_files.copy()

            image, mask = self.process_sample_images(solar_images, solar_masks, building_images, building_masks)

            # Define minimum and maximum number of white pixels
            min_white_pixels =  200
            max_white_pixels =  10000

            # Convert mask to grayscale and threshold so that white pixels have value 255
            mask = mask.convert("L")
            mask_np = np.array(mask)

            # Count the number of white pixels in the mask
            num_white_pixels = np.sum(mask_np == 255)

            # If the mask meets the condition, save the image and mask
            if min_white_pixels <= num_white_pixels <= max_white_pixels:
                # Save the modified target image and its mask with sequential numbers
                image.save(os.path.join(output_image_dir, f"{counter}.png"))
                mask.save(os.path.join(output_mask_dir, f"{counter}.png"))
                counter += 1

        print(f"Success: Number of valid solar images generated: {counter - 1}")

        end = time.time()
        # time taken to run the script, in hrs, mins, secs
        time_taken = time.strftime("%H:%M:%S", time.gmtime(end - start_time))

if __name__ == "__main__":
    # set random seed
    random.seed(42)

    # Fetch the parent directory of the current directory
    parent_dir = os.path.dirname(os.getcwd())

    # Specify the Fraction of solar images to use
    FRACTION = 5

    # Specify the directories of the solar images and masks
    positive_image_dir = os.path.join(parent_dir, 'data_train', 'Heerlen_2018_HR_output', 'images_positive')
    positive_mask_dir = os.path.join(parent_dir, 'data_train', 'Heerlen_2018_HR_output', 'masks_positive')

    # Specify the directories of the building images and masks
    building_image_dir = os.path.join(parent_dir, 'data', 'Heerlen_2018_HR_output', 'images_negative')
    building_mask_dir = os.path.join(parent_dir, 'data', 'Heerlen_2018_HR_output', 'masks_negative')

    # Specify the directories to save the output images and masks
    output_image_dir = os.path.join(parent_dir, 'data_snippet', 'Heerlen_RA', 'images_positive')
    output_mask_dir = os.path.join(parent_dir, 'data_snippet', 'Heerlen_RA', 'masks_positive')

    # Get the list of solar images and masks
    train_images_positive = sorted([f for f in os.listdir(positive_image_dir) if f.endswith('.png')])
    train_masks_positive = sorted([f for f in os.listdir(positive_mask_dir) if f.endswith('.png')])


    # Create an instance of the ImageProcessor class
    image_processor = ImageProcessor(train_images_positive, train_masks_positive, [positive_image_dir],
                                     [positive_mask_dir], building_image_dir, building_mask_dir)

    # Execute the process_all_images method
    image_processor.process_all_images(FRACTION, (output_image_dir, output_mask_dir))