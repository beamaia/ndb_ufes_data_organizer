import json
import pathlib as pl
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from src.utils.logger import logger

@dataclass
class ModelRunMetadata:
    run_timestamp: str
    model_name: str
    model_id: str
    description: str
    
    priority: int
    category: str
    source: str
    extract_method: str
    input_size: int
    output_dim: int
    batch_size: int
    device: str
    num_labels: int
    pretrained: bool
    
    num_patches: int
    num_origins: int
    avg_patches_per_origin: float
    
    cache_hits: int
    cache_total: int
    cache_hit_rate_percent: float
    extraction_duration_seconds: float
    patches_per_second: float
    
    embeddings_output_path: str
    
    status: str  # "success" or "failed"
    error_message: Optional[str] = None

class MetadataTracker:    
    def __init__(self, metadata_dir: Optional[str] = None):
        """ 
        Args:
            metadata_dir: Directory to save metadata. Defaults to results/phase1_metadata/
        """
        if metadata_dir is None:
            metadata_dir = pl.Path(__file__).parent.parent.parent.parent / "results" / "phase1_metadata"
        
        self.metadata_dir = pl.Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self.master_file = self.metadata_dir / "master_runs.json"
        self.runs = []
        
        self._load_existing_runs()
        
        logger.info(f"MetadataTracker initialized at {self.metadata_dir}")
    
    def _load_existing_runs(self):
        if self.master_file.exists():
            try:
                with open(self.master_file, 'r') as f:
                    data = json.load(f)
                    self.runs = [ModelRunMetadata(**run) for run in data.get('runs', [])]
                logger.info(f"Loaded {len(self.runs)} existing model runs from {self.master_file}")
            except Exception as e:
                logger.warning(f"Failed to load existing metadata: {e}")
                self.runs = []
        else:
            self.runs = []
    
    def add_run(self, metadata: ModelRunMetadata):
        """
        Add a new model run to tracking
        
        Args:
            metadata: ModelRunMetadata object with all extraction details
        """
        self.runs.append(metadata)
        logger.info(f"Added metadata for {metadata.model_name} to tracker")
    
    def save(self):
        try:
            runs_data = [asdict(run) for run in self.runs]
            
            output_data = {
                "metadata_file_last_updated": datetime.now().isoformat(),
                "total_runs_tracked": len(self.runs),
                "runs": runs_data
            }
            
            with open(self.master_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            logger.info(f"Metadata saved to {self.master_file}")
            logger.info(f"\tTotal runs tracked: {len(self.runs)}")
            
            self._save_summary()
            
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise
    
    def _save_summary(self):
        try:
            summary_file = self.metadata_dir / "runs_summary.txt"
            
            with open(summary_file, 'w') as f:
                f.write("-" * 100 + "\n")
                f.write("PHASE 1 EXTRACTION RUNS SUMMARY\n")
                f.write("-" * 100 + "\n\n")
                
                runs_by_timestamp = {}
                for run in self.runs:
                    if run.run_timestamp not in runs_by_timestamp:
                        runs_by_timestamp[run.run_timestamp] = []
                    runs_by_timestamp[run.run_timestamp].append(run)
                
                for timestamp in sorted(runs_by_timestamp.keys(), reverse=True):
                    runs = runs_by_timestamp[timestamp]
                    f.write(f"\nRun Timestamp: {timestamp}\n")
                    f.write("-" * 100 + "\n")
                    
                    successful = [r for r in runs if r.status == "success"]
                    failed = [r for r in runs if r.status == "failed"]
                    
                    f.write(f"Status: {len(successful)}/{len(runs)} models successfully extracted\n")
                    
                    if failed:
                        f.write(f"Failed models: {', '.join([r.model_name for r in failed])}\n")
                    
                    f.write("\nModel Details:\n")
                    for run in runs:
                        f.write(f"\n  {run.model_name}\n")
                        f.write(f"\tModel ID: {run.model_id}\n")
                        f.write(f"\tStatus: {run.status}\n")
                        if run.error_message:
                            f.write(f"\tError: {run.error_message}\n")
                        else:
                            f.write(f"\tBatch Size: {run.batch_size}\n")
                            f.write(f"\tDevice: {run.device}\n")
                            f.write(f"\tPatches Processed: {run.num_patches}\n")
                            f.write(f"\tExtraction Time: {run.extraction_duration_seconds:.2f}s ({run.patches_per_second:.1f} patches/sec)\n")
                            f.write(f"\tCache Hit Rate: {run.cache_hit_rate_percent:.1f}% ({run.cache_hits}/{run.cache_total})\n")
                            f.write(f"\tOutput: {run.embeddings_output_path}\n")
                    
                    f.write("\n")
            
            logger.info(f"Summary saved to {summary_file}")
            
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
    
    def get_run_by_model(self, model_name: str, run_timestamp: Optional[str] = None) -> Optional[ModelRunMetadata]:
        """
        Retrieve metadata for a specific model run (useful for notebook)
        
        Args:
            model_name: Name of the model
            run_timestamp: Optional specific timestamp to filter by
            
        Returns:
            ModelRunMetadata or None if not found
        """
        matches = [r for r in self.runs if r.model_name == model_name]
        
        if run_timestamp:
            matches = [r for r in matches if r.run_timestamp == run_timestamp]
        
        return matches[0] if matches else None
    
    
    def get_failed_runs(self) -> List[ModelRunMetadata]:
        return [r for r in self.runs if r.status == "failed"]
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.runs:
            return {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "success_rate": 0.0,
                "avg_extraction_time": 0.0,
                "avg_cache_hit_rate": 0.0
            }
        
        successful = [r for r in self.runs if r.status == "success"]
        failed = [r for r in self.runs if r.status == "failed"]
        
        return {
            "total_runs": len(self.runs),
            "successful_runs": len(successful),
            "failed_runs": len(failed),
            "success_rate": (len(successful) / len(self.runs)) * 100 if self.runs else 0,
            "avg_extraction_time": sum(r.extraction_duration_seconds for r in successful) / len(successful) if successful else 0,
            "avg_cache_hit_rate": sum(r.cache_hit_rate_percent for r in successful) / len(successful) if successful else 0,
            "total_patches_processed": sum(r.num_patches for r in successful),
            "total_extraction_time": sum(r.extraction_duration_seconds for r in successful)
        }
