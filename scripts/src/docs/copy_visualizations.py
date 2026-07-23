import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from src.utils.logger import logger

def copy_visualizations():
    """Copy HTML visualization files to docs folder for GitHub Pages."""
    
    source_dir = PROJECT_ROOT / "results/phase1/visualizations"
    dest_dir = PROJECT_ROOT / "docs/visualizations"
    
    if not source_dir.exists():
        logger.info(f"Source directory not found: {source_dir}")
        logger.info("   Run Phase 1 first: uv run python scripts/phase1.py")
        return
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    html_files = list(source_dir.glob("*.html"))
    if not html_files:
        logger.info(f"No HTML files found in {source_dir}")
        return
    
    logger.info(f"📋 Copying {len(html_files)} visualization files...")
    for html_file in html_files:
        # patch_clusters_3d_uni_20260421_183206.html → patch_clusters_3d_uni.html
        base_name = html_file.stem  # without .html
        parts = base_name.split('_')
        
        if len(parts) >= 4 and parts[-2].isdigit() and len(parts[-2]) == 8:
            clean_name = '_'.join(parts[:-2]) + ".html"
        else:
            clean_name = html_file.name
        
        dest_file = dest_dir / clean_name
        shutil.copy2(html_file, dest_file)
        logger.info(f"{html_file.name} → {clean_name}")

if __name__ == "__main__":
    copy_visualizations()
