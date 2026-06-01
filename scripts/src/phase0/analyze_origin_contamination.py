import pathlib as pl
import pandas as pd
import matplotlib.pyplot as plt
import cv2 as cv
import numpy as np

from utils import logger


def orb_sim(img1, img2, thrs=50):
    """
    Compute similarity between two images using ORB feature matching.
    
    Source: https://github.com/bnsreenu/python_for_microscopists/blob/master/191_measure_img_similarity.py
    
    Args:
        img1: First image (numpy array)
        img2: Second image (numpy array)
        thrs: Distance threshold for feature matches (0-100)
        
    Returns:
        float: Proportion of matches below threshold (0.0 to 1.0)
    """
    orb = cv.ORB_create()
    
    # detect keypoints and descriptors
    kp_a, desc_a = orb.detectAndCompute(img1, None)
    kp_b, desc_b = orb.detectAndCompute(img2, None)
    
    # brute-force matcher
    bf = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)
    matches = bf.match(desc_a, desc_b)
    
    # find matches with distance < threshold
    similar_regions = [i for i in matches if i.distance < thrs]
    
    if len(matches) == 0:
        return 0
    return len(similar_regions) / len(matches)


def analyze_origin_contamination(origin_id, link_df, patches_images_dir, 
                                  output_dir=None, similarity_threshold=0.7):
    """
    Analyze a single origin for contamination by computing all patch similarities.
    
    Args:
        origin_id: Origin ID to analyze (e.g., "0011")
        link_df: DataFrame with columns ["patch", "origin"]
        patches_images_dir: Path to directory with patch images
        output_dir: Directory to save visualizations (optional)
        similarity_threshold: Threshold for flagging contamination (default 0.7)
        
    Returns:
        dict: {
            'similarity_matrix': 2D list of similarity scores,
            'images_names': List of patch IDs,
            'contaminated_pairs': List of tuples (patch1, patch2) with high similarity
        }
    """
    origin_patches = link_df[link_df["origin"] == origin_id].reset_index(drop=True)
    n_patches = len(origin_patches)
    
    logger.info(f"\nAnalyzing origin {origin_id} with {n_patches} patches...")
    
    similarity_matrix = [[-1 for _ in range(n_patches)] for _ in range(n_patches)]
    images_names = []
    
    for i, row_i in enumerate(origin_patches.iterrows()):
        patch_i = row_i[1]["patch"]
        images_names.append(patch_i)
        
        img1_path = patches_images_dir / f"{patch_i}.png"
        img1 = cv.imread(str(img1_path), cv.IMREAD_COLOR)
        
        if img1 is None:
            logger.info(f"  Warning: Could not load {patch_i}.png")
            continue
        
        for j, row_j in enumerate(origin_patches.iterrows()):
            patch_j = row_j[1]["patch"]
            img2_path = patches_images_dir / f"{patch_j}.png"
            img2 = cv.imread(str(img2_path), cv.IMREAD_COLOR)
            
            if img2 is None:
                continue
            
            similarity = orb_sim(img1, img2)
            similarity_matrix[i][j] = similarity
            
            # symmetric: if computed, set both [i][j] and [j][i]
            if i != j:
                similarity_matrix[j][i] = similarity
            else:
                break
    
    # find contaminated pairs (high similarity, excluding diagonal)
    contaminated_pairs = []
    for i in range(n_patches):
        for j in range(i + 1, n_patches):
            if similarity_matrix[i][j] >= similarity_threshold:
                contaminated_pairs.append((images_names[i], images_names[j]))
    
    if output_dir:
        output_dir = pl.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        plt.figure(figsize=(10, 10))
        plt.imshow(similarity_matrix, cmap="PuRd")
        plt.colorbar()
        plt.title(f"Patch Similarity Matrix - Origin {origin_id}")
        plt.savefig(output_dir / f"similarity_matrix_{origin_id}.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"  Saved visualization to {output_dir / f'similarity_matrix_{origin_id}.png'}")
    
    return {
        'origin_id': origin_id,
        'similarity_matrix': similarity_matrix,
        'images_names': images_names,
        'contaminated_pairs': contaminated_pairs,
        'n_patches': n_patches,
        'n_contaminated_pairs': len(contaminated_pairs)
    }


def visualize_contaminated_pairs(contaminated_pairs, patches_images_dir, 
                                 output_file=None, figsize=(5, 180)):
    """
    Create side-by-side visualization of contaminated patch pairs.
    
    Args:
        contaminated_pairs: List of tuples (patch1, patch2)
        patches_images_dir: Path to patch images directory
        output_file: File to save visualization (optional)
        figsize: Figure size (width, height)
    """
    if not contaminated_pairs:
        logger.info("No contaminated pairs to visualize.")
        return
    
    plt.figure(figsize=figsize)
    
    for i, (patch1_id, patch2_id) in enumerate(contaminated_pairs):
        img1_path = patches_images_dir / f"{patch1_id}.png"
        img1 = cv.imread(str(img1_path), cv.IMREAD_COLOR)
        img1_rgb = cv.cvtColor(img1, cv.COLOR_BGR2RGB) if img1 is not None else None
        
        img2_path = patches_images_dir / f"{patch2_id}.png"
        img2 = cv.imread(str(img2_path), cv.IMREAD_COLOR)
        img2_rgb = cv.cvtColor(img2, cv.COLOR_BGR2RGB) if img2 is not None else None
        
        plt.subplot(len(contaminated_pairs), 2, i * 2 + 1)
        if img1_rgb is not None:
            plt.imshow(img1_rgb)
        plt.title(patch1_id)
        plt.axis('off')
        
        plt.subplot(len(contaminated_pairs), 2, i * 2 + 2)
        if img2_rgb is not None:
            plt.imshow(img2_rgb)
        plt.title(patch2_id)
        plt.axis('off')
    
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        logger.info(f"Saved contaminated pairs visualization to {output_file}")
    
    plt.close()


if __name__ == "__main__":
    WORK_DIR = pl.Path(__file__).parent.parent
    PATCHES_DIR = WORK_DIR / "data/ndb_ufes/patch_level/images"
    LINK_FILE = WORK_DIR / "data/ndb_ufes/patch_level/csvs/parcial_pndb_ufes.csv"
    OUTPUT_DIR = WORK_DIR / "results/contamination_analysis"
    
    link_df = pd.read_csv(LINK_FILE)
    link_df["origin"] = link_df["origin"].astype(str).str.zfill(4)
    link_df = link_df[["patch", "origin"]].drop_duplicates()
    
    origin_counts = link_df["origin"].value_counts()
    high_patch_origins = origin_counts.head(10).index.tolist()
    
    logger.info(f"Analyzing top {len(high_patch_origins)} origins by patch count...")
    results = []
    
    for origin_id in high_patch_origins[:1]:  # start with top 1 (origin 0011)
        result = analyze_origin_contamination(
            origin_id,
            link_df,
            PATCHES_DIR,
            output_dir=OUTPUT_DIR,
            similarity_threshold=0.7
        )
        results.append(result)
        
        logger.info(f"Origin {origin_id}:")
        logger.info(f"\t- Total patches: {result['n_patches']}")
        logger.info(f"\t- Contaminated pairs: {result['n_contaminated_pairs']}")
        if result['contaminated_pairs']:
            logger.info(f"\t- Pairs: {result['contaminated_pairs'][:5]}{'...' if len(result['contaminated_pairs']) > 5 else ''}")
        
        if result['contaminated_pairs']:
            visualize_contaminated_pairs(
                result['contaminated_pairs'],
                PATCHES_DIR,
                output_file=OUTPUT_DIR / f"contaminated_pairs_{origin_id}.png"
            )
    
    logger.info("\n" + "="*60)
    logger.info("CONTAMINATION ANALYSIS SUMMARY")
    logger.info("="*60)
    for result in results:
        logger.info(f"Origin {result['origin_id']}: {result['n_contaminated_pairs']} contaminated pairs detected")
