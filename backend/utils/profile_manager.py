"""
Profile Manager - Save/Load/Update Business Profiles

Handles persistence of business profiles to JSON files,
enabling manual editing and incremental updates.
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# Default storage location
PROFILES_DIR = Path(__file__).parent.parent.parent / "storage" / "profiles"


class ProfileManager:
    """
    Manages business profile persistence.
    
    Features:
    - Save profiles as JSON files
    - Load profiles by job_id
    - Update individual services within a profile
    - List all saved profiles
    - Export profile for download
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else PROFILES_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ProfileManager initialized: {self.storage_dir}")
    
    def save_profile(self, job_id: str, profile_data: Dict[str, Any]) -> str:
        """
        Save a business profile to JSON file.
        
        Args:
            job_id: Unique job identifier
            profile_data: Profile dictionary
            
        Returns:
            Path to saved file
        """
        filepath = self.storage_dir / f"{job_id}_profile.json"
        
        # Add save metadata
        profile_data['_metadata'] = {
            'saved_at': datetime.now().isoformat(),
            'job_id': job_id,
            'version': profile_data.get('_metadata', {}).get('version', 0) + 1,
            'last_edited_by': 'manual_ui'
        }
        
        # Create backup if file exists
        if filepath.exists():
            backup_path = self.storage_dir / f"{job_id}_profile.backup.json"
            shutil.copy2(filepath, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Profile saved: {filepath}")
        return str(filepath)
    
    def load_profile(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a business profile from JSON file.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Profile dictionary or None
        """
        filepath = self.storage_dir / f"{job_id}_profile.json"
        
        if not filepath.exists():
            logger.warning(f"Profile not found: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        logger.info(f"Profile loaded: {filepath}")
        return profile_data
    
    def update_service(self, job_id: str, service_index: int, service_data: Dict[str, Any]) -> bool:
        """
        Update a specific service in the profile.
        
        Args:
            job_id: Unique job identifier
            service_index: Index of service to update
            service_data: Updated service data
            
        Returns:
            True if successful
        """
        profile = self.load_profile(job_id)
        if not profile:
            logger.error(f"Cannot update service: profile not found for {job_id}")
            return False
        
        services = profile.get('services', [])
        if service_index >= len(services):
            logger.error(f"Service index {service_index} out of range (total: {len(services)})")
            return False
        
        services[service_index] = service_data
        profile['services'] = services
        
        self.save_profile(job_id, profile)
        logger.info(f"Service {service_index} updated for job {job_id}")
        return True
    
    def add_service(self, job_id: str, service_data: Dict[str, Any]) -> bool:
        """
        Add a new service to the profile.
        
        Args:
            job_id: Unique job identifier
            service_data: New service data
            
        Returns:
            True if successful
        """
        profile = self.load_profile(job_id)
        if not profile:
            logger.error(f"Cannot add service: profile not found for {job_id}")
            return False
        
        services = profile.get('services', [])
        service_data['service_id'] = f"svc_{len(services)}"
        services.append(service_data)
        profile['services'] = services
        
        self.save_profile(job_id, profile)
        logger.info(f"New service added to job {job_id} (total: {len(services)})")
        return True
    
    def delete_service(self, job_id: str, service_index: int) -> bool:
        """
        Delete a service from the profile.
        
        Args:
            job_id: Unique job identifier
            service_index: Index of service to delete
            
        Returns:
            True if successful
        """
        profile = self.load_profile(job_id)
        if not profile:
            return False
        
        services = profile.get('services', [])
        if service_index >= len(services):
            return False
        
        removed = services.pop(service_index)
        
        # Re-index service IDs
        for i, svc in enumerate(services):
            svc['service_id'] = f"svc_{i}"
        
        profile['services'] = services
        self.save_profile(job_id, profile)
        logger.info(f"Service '{removed.get('name', 'unknown')}' deleted from job {job_id}")
        return True
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all saved profiles.
        
        Returns:
            List of profile summaries
        """
        profiles = []
        for filepath in self.storage_dir.glob("*_profile.json"):
            if filepath.name.endswith('.backup.json'):
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                profiles.append({
                    'job_id': data.get('_metadata', {}).get('job_id', filepath.stem.replace('_profile', '')),
                    'business_name': data.get('business_info', {}).get('name', 'Unknown'),
                    'business_type': data.get('business_type', 'unknown'),
                    'services_count': len(data.get('services', [])),
                    'products_count': len(data.get('products', [])),
                    'saved_at': data.get('_metadata', {}).get('saved_at', 'Unknown'),
                    'filepath': str(filepath)
                })
            except Exception as e:
                logger.warning(f"Failed to read profile {filepath}: {e}")
        
        return sorted(profiles, key=lambda x: x.get('saved_at', ''), reverse=True)
    
    def export_profile(self, job_id: str) -> Optional[str]:
        """
        Export profile as formatted JSON string (for download).
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            JSON string or None
        """
        profile = self.load_profile(job_id)
        if not profile:
            return None
        
        # Remove internal metadata for export
        export_data = {k: v for k, v in profile.items() if not k.startswith('_')}
        
        return json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
    
    def calculate_completeness(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate profile completeness scores.
        
        Args:
            profile: Profile dictionary
            
        Returns:
            Completeness analysis
        """
        scores = {}
        
        # Business info score
        bi = profile.get('business_info', {})
        bi_fields = ['name', 'description', 'category']
        bi_contact = bi.get('contact', {})
        bi_filled = sum(1 for f in bi_fields if bi.get(f))
        bi_filled += sum(1 for f in ['phone', 'email', 'website'] if bi_contact.get(f))
        scores['business_info'] = bi_filled / 6
        
        # Services score
        services = profile.get('services', [])
        if services:
            svc_scores = []
            for svc in services:
                svc_score = 0
                total_fields = 13
                
                if svc.get('name'): svc_score += 1
                if svc.get('description') and len(svc.get('description', '')) > 20: svc_score += 1
                if svc.get('category'): svc_score += 1
                if svc.get('pricing') and svc['pricing'].get('base_price'): svc_score += 1
                if svc.get('details') and svc['details'].get('duration'): svc_score += 1
                if svc.get('itinerary') and len(svc.get('itinerary', [])) > 0: svc_score += 1
                if svc.get('inclusions') and len(svc.get('inclusions', [])) > 0: svc_score += 1
                if svc.get('exclusions') and len(svc.get('exclusions', [])) > 0: svc_score += 1
                if svc.get('cancellation_policy'): svc_score += 1
                if svc.get('payment_policy'): svc_score += 1
                if svc.get('travel_info'): svc_score += 1
                if svc.get('faqs') and len(svc.get('faqs', [])) > 0: svc_score += 1
                if svc.get('tags') and len(svc.get('tags', [])) > 1: svc_score += 1
                
                svc_scores.append(svc_score / total_fields)
            
            scores['services'] = sum(svc_scores) / len(svc_scores)
            scores['services_detail'] = svc_scores
        else:
            scores['services'] = 0.0
        
        # Overall
        scores['overall'] = (scores['business_info'] * 0.3 + scores.get('services', 0) * 0.7)
        
        return scores
