"""
Storage management for extracted files
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.models.schemas import FileDiscoveryOutput


class StorageManager:
    """
    Manages storage directories and file organization
    """
    
    def __init__(
        self,
        storage_base: str = "./storage",
        uploads_dir: str = "uploads",
        extracted_dir: str = "extracted",
        profiles_dir: str = "profiles",
        index_dir: str = "index",
        temp_dir: str = "temp"
    ):
        self.storage_base = Path(storage_base)
        self.uploads_dir = self.storage_base / uploads_dir
        self.extracted_dir = self.storage_base / extracted_dir
        self.profiles_dir = self.storage_base / profiles_dir
        self.index_dir = self.storage_base / index_dir
        self.temp_dir = self.storage_base / temp_dir
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """
        Create storage directories if they don't exist
        """
        for directory in [
            self.storage_base,
            self.uploads_dir,
            self.extracted_dir,
            self.profiles_dir,
            self.index_dir,
            self.temp_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def create_job_directory(self, job_id: str) -> Path:
        """
        Create extraction directory for a job
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Path to created directory
        """
        job_dir = self.extracted_dir / job_id
        
        if job_dir.exists():
            # Clean existing directory
            shutil.rmtree(job_dir)
        
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (job_dir / "documents").mkdir(exist_ok=True)
        (job_dir / "spreadsheets").mkdir(exist_ok=True)
        (job_dir / "images").mkdir(exist_ok=True)
        (job_dir / "videos").mkdir(exist_ok=True)
        (job_dir / "unknown").mkdir(exist_ok=True)
        
        return job_dir
    
    def get_job_directory(self, job_id: str) -> Path:
        """
        Get job directory path
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Path to job directory
        """
        return self.extracted_dir / job_id
    
    def get_upload_directory(self) -> Path:
        """
        Get uploads directory
        
        Returns:
            Path to uploads directory
        """
        return self.uploads_dir
    
    def get_profile_path(self, job_id: str) -> Path:
        """
        Get path for storing business profile
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Path to profile file
        """
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        return self.profiles_dir / f"{job_id}.json"
    
    def get_index_path(self, job_id: str) -> Path:
        """
        Get path for storing page index
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Path to index directory
        """
        index_path = self.index_dir / job_id
        index_path.mkdir(parents=True, exist_ok=True)
        return index_path
    
    def get_temp_directory(self, job_id: Optional[str] = None) -> Path:
        """
        Get temporary directory
        
        Args:
            job_id: Optional job ID for job-specific temp dir
            
        Returns:
            Path to temp directory
        """
        if job_id:
            temp_path = self.temp_dir / job_id
            temp_path.mkdir(parents=True, exist_ok=True)
            return temp_path
        return self.temp_dir
    
    def cleanup_job_directory(self, job_id: str, keep_profiles: bool = True) -> bool:
        """
        Clean up job extraction directory
        
        Args:
            job_id: Unique job identifier
            keep_profiles: If True, don't delete profile files
            
        Returns:
            True if cleanup successful
        """
        job_dir = self.get_job_directory(job_id)
        
        if not job_dir.exists():
            return True
        
        try:
            if keep_profiles:
                # Move profiles to safe location before cleanup
                profiles_subdir = job_dir / "profiles"
                if profiles_subdir.exists():
                    shutil.copytree(
                        profiles_subdir,
                        self.profiles_dir / job_id,
                        dirs_exist_ok=True
                    )
            
            shutil.rmtree(job_dir)
            return True
            
        except Exception as e:
            print(f"Error cleaning up job directory: {e}")
            return False
    
    def cleanup_temp_directory(self, job_id: str) -> bool:
        """
        Clean up job temporary directory
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if cleanup successful
        """
        temp_dir = self.get_temp_directory(job_id)
        
        if not temp_dir.exists():
            return True
        
        try:
            shutil.rmtree(temp_dir)
            return True
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")
            return False
    
    def get_storage_stats(self) -> dict:
        """
        Get storage usage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        def get_dir_size(path: Path) -> int:
            total = 0
            if path.exists():
                for entry in path.rglob('*'):
                    if entry.is_file():
                        total += entry.stat().st_size
            return total
        
        return {
            "storage_base": str(self.storage_base),
            "uploads_size_bytes": get_dir_size(self.uploads_dir),
            "extracted_size_bytes": get_dir_size(self.extracted_dir),
            "profiles_size_bytes": get_dir_size(self.profiles_dir),
            "index_size_bytes": get_dir_size(self.index_dir),
            "temp_size_bytes": get_dir_size(self.temp_dir),
        }
    
    def organize_extracted_file(
        self,
        file_path: Path,
        file_category: str,
        job_id: str
    ) -> Path:
        """
        Move extracted file to appropriate category subdirectory
        
        Args:
            file_path: Path to extracted file
            file_category: Category (document, spreadsheet, image, video, unknown)
            job_id: Unique job identifier
            
        Returns:
            New path of organized file
        """
        job_dir = self.get_job_directory(job_id)
        category_dir = job_dir / file_category
        
        if not category_dir.exists():
            category_dir.mkdir(parents=True, exist_ok=True)
        
        # Move file to category directory
        new_path = category_dir / file_path.name
        
        # Handle name conflicts
        if new_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_path = category_dir / f"{stem}_{timestamp}{suffix}"
        
        shutil.move(str(file_path), str(new_path))
        return new_path
    
    def save_discovery_output(
        self,
        output: FileDiscoveryOutput,
        job_id: str
    ) -> Path:
        """
        Save file discovery output to job directory
        
        Args:
            output: File discovery output
            job_id: Unique job identifier
            
        Returns:
            Path to saved metadata file
        """
        job_dir = self.get_job_directory(job_id)
        metadata_path = job_dir / "discovery_metadata.json"
        
        import json
        with open(metadata_path, 'w') as f:
            # Convert Pydantic model to dict
            output_dict = output.model_dump(mode='json')
            json.dump(output_dict, f, indent=2)
        
        return metadata_path
