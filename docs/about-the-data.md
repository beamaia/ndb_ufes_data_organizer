# About the Data

This is a study of the NDB-UFES dataset and of P-NDB-UFES, the dataset of patches cut from its images. Two other datasets, internal ones that hold earlier information, were used to link each patch to the image it was cut from and to verify that link: **SAB** and **patches_data**. They are the internal material the published P-NDB-UFES was made from. They are not published here.

## The four datasets

| Dataset | Public | What it is | Classes |
| --- | --- | --- | --- |
| NDB-UFES | Yes | Whole histopathology images with patient data and a diagnosis for each image. | OSCC, leukoplakia with dysplasia, leukoplakia without dysplasia |
| P-NDB-UFES | Yes | Patches cut from parent images, labelled one by one. | OSCC, leukoplakia with dysplasia, leukoplakia without dysplasia |
| SAB | No | The internal dataset the patches were generated from: the parent images, filed by the SAB database. | `carcinoma`, `leucoplasia`, `benigno` (three folders) |
| patches_data | No | The internal patches with the labels the dental team gave them, divided into hold-out sets. | `carcinoma`, `with_dysplasia`, `no_dysplasia` (three folders), which correspond to OSCC, leukoplakia with dysplasia and leukoplakia without dysplasia |

## NDB-UFES and P-NDB-UFES

P-NDB-UFES was not built specifically on NDB-UFES. It does contain patches for most of the NDB-UFES images, but it also contains patches that do not belong to any NDB-UFES image: they were cut from other parent images that exist only in the internal SAB dataset.

Not every NDB-UFES image has patches. Some are also in SAB but were never cut into usable patches, and some images exist only in NDB-UFES: they are not in SAB, and they have no patches in P-NDB-UFES. The [factsheet of NDB-UFES](factsheet-ndb-ufes.md) and the [factsheet of P-NDB-UFES](factsheet-p-ndb-ufes.md) have the counts.

## SAB

SAB is the internal dataset that was used to generate the patches. It contains the parent images, and many of them are also in NDB-UFES: the same image is found in both datasets. The rest exist only in SAB.

Its classes differ from the NDB-UFES classes. SAB files its images in three folders, `carcinoma`, `leucoplasia` and `benigno`, and these are not one to one with the three NDB-UFES classes. They also conflict with them: `carcinoma` holds mostly OSCC but also pictures NDB-UFES diagnoses with dysplasia, `leucoplasia` is a broad folder that holds all three diagnoses, and `benigno` has no picture in NDB-UFES at all. This is because SAB is an internal dataset: its information comes from the SAB database, and not from the later work of validating each image and its class. For that reason the SAB folders are never used as classes in this study.

The SAB images are not published. Publishing them would first need each image to be relabeled and verified, the way NDB-UFES was. Parts of them are shown in the [atlases](matching-and-atlases.md) only because their patches are already published with labels, and the class shown there is not verified.

SAB image names carry specific hashes: a masked patient prefix and a photo identifier. Those names are what tie a patch back to a patient and to a parent image.

## patches_data

patches_data is the earlier division of the patches. It uses the same classes as P-NDB-UFES, under folder names, and it holds the joint information of the labelling work the dental team did on the patches afterwards. It does not conflict with P-NDB-UFES: it only organizes the patches into hold-out divisions (train and test) instead of folds, and those divisions are not used here.

It keeps the original names. A patch is named after its parent image's hash, then its patch number: `hash_1`, `hash_2` and so on.

Here it was used afterwards, together with SAB, as a confirmation: it shows that the SIFT and template matching algorithms had grouped the information properly. The patch in patches_data with the same pixels as a P-NDB-UFES patch must carry the same name and the same class.

## Patches that were not kept

Many patches were cut from each parent image, but not all of them were saved. Some showed only background, some were too blurry, and some were too hard to label or were judged unusable. So P-NDB-UFES holds only the patches that could be labelled, and some parent images have no patches at all.

## Two ways to organize the data, one result

The data was organized in two different ways, and they arrived at the same results:

1. **By the images themselves.** Template matching finds each patch in its parent image, and SIFT finds the pictures that show the same tissue. Template matching suits patches because a patch is a straight crop: its size and color do not vary. SIFT is used between pictures, because pictures vary in zoom, color and rotation.
2. **By the names.** The SAB file names carry the masked patient prefix and the photo identifier, and patches_data keeps those names, so a prefix search ties each patch to a photo and a patient.

For every patch, the picture that template matching finds is the picture its name points to: all 3,763 agree. The one place where the names and the pixels do not line up is a single photo that the SAB database filed under two different prefixes. It is flagged for review, and its cases are kept together. The [reproducibility page](reproducibility.md) describes each step and what it guarantees.

## How the data was reconstructed

The prefixes were added late. They come from archived files that were hard to locate and were recovered only after a long search, so they could not be used from the start. This reflects how the project has run: it has many fronts and many steps, involves different people, and the organization of the data was rebuilt step by step as new material was found. The two routes above were therefore not planned together. They were built at different times from different material, which is why their agreement is meaningful.

## How the pieces are linked

1. Every patch is searched, by exact pixels, in every parent image from NDB-UFES and SAB.
2. The image found must be the one named in the patch's SAB file name, and the patch must match the patches_data patch with the same name and class.
3. Parent images that show the same tissue, zoomed or shifted, are tied together, and so are the images and patients that share evidence, into case groups.
4. The folds are cut on case groups, so patches of the same patient are never on both sides of an evaluation.

The [data dictionary](data-dictionary.md) explains every column of the tables this produces.
