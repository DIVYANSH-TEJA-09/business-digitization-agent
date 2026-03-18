"""
Media Extraction Agent

Extracts embedded and standalone media (images, videos) from parsed documents.
Implements deduplication, quality assessment, and document association.
"""
import os
import io
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from PIL import Image
import imagehash

from backend.models.schemas import (
    MediaExtractionInput,
    MediaExtractionOutput,
    ExtractedImage,
    MediaCollection,
    ParsedDocument,
    Page,
)
from backend.models.enums import FileType
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class MediaExtractionError(Exception):
    """Base exception for media extraction errors"""
    pass


class MediaExtractionAgent:
    """
    Extracts media from parsed documents and standalone files
    
    Features:
    - Embedded image extraction from PDFs
    - Embedded image extraction from DOCX
    - Standalone media processing
    - Perceptual hashing for deduplication
    - Quality assessment
    - Document association
    """
    
    def __init__(
        self,
        enable_deduplication: bool = True,
        min_image_quality: float = 0.3,
        output_dir: Optional[str] = None
    ):
        """
        Initialize Media Extraction Agent
        
        Args:
            enable_deduplication: Enable duplicate image detection
            min_image_quality: Minimum quality score (0.0-1.0)
            output_dir: Directory to save extracted media
        """
        self.enable_deduplication = enable_deduplication
        self.min_image_quality = min_image_quality
        self.output_dir = output_dir or "./storage/extracted/media"
        self.image_utils = ImageUtils()
    
    def extract_all(self, input: MediaExtractionInput) -> MediaExtractionOutput:
        """
        Extract all media from documents and standalone files
        
        Args:
            input: Media extraction input
            
        Returns:
            Media extraction output
        """
        start_time = time.time()
        errors: List[str] = []
        all_images: List[ExtractedImage] = []
        
        logger.info(f"Starting media extraction for job {input.job_id}")
        logger.info(f"Documents to process: {len(input.parsed_documents)}")
        
        try:
            # Step 1: Extract embedded images from documents
            embedded_images = self._extract_from_documents(
                input.parsed_documents,
                input.job_id,
                errors
            )
            all_images.extend(embedded_images)
            logger.info(f"Extracted {len(embedded_images)} embedded images")
            
            # Step 2: Process standalone media files
            standalone_images = self._process_standalone_media(
                input.standalone_files,
                input.job_id,
                errors
            )
            all_images.extend(standalone_images)
            logger.info(f"Processed {len(standalone_images)} standalone images")
            
            # Step 3: Deduplicate if enabled
            duplicates_removed = 0
            if self.enable_deduplication and all_images:
                all_images, duplicates_removed = self._deduplicate_images(all_images)
                logger.info(f"Removed {duplicates_removed} duplicate images")
            
            # Step 4: Assess quality
            assessed_images = []
            for image in all_images:
                quality = self.image_utils.assess_quality(image.file_path)
                # Create updated metadata
                new_metadata = dict(image.metadata) if image.metadata else {}
                new_metadata['quality_score'] = quality.get('score', 0.0)
                new_metadata['resolution'] = quality.get('resolution', 'unknown')
                
                # Create new image with updated metadata
                updated_image = image.model_copy(update={'metadata': new_metadata})
                assessed_images.append(updated_image)
            
            all_images = assessed_images
            
            # Step 5: Calculate statistics
            processing_time = time.time() - start_time
            
            output = MediaExtractionOutput(
                job_id=input.job_id,
                success=len(all_images) > 0,
                media=MediaCollection(
                    images=all_images,
                    videos=[],  # Can be added later
                    total_count=len(all_images),
                    extraction_summary={
                        'embedded_count': len(embedded_images),
                        'standalone_count': len(standalone_images),
                        'duplicates_removed': duplicates_removed,
                        'total_size_bytes': sum(img.file_size for img in all_images)
                    }
                ),
                total_images=len(all_images),
                duplicates_removed=duplicates_removed,
                processing_time=processing_time,
                errors=errors
            )
            
            logger.info(
                f"Media extraction completed: {len(all_images)} images "
                f"in {processing_time:.2f}s"
            )
            
            return output
            
        except Exception as e:
            logger.exception(f"Unexpected error in media extraction: {e}")
            return MediaExtractionOutput(
                job_id=input.job_id,
                success=False,
                media=MediaCollection(images=[], videos=[], total_count=0),
                total_images=0,
                duplicates_removed=0,
                processing_time=time.time() - start_time,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def _extract_from_documents(
        self,
        documents: List[ParsedDocument],
        job_id: str,
        errors: List[str]
    ) -> List[ExtractedImage]:
        """
        Extract embedded images from parsed documents
        
        Args:
            documents: List of parsed documents
            job_id: Unique job identifier
            errors: List to append errors to
            
        Returns:
            List of extracted images
        """
        images = []
        
        for doc in documents:
            try:
                if doc.file_type == FileType.PDF:
                    doc_images = self._extract_from_pdf(doc)
                    images.extend(doc_images)
                elif doc.file_type == FileType.DOCX:
                    doc_images = self._extract_from_docx(doc)
                    images.extend(doc_images)
            except Exception as e:
                error_msg = f"Failed to extract images from {doc.source_file}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return images
    
    def _extract_from_pdf(self, doc: ParsedDocument) -> List[ExtractedImage]:
        """
        Extract embedded images from PDF using pdfplumber
        
        Args:
            doc: ParsedDocument object
            
        Returns:
            List of extracted images
        """
        images = []
        
        try:
            import pdfplumber
            
            with pdfplumber.open(doc.source_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    if not hasattr(page, 'images') or not page.images:
                        continue
                    
                    for i, img_info in enumerate(page.images):
                        try:
                            # Get xref (object reference)
                            xref = img_info.get('xref')
                            
                            if not xref:
                                continue
                            
                            # Extract image bytes using xref
                            raw_pdf = page.pdf.pdf
                            image_data = raw_pdf.extract_image(xref)
                            
                            if not image_data or 'image' not in image_data:
                                continue
                            
                            image_bytes = image_data['image']
                            
                            # Load with PIL to get format info
                            try:
                                image = Image.open(io.BytesIO(image_bytes))
                                
                                # Determine format
                                img_format = image.format.lower() if image.format else 'jpg'
                                
                                # Generate unique ID
                                image_id = f"pdf_{doc.doc_id}_p{page_num}_{i}"
                                
                                # Save image
                                output_path = self._save_image(
                                    image_bytes,
                                    image_id,
                                    img_format
                                )
                                
                                # Create ExtractedImage
                                extracted = ExtractedImage(
                                    image_id=image_id,
                                    file_path=output_path,
                                    source_doc=doc.source_file,
                                    source_page=page_num,
                                    width=image.width,
                                    height=image.height,
                                    file_size=len(image_bytes),
                                    mime_type=f"image/{img_format}",
                                    extraction_method="embedded_pdf",
                                    is_embedded=True,
                                    image_hash=self.image_utils.calculate_hash(image_bytes),
                                    metadata={
                                        'bbox': img_info.get('bbox'),
                                        'width': img_info.get('width'),
                                        'height': img_info.get('height'),
                                        'xref': xref
                                    }
                                )
                                
                                images.append(extracted)
                                
                            except Exception as e:
                                logger.warning(f"Failed to process image {i} on page {page_num}: {e}")
                                
                        except Exception as e:
                            logger.warning(f"Failed to extract image {i} on page {page_num}: {e}")
                            
        except Exception as e:
            logger.error(f"Failed to open PDF {doc.source_file}: {e}")
        
        return images
    
    def _extract_from_docx(self, doc: ParsedDocument) -> List[ExtractedImage]:
        """
        Extract embedded images from DOCX file
        
        Args:
            doc: ParsedDocument object
            
        Returns:
            List of extracted images
        """
        images = []
        
        try:
            import zipfile
            
            # DOCX files are ZIP archives
            with zipfile.ZipFile(doc.source_file) as docx_zip:
                # List all files in word/media/
                media_files = [
                    f for f in docx_zip.namelist()
                    if f.startswith('word/media/')
                ]
                
                for i, media_file in enumerate(media_files):
                    try:
                        # Extract image bytes
                        image_bytes = docx_zip.read(media_file)
                        
                        # Determine format from filename
                        img_format = self._detect_image_format(media_file)
                        
                        # Generate unique ID
                        image_id = f"docx_{doc.doc_id}_{i}"
                        
                        # Save image
                        output_path = self._save_image(
                            image_bytes,
                            image_id,
                            img_format
                        )
                        
                        # Get image dimensions
                        try:
                            with Image.open(io.BytesIO(image_bytes)) as img:
                                width = img.width
                                height = img.height
                        except Exception:
                            width, height = 0, 0
                        
                        # Create ExtractedImage
                        extracted = ExtractedImage(
                            image_id=image_id,
                            file_path=output_path,
                            source_doc=doc.source_file,
                            source_page=1,  # DOCX doesn't have fixed pages
                            width=width,
                            height=height,
                            file_size=len(image_bytes),
                            mime_type=f"image/{img_format}",
                            extraction_method="embedded_docx",
                            is_embedded=True,
                            image_hash=self.image_utils.calculate_hash(image_bytes),
                            metadata={
                                'original_filename': os.path.basename(media_file),
                                'extraction_method': 'docx_zip'
                            }
                        )
                        
                        images.append(extracted)
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract {media_file}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to open DOCX {doc.source_file}: {e}")
        
        return images
    
    def _process_standalone_media(
        self,
        standalone_files: List[str],
        job_id: str,
        errors: List[str]
    ) -> List[ExtractedImage]:
        """
        Process standalone image files
        
        Args:
            standalone_files: List of file paths
            job_id: Unique job identifier
            errors: List to append errors to
            
        Returns:
            List of processed images
        """
        images = []
        
        for file_path in standalone_files:
            try:
                # Read file
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                
                # Determine format
                img_format = self._detect_image_format(file_path)
                
                # Generate unique ID
                image_id = f"standalone_{job_id}_{os.path.basename(file_path)}"
                
                # Save image
                output_path = self._save_image(
                    image_bytes,
                    image_id,
                    img_format
                )
                
                # Get dimensions
                with Image.open(io.BytesIO(image_bytes)) as img:
                    width = img.width
                    height = img.height
                
                # Create ExtractedImage
                extracted = ExtractedImage(
                    image_id=image_id,
                    file_path=output_path,
                    source_doc=None,
                    source_page=None,
                    width=width,
                    height=height,
                    file_size=len(image_bytes),
                    mime_type=f"image/{img_format}",
                    extraction_method="standalone",
                    is_embedded=False,
                    image_hash=self.image_utils.calculate_hash(image_bytes),
                    metadata={
                        'original_path': file_path,
                        'extraction_method': 'standalone_copy'
                    }
                )
                
                images.append(extracted)
                
            except Exception as e:
                error_msg = f"Failed to process {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return images
    
    def _deduplicate_images(
        self,
        images: List[ExtractedImage]
    ) -> Tuple[List[ExtractedImage], int]:
        """
        Remove duplicate images using perceptual hashing
        
        Args:
            images: List of images
            
        Returns:
            Tuple of (unique images, duplicates removed count)
        """
        if not images:
            return images, 0
        
        seen_hashes = {}
        unique_images = []
        duplicates = 0
        
        for image in images:
            img_hash = image.image_hash
            
            if img_hash in seen_hashes:
                # Found duplicate
                duplicates += 1
                
                # Keep higher quality version
                existing = seen_hashes[img_hash]
                existing_quality = existing.metadata.get('quality_score', 0.5) if existing.metadata else 0.5
                new_quality = image.metadata.get('quality_score', 0.5) if image.metadata else 0.5
                
                if new_quality > existing_quality:
                    # Replace with better quality
                    seen_hashes[img_hash] = image
                    logger.info(
                        f"Replaced duplicate {existing.image_id} with "
                        f"higher quality {image.image_id}"
                    )
            else:
                seen_hashes[img_hash] = image
                unique_images.append(image)
        
        return unique_images, duplicates
    
    def _save_image(
        self,
        image_bytes: bytes,
        image_id: str,
        img_format: str
    ) -> str:
        """
        Save image to output directory
        
        Args:
            image_bytes: Raw image bytes
            image_id: Unique image identifier
            img_format: Image format (jpg, png, etc.)
            
        Returns:
            Path to saved image
        """
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate filename
        filename = f"{image_id}.{img_format}"
        output_path = os.path.join(self.output_dir, filename)
        
        # Save file
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        return output_path
    
    def _detect_image_format(self, filename: str) -> str:
        """
        Detect image format from filename
        
        Args:
            filename: Image filename
            
        Returns:
            Format string (jpg, png, etc.)
        """
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        format_map = {
            'jpg': 'jpg',
            'jpeg': 'jpg',
            'png': 'png',
            'gif': 'gif',
            'bmp': 'bmp',
            'webp': 'webp',
        }
        
        return format_map.get(ext, 'jpg')


class ImageUtils:
    """
    Utility functions for image processing
    """
    
    def calculate_hash(self, image_bytes: bytes) -> str:
        """
        Calculate perceptual hash for image
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Perceptual hash string
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to grayscale
                img = img.convert('L')
                
                # Calculate perceptual hash
                phash = imagehash.phash(img, hash_size=16)
                
                return str(phash)
                
        except Exception as e:
            # Fallback to content hash
            return hashlib.md5(image_bytes).hexdigest()
    
    def assess_quality(self, image_path: str) -> Dict[str, Any]:
        """
        Assess image quality for business use
        
        Args:
            image_path: Path to image file
            
        Returns:
            Quality assessment dictionary
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                pixels = width * height
                
                quality = {
                    'resolution': 'unknown',
                    'score': 0.5,
                    'width': width,
                    'height': height
                }
                
                # Resolution scoring
                if pixels >= 1920 * 1080:  # Full HD
                    quality['resolution'] = 'high'
                    quality['score'] = 1.0
                elif pixels >= 1280 * 720:  # HD
                    quality['resolution'] = 'medium'
                    quality['score'] = 0.7
                elif pixels >= 640 * 480:  # VGA
                    quality['resolution'] = 'low'
                    quality['score'] = 0.5
                else:
                    quality['resolution'] = 'very_low'
                    quality['score'] = 0.3
                
                # Aspect ratio check
                ratio = width / height if height > 0 else 1.0
                standard_ratios = [16/9, 4/3, 1.0, 3/2]
                closest = min(standard_ratios, key=lambda x: abs(x - ratio))
                
                if abs(closest - ratio) < 0.1:
                    quality['standard_aspect_ratio'] = True
                    quality['score'] = min(quality['score'] + 0.1, 1.0)
                else:
                    quality['standard_aspect_ratio'] = False
                
                return quality
                
        except Exception as e:
            return {
                'resolution': 'unknown',
                'score': 0.0,
                'error': str(e)
            }
