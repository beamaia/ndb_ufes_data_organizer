import os
import pathlib as pl
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scripts.src.utils import logger

import cv2 as cv

def parse_args():
    parser = argparse.ArgumentParser(
                prog="NPD-UFES and P-NDB-UFES data link",
                description="Links patches from P-NDB-UFES to the original image the patch was \
                obtained from using NDB-UFES",
            )
    
    parser.add_argument("-pp", "--patch_path", default="data/ndb_ufes/patch/images", help="Path to \
                        directory with patches images from P-NDB-UFES.")
    parser.add_argument("-ip", "--image_path", default="data/ndb_ufes/images", help="Path to \
                        directory with original images from NDB-UFES.")
    parser.add_argument("-lp", "--link_path", default="data/ndb_ufes/link", help="Path to \
                        directory that saves figures and csv that compares patch to detected point in the \
                        original image.")
    parser.add_argument("-c", "--use_checkpoint", action="store_true", help="Continues linking images, \
                        considering images already linked in link path images directory.")
    parser.add_argument("--ignore_patches", default=[], help="List of ids (int) of patches that \
                        should be ignored.", nargs="+", type=int)
    return parser.parse_args()

def main():
    pass

def use_checkpoint(links_path, patches_list, patch_paths):
    links_path = links_path / "images"
    linked_images = set([img.name[6:11] for img in links_path.iterdir()])

    new_images = set(patches_list) - linked_images
    linked_index = set([patches_list.index(name) for name in new_images])

    new_patches_list = sorted([patches_list[i] for i in linked_index])
    new_patch_paths = sorted([patch_paths[i] for i in linked_index])

    return new_patches_list, new_patch_paths

def ignore_patches(ignore_ids, patches_list, patch_paths):
    ignore_parsed = [f"p{id:04}" for id in ignore_ids]
    print(ignore_parsed)
    ignored_ids = set([patches_list.index(name) for name in patches_list if name not in ignore_parsed])

    new_patches_list = sorted([patches_list[i] for i in ignored_ids])
    new_patch_paths = sorted([patch_paths[i] for i in ignored_ids])   

    return new_patches_list, new_patch_paths

if __name__ == "__main__":
    args = parse_args()
    print("Path to patches", args.patch_path)
    print("Path to origin images", args.image_path)

    PATCHES_PATH = pl.Path(args.patch_path)
    ORIGIN_PATH = pl.Path(args.image_path)
    LINK_PATH = pl.Path(args.link_path)

    if not os.path.exists(str(LINK_PATH)):
        os.makedirs(str(LINK_PATH))

    patches_list = [img.name[:-4] for img in PATCHES_PATH.iterdir()]
    patch_paths = [str(img) for img in PATCHES_PATH.iterdir()]
    origin_list = [img.name[:-4] for img in ORIGIN_PATH.iterdir()]
    origin_paths = [str(img) for img in ORIGIN_PATH.iterdir()]

    link_df = pd.DataFrame({
            "patch_id": patches_list,
            "patch_path": patch_paths,
        })
    
    link_df["public_id"] = -1
    link_df["public_path"] = ""

    link_df["top_left_x"] = -1
    link_df["top_left_y"] = -1
    link_df["bottom_right_x"] = -1
    link_df["bottom_right_y"] = -1
    link_df["found"] = False

    print("*"*10)

    link_df = link_df.sort_values(by="patch_id")
    origin_list = sorted(origin_list)
    origin_paths = sorted(origin_paths)

    if args.use_checkpoint:
        patches_list, patch_paths = use_checkpoint(LINK_PATH, 
                                                   patches_list,
                                                   patch_paths)
        
    if len(args.ignore_patches):
        patches_list, patch_paths = ignore_patches(args.ignore_patches,
                                                   patches_list,
                                                   patch_paths)

    last_img_index = 0
    for rows in link_df.iterrows():
        index = rows[0]
        index_info = rows[1]

        patch_path = index_info.patch_path
        patch_name = index_info.patch_id

        if patch_name not in patches_list:
            continue

        if not os.path.exists(patch_path) and patch_path != "/":
            continue

        patch_img_rgb = cv.imread(patch_path)
        patch_img = cv.cvtColor(patch_img_rgb, cv.IMREAD_GRAYSCALE)
        pw, ph = patch_img.shape[:-1]

        print(f"Searching for origin of patch {patch_name}")

        origin_paths[last_img_index], origin_paths[0] = origin_paths[0], origin_paths[last_img_index]
        origin_list[last_img_index], origin_list[0] = origin_list[0], origin_list[last_img_index]

        for index, (origin_name, origin_path) in enumerate(zip(origin_list, origin_paths)):
            print(f"Reading path of image {origin_path}")

            if not os.path.exists(origin_path) and origin_path != "/":
                continue

            img_rgb = cv.imread(origin_path)
            img = cv.cvtColor(img_rgb, cv.IMREAD_GRAYSCALE)

            method = cv.TM_CCOEFF_NORMED

            res = cv.matchTemplate(img, patch_img, method)
            min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
            
            loc = np.where(res > 0.7)
            
            if not len(loc[0]) and not len(loc[1]):
                continue
            
            print(f"Found origin of patch {patch_name}, image {origin_name}.")

            top_left = max_loc
            bottom_right = (top_left[0] + pw, top_left[1] + ph)   
            
            link_df.at[index, "public_id"]  = int(origin_name)
            link_df.at[index, "public_path"]  = origin_path

            link_df.at[index, "top_left_x"] = top_left[0]
            link_df.at[index, "top_left_y"] = -top_left[1]
            link_df.at[index, "bottom_right_x"] = bottom_right[0]
            link_df.at[index, "bottom_right_y"] = bottom_right[1]
            link_df.at[index, "found"] = True

            cv.rectangle(img_rgb, top_left, bottom_right, 255, 2)

            plt.subplot(1, 2, 1), plt.imshow(patch_img_rgb)
            plt.title('Patch Point'), plt.xticks([]), plt.yticks([])

            plt.subplot(1, 2, 2), plt.imshow(img_rgb)
            plt.title('Detected point'), plt.xticks([]), plt.yticks([])
            
            plt.savefig(LINK_PATH / "images" /f"patch_{patch_name}_origin_{origin_name}")
            last_img_index = index
            break

    add = 0

    while True:
        if not add:
            path = LINK_PATH / "ndb_pndb_relation.csv"
        else:
            path = LINK_PATH / f"ndb_pndb_relation_{add}.csv"

        if not os.path.exists(path):
            link_df.to_csv(path, index=False)
            break