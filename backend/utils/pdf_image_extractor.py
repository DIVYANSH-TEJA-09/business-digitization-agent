"""
Module: pdf_image_extractor.py
Purpose: Extract images from PDFs using YOLO for object detection.

Extracts images from PDF pages, detects objects using YOLO,
and generates descriptions using Qwen vision model.
Maintains page-level metadata for each extracted image.
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image as PILImage
from ultralytics import YOLO

from backend.utils.llm_client import llm_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# YOLO model (nano version for speed, can be changed to 'yolov8n.pt' or others)
YOLO_MODEL = "yolov8n.pt"


class PDFImageExtractor:
    """
    Extract images from PDFs with YOLO-based object detection.

    Features:
        - Extract images from each PDF page
        - Detect objects using YOLO
        - Generate descriptions using Qwen vision
        - Maintain page-level metadata
    """

    def __init__(self):
        self._yolo_model = None
        logger.info("[PDFImageExtractor] Initializing PDF image extractor...")

    @property
    def yolo_model(self):
        """Lazy-loaded YOLO model."""
        if self._yolo_model is None:
            logger.info(f"[PDFImageExtractor] Loading YOLO model '{YOLO_MODEL}'...")
            try:
                self._yolo_model = YOLO(YOLO_MODEL)
                logger.info(f"[PDFImageExtractor] YOLO model '{YOLO_MODEL}' loaded successfully")
            except Exception as e:
                logger.error(f"[PDFImageExtractor] Failed to load YOLO model: {e}. Object detection will be skipped.")
                self._yolo_model = None
        return self._yolo_model
    
    def extract_images_from_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        job_id: str,
        run_yolo: bool = True,
        run_vision: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Extract all images from a PDF with metadata.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save extracted images
            job_id: Job identifier
            run_yolo: Whether to run YOLO object detection
            run_vision: Whether to run Qwen vision analysis

        Returns:
            List of dicts with image metadata, detections, and descriptions
        """
        import fitz  # PyMuPDF for reliable image extraction
        
        pdf_name = Path(pdf_path).stem
        extracted_images = []

        logger.info(f"[PDFImageExtractor] Starting image extraction from PDF: {pdf_name}")
        logger.info(f"[PDFImageExtractor] PDF path: {pdf_path}")
        logger.info(f"[PDFImageExtractor] Output directory: {output_dir}")
        logger.info(f"[PDFImageExtractor] YOLO enabled: {run_yolo}, Vision enabled: {run_vision}")

        try:
            # Use PyMuPDF for reliable image extraction
            with fitz.open(pdf_path) as pdf_doc:
                logger.info(f"[PDFImageExtractor] PDF opened: {len(pdf_doc)} pages")
                
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc[page_num]
                    logger.info(f"[PDFImageExtractor] Processing page {page_num + 1}/{len(pdf_doc)}")

                    # Get page images using PyMuPDF
                    image_list = page.get_images(full=True)
                    logger.info(f"[PDFImageExtractor] Found {len(image_list)} images on page {page_num + 1}")

                    for img_idx, img_info in enumerate(image_list):
                        try:
                            xref = img_info[0]
                            
                            # Extract image
                            img_data = page.extract_image(xref)
                            if not img_data:
                                logger.warning(f"[PDFImageExtractor] Could not extract image {img_idx} from page {page_num + 1}")
                                continue
                            
                            image_bytes = img_data["image"]
                            img_ext = img_data.get("ext", "png")
                            
                            # Generate unique filename
                            img_filename = f"{pdf_name}_page{page_num + 1}_img{img_idx}.{img_ext}"
                            img_path = Path(output_dir) / img_filename
                            
                            # Save image
                            with open(img_path, 'wb') as f:
                                f.write(image_bytes)
                            
                            # Get image dimensions
                            with PILImage.open(img_path) as img:
                                actual_width, actual_height = img.size
                            
                            logger.info(f"[PDFImageExtractor] Extracted image: {img_filename} ({actual_width}x{actual_height})")
                            
                            # Build image info
                            img_info_data = {
                                'image_id': f"{pdf_name}_p{page_num + 1}_img{img_idx}",
                                'file_path': str(img_path),
                                'source_pdf': pdf_name,
                                'page_number': page_num + 1,
                                'image_index': img_idx,
                                'width': actual_width,
                                'height': actual_height,
                                'file_size': img_path.stat().st_size,
                                'extraction_method': 'pymupdf',
                            }

                            # Run YOLO object detection
                            if run_yolo and self.yolo_model and img_path.exists():
                                logger.info(f"[PDFImageExtractor] Running YOLO detection on {img_filename}")
                                detections = self._run_yolo_detection(str(img_path))
                                img_info_data['yolo_detections'] = detections
                                logger.info(f"[PDFImageExtractor] YOLO detected {len(detections)} objects")

                            # Run Qwen vision analysis
                            if run_vision and img_path.exists():
                                logger.info(f"[PDFImageExtractor] Running Qwen vision analysis on {img_filename}")
                                description = self._run_vision_analysis(
                                    str(img_path),
                                    pdf_name,
                                    page_num + 1
                                )
                                img_info_data['vision_description'] = description
                                logger.info(f"[PDFImageExtractor] Vision analysis complete for {img_filename}")

                            extracted_images.append(img_info_data)

                        except Exception as e:
                            logger.error(f"[PDFImageExtractor] Failed to extract image {img_idx} from page {page_num + 1}: {e}")

            logger.info(f"[PDFImageExtractor] Extraction complete: {len(extracted_images)} images from {pdf_name}")

        except Exception as e:
            logger.error(f"[PDFImageExtractor] Failed to process PDF {pdf_path}: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return extracted_images

    def _run_yolo_detection(self, image_path: str) -> List[Dict[str, Any]]:
        """Run YOLO object detection on an image."""
        if not self.yolo_model or not image_path or not Path(image_path).exists():
            logger.debug(f"[PDFImageExtractor] Skipping YOLO: model={self.yolo_model is not None}, exists={Path(image_path).exists() if image_path else False}")
            return []

        try:
            logger.debug(f"[PDFImageExtractor] Running YOLO on: {image_path}")
            results = self.yolo_model(image_path, verbose=False, conf=0.25)
            detections = []

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    logger.debug(f"[PDFImageExtractor] No boxes detected")
                    continue

                logger.debug(f"[PDFImageExtractor] Detected {len(boxes)} objects")
                for box in boxes:
                    # Get bounding box coordinates
                    xyxy = box.xyxy[0].tolist()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = self.yolo_model.names.get(class_id, 'unknown')

                    detections.append({
                        'class': class_name,
                        'class_id': class_id,
                        'confidence': round(confidence, 3),
                        'bbox': {
                            'x1': round(xyxy[0], 1),
                            'y1': round(xyxy[1], 1),
                            'x2': round(xyxy[2], 1),
                            'y2': round(xyxy[3], 1),
                        }
                    })

            logger.info(f"[PDFImageExtractor] YOLO detection complete: {len(detections)} objects detected")
            return detections

        except Exception as e:
            logger.error(f"[PDFImageExtractor] YOLO detection failed: {e}")
            return []

    def _run_vision_analysis(
        self,
        image_path: str,
        pdf_name: str,
        page_num: int,
    ) -> Dict[str, Any]:
        """Run Qwen vision analysis on an extracted image."""
        logger.info(f"[PDFImageExtractor] Starting vision analysis for {Path(image_path).name}")
        
        if not image_path or not Path(image_path).exists():
            logger.warning(f"[PDFImageExtractor] Image not found: {image_path}")
            return {
                'description': 'Image not available for analysis',
                'tags': [],
                'category': 'unknown'
            }

        try:
            # Custom prompt for PDF image analysis
            prompt = f"""Analyze this image extracted from a PDF document (Page {page_num}).
Provide a JSON response with:
1. A concise description of what's in the image
2. Relevant tags (3-5 keywords)
3. Category (choose from: product, person, document, chart, graph, table, logo, diagram, photo, illustration, other)
4. Whether this appears to be a business-related image

Respond with ONLY valid JSON:
{{
    "description": "detailed description here",
    "tags": ["tag1", "tag2", "tag3"],
    "category": "category_name",
    "is_business_related": true/false,
    "context_note": "How this image relates to the PDF document context"
}}"""

            logger.info(f"[PDFImageExtractor] Calling Qwen vision API...")
            response = llm_client.analyze_image(
                image_path=image_path,
                prompt=prompt,
                temperature=0.1,
                max_tokens=512,
            )
            logger.info(f"[PDFImageExtractor] Vision API response received")

            # Parse JSON response
            import json
            try:
                # Try to extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    data = json.loads(json_str)
                else:
                    logger.warning(f"[PDFImageExtractor] Could not parse JSON from response")
                    data = {
                        'description': response[:200],
                        'tags': ['extracted', 'pdf-image'],
                        'category': 'other',
                        'is_business_related': False
                    }

                logger.info(f"[PDFImageExtractor] Vision analysis parsed successfully")
                return result

            except json.JSONDecodeError as e:
                logger.warning(f"[PDFImageExtractor] Failed to parse vision response: {e}")
                return {
                    'description': response[:200] if response else 'Analysis failed',
                    'tags': ['extracted', 'pdf-image'],
                    'category': 'other',
                    'is_business_related': False,
                    'parse_error': True
                }

        except Exception as e:
            logger.error(f"[PDFImageExtractor] Vision analysis failed: {e}")
            return {
                'description': 'Vision analysis failed',
                'tags': ['error'],
                'category': 'unknown',
                'error': str(e)
            }


# Singleton instance
pdf_image_extractor = PDFImageExtractor()
