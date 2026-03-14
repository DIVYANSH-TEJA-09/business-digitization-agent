"""
Module: vision_agent.py
Purpose: Vision Agent — analyzes images using Qwen 3.5 0.8B via Ollama.

Uses few-shot prompting strategy to maximize accuracy from the small
0.8B model. Classifies images, generates descriptions, and tags them.
"""

import json
from typing import List, Optional

from backend.models.schemas import (
    ExtractedImage,
    ImageAnalysis,
    ImageCategory,
)
from backend.utils.llm_client import llm_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Few-shot examples to boost accuracy (Qwen 3.5 0.8B benefits from examples)
VISION_PROMPT = """Analyze this image and respond in JSON format ONLY. No other text.

Examples of expected output:
- Product photo: {"description": "A red leather handbag with gold buckle", "category": "product", "tags": ["handbag", "leather", "accessories"], "is_product": true, "is_service": false}
- Restaurant interior: {"description": "A modern restaurant with wooden tables and warm lighting", "category": "food", "tags": ["restaurant", "interior", "dining"], "is_product": false, "is_service": true}
- Travel destination: {"description": "A scenic mountain valley with a river", "category": "destination", "tags": ["mountain", "nature", "travel"], "is_product": false, "is_service": true}
- Company logo: {"description": "A circular blue logo with company initials", "category": "logo", "tags": ["logo", "branding"], "is_product": false, "is_service": false}
- Document scan: {"description": "A scanned document page with text and tables", "category": "document", "tags": ["document", "text"], "is_product": false, "is_service": false}

Now analyze the provided image. Respond with ONLY the JSON object:
{"description": "...", "category": "product|service|food|destination|person|document|logo|other", "tags": ["...", "..."], "is_product": true/false, "is_service": true/false}"""


class VisionAgent:
    """
    Agent for analyzing images using Qwen 3.5 0.8B vision model.

    Uses few-shot prompting to maximize accuracy from the small model.
    Generates descriptions, categories, and tags for each image.
    """

    def __init__(self):
        self.client = llm_client

    def analyze(self, image: ExtractedImage) -> ImageAnalysis:
        """
        Analyze a single image and generate metadata.

        Args:
            image: ExtractedImage with file path

        Returns:
            ImageAnalysis with description, category, and tags
        """
        if not image.file_path or image.file_path == "":
            logger.debug(f"Skipping image with no file path: {image.image_id}")
            return self._empty_analysis(image.image_id)

        logger.debug(f"Analyzing image: {image.image_id}")

        try:
            response = self.client.analyze_image(
                image_path=image.file_path,
                prompt=VISION_PROMPT,
                temperature=0.1,
                max_tokens=512,
            )

            return self._parse_response(image.image_id, response)

        except Exception as e:
            logger.warning(
                f"Vision analysis failed for {image.image_id}: {e}"
            )
            return self._empty_analysis(image.image_id)

    def analyze_batch(
        self,
        images: List[ExtractedImage],
        max_images: int = 50,
    ) -> List[ImageAnalysis]:
        """
        Analyze multiple images.

        Processing is sequential (Ollama is local, no need for async).
        Limits to max_images to avoid excessive processing.

        Args:
            images: List of images to analyze
            max_images: Maximum number of images to process

        Returns:
            List of ImageAnalysis results
        """
        # Filter images that have valid file paths
        valid_images = [
            img for img in images
            if img.file_path and img.file_path != ""
        ]

        if len(valid_images) > max_images:
            logger.info(
                f"Limiting vision analysis to {max_images} images "
                f"(of {len(valid_images)} total)"
            )
            valid_images = valid_images[:max_images]

        results = []
        for i, image in enumerate(valid_images):
            logger.info(
                f"Analyzing image {i+1}/{len(valid_images)}: "
                f"{image.image_id}"
            )
            analysis = self.analyze(image)
            results.append(analysis)

        logger.info(f"Vision analysis complete: {len(results)} images processed")
        return results

    def _parse_response(
        self, image_id: str, response: str
    ) -> ImageAnalysis:
        """Parse the LLM JSON response into an ImageAnalysis."""
        try:
            # Try to extract JSON from response
            data = self._extract_json(response)

            if not data:
                return self._empty_analysis(image_id)

            # Map category string to enum
            category_str = data.get("category", "other").lower()
            category = self._map_category(category_str)

            return ImageAnalysis(
                image_id=image_id,
                description=data.get("description", ""),
                category=category,
                tags=data.get("tags", []),
                is_product=data.get("is_product", False),
                is_service_related=data.get("is_service", False),
                confidence=0.7,  # Base confidence for 0.8B model
                metadata={"raw_response": response[:500]},
            )

        except Exception as e:
            logger.debug(f"Failed to parse vision response: {e}")
            return self._empty_analysis(image_id)

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON object from LLM response text."""
        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the text
        import re
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _map_category(self, category_str: str) -> ImageCategory:
        """Map category string to ImageCategory enum."""
        mapping = {
            "product": ImageCategory.PRODUCT,
            "service": ImageCategory.SERVICE,
            "food": ImageCategory.FOOD,
            "destination": ImageCategory.DESTINATION,
            "person": ImageCategory.PERSON,
            "document": ImageCategory.DOCUMENT,
            "logo": ImageCategory.LOGO,
        }
        return mapping.get(category_str, ImageCategory.OTHER)

    def _empty_analysis(self, image_id: str) -> ImageAnalysis:
        """Return an empty analysis for images that can't be processed."""
        return ImageAnalysis(
            image_id=image_id,
            description="",
            category=ImageCategory.OTHER,
            confidence=0.0,
        )
