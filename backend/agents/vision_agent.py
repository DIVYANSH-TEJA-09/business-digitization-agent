"""
Vision Agent

Analyzes images using Groq Vision API (primary) or Ollama (fallback).
Generates descriptions, tags, categories, and associations for business images.
"""
import os
import io
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from PIL import Image

from backend.models.schemas import (
    VisionAnalysisInput,
    VisionAnalysisOutput,
    ImageAnalysis,
    ExtractedImage,
)
from backend.models.enums import ImageCategory
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class VisionAgentError(Exception):
    """Base exception for vision agent errors"""
    pass


class VisionProviderError(VisionAgentError):
    """Raised when vision provider fails"""
    pass


class VisionAgent:
    """
    Analyzes images using Groq Vision API (primary) or Ollama (fallback)
    
    Features:
    - Groq API integration (llama-3.2-90b-vision-preview)
    - Ollama fallback (qwen3.5:0.8b)
    - Image description generation
    - Category classification (product, service, food, etc.)
    - Tag extraction
    - Product/service detection
    - Context-aware analysis
    - Batch processing
    """
    
    def __init__(
        self,
        provider: str = "groq",  # "groq" or "ollama"
        groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct",  # Current Groq vision model
        ollama_model: str = "qwen3.5:0.8b",
        ollama_host: str = "http://localhost:11434",
        timeout: int = 60,
        max_concurrent: int = 5
    ):
        """
        Initialize Vision Agent
        
        Args:
            provider: Primary vision provider ("groq" or "ollama")
            groq_model: Groq vision model name
            ollama_model: Ollama model name
            ollama_host: Ollama server host
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent analyses
        """
        self.provider = provider
        self.groq_model = groq_model
        self.ollama_model = ollama_model
        self.ollama_host = ollama_host
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        
        # Initialize clients
        self.groq_client = None
        self.ollama_client = None
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize vision clients"""
        # Try Groq first
        if self.provider == "groq":
            try:
                from groq import Groq
                api_key = os.getenv("GROQ_API_KEY")
                
                if not api_key:
                    logger.warning("GROQ_API_KEY not set, falling back to Ollama")
                    self.provider = "ollama"
                else:
                    self.groq_client = Groq(api_key=api_key, timeout=self.timeout)
                    logger.info(f"Groq Vision Client initialized: {self.groq_model}")
                    
            except ImportError:
                logger.warning("groq package not installed, falling back to Ollama")
                self.provider = "ollama"
            except Exception as e:
                logger.warning(f"Groq initialization failed: {e}, falling back to Ollama")
                self.provider = "ollama"
        
        # Initialize Ollama if needed
        if self.provider == "ollama":
            try:
                from ollama import Client
                self.ollama_client = Client(host=self.ollama_host, timeout=self.timeout)
                logger.info(f"Ollama Vision Client initialized: {self.ollama_model}")
            except Exception as e:
                logger.error(f"Ollama initialization failed: {e}")
                raise VisionAgentError("No vision provider available")
    
    def analyze(self, input: VisionAnalysisInput) -> ImageAnalysis:
        """
        Analyze single image
        
        Args:
            input: Vision analysis input
            
        Returns:
            ImageAnalysis object
        """
        start_time = time.time()
        
        logger.info(f"Analyzing image: {input.image.image_id} (provider: {self.provider})")
        
        try:
            # Load image
            image = Image.open(input.image.file_path)
            
            # Build prompt
            prompt = self._build_prompt(input.context, input.image.extraction_method)
            
            # Call appropriate provider
            if self.provider == "groq":
                response_text = self._call_groq(image, prompt)
            else:
                response_text = self._call_ollama(image, prompt)
            
            # Parse response
            analysis_data = self._parse_response(response_text)
            
            # Create ImageAnalysis
            analysis = ImageAnalysis(
                image_id=input.image.image_id,
                description=analysis_data.get('description', ''),
                category=self._map_category(analysis_data.get('category', 'other')),
                tags=analysis_data.get('tags', []),
                is_product=analysis_data.get('is_product', False),
                is_service_related=analysis_data.get('is_service_related', False),
                suggested_associations=analysis_data.get('associations', []),
                confidence=analysis_data.get('confidence', 0.85),
                analyzed_at=datetime.now(),
                metadata={
                    'model': self.groq_model if self.provider == 'groq' else self.ollama_model,
                    'provider': self.provider,
                    'processing_time': time.time() - start_time,
                    'image_width': image.width,
                    'image_height': image.height,
                    'context_used': bool(input.context)
                }
            )
            
            logger.info(
                f"Analysis complete for {input.image.image_id}: "
                f"{analysis.category.value} ({analysis.confidence:.2f}) "
                f"in {analysis.metadata['processing_time']:.2f}s"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Vision analysis failed for {input.image.image_id}: {e}")
            
            # Return fallback analysis
            return self._create_fallback_analysis(input.image, str(e))
    
    def analyze_batch(
        self,
        images: List[ExtractedImage],
        context: str = ""
    ) -> List[ImageAnalysis]:
        """
        Analyze multiple images
        
        Args:
            images: List of images to analyze
            context: Optional context for all images
            
        Returns:
            List of ImageAnalysis objects
        """
        logger.info(f"Analyzing batch of {len(images)} images with {self.provider}")
        
        results = []
        
        for i, image in enumerate(images):
            try:
                input_data = VisionAnalysisInput(
                    image=image,
                    context=context,
                    job_id="batch_job"
                )
                
                analysis = self.analyze(input_data)
                results.append(analysis)
                
                logger.info(f"Progress: {i+1}/{len(images)}")
                
            except Exception as e:
                logger.error(f"Failed to analyze image {image.image_id}: {e}")
                # Add fallback
                results.append(self._create_fallback_analysis(image, str(e)))
        
        return results
    
    def _build_prompt(self, context: str, extraction_method: str) -> str:
        """
        Build context-aware prompt for image analysis
        
        Args:
            context: Surrounding text context
            extraction_method: How image was extracted
            
        Returns:
            Prompt string
        """
        # Base prompt
        base_prompt = """
Analyze this image for a business digitization system.

Provide your response as JSON with this exact structure:
{
    "description": "Detailed 2-3 sentence description of what's shown in the image",
    "category": "product|service|food|destination|person|document|logo|other",
    "tags": ["tag1", "tag2", "tag3", ...],
    "is_product": true|false,
    "is_service_related": true|false,
    "associations": ["suggested product/service names this could relate to"],
    "confidence": 0.0-1.0
}

Guidelines:
- Be specific and descriptive
- Focus on business-relevant details
- Identify text, logos, or brand names if visible
- Note quality indicators (professional photo, lighting, etc.)
- For food: identify cuisine type and dishes
- For products: note colors, style, packaging
- For services: note activities, experiences, locations
- Respond ONLY with valid JSON, no additional text
"""
        
        # Add context if available
        if context:
            context_snippet = context[:500]  # Limit context length
            base_prompt = f"""
Context from source document:
{context_snippet}

{base_prompt}
"""
        
        # Add extraction method hint
        if extraction_method == "embedded_pdf":
            base_prompt += "\n\nNote: This image was embedded in a business document."
        elif extraction_method == "embedded_docx":
            base_prompt += "\n\nNote: This image was embedded in a Word document."
        
        return base_prompt

    def _call_groq(self, image: Image.Image, prompt: str) -> str:
        """
        Call Groq Vision API
        
        Args:
            image: PIL Image object
            prompt: Prompt string
            
        Returns:
            Response text
        """
        try:
            # Resize image if too large (Groq limit: 4MB base64, ~2048px max dimension)
            max_dimension = 2048
            if max(image.width, image.height) > max_dimension:
                ratio = max_dimension / max(image.width, image.height)
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {image.width}x{image.height} to {new_size}")
            
            # Convert image to base64 with quality compression
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='JPEG', quality=85, optimize=True)
            img_bytes.seek(0)
            
            # Check size before encoding
            img_size_mb = len(img_bytes.getvalue()) / (1024 * 1024)
            if img_size_mb > 3.5:  # Keep under 4MB limit
                # Reduce quality further
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='JPEG', quality=75, optimize=True)
                img_bytes.seek(0)
            
            import base64
            base64_image = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
            
            # Call Groq API
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                temperature=1,
                max_tokens=1000,
                timeout=self.timeout * 1000
            )
            
            content = response.choices[0].message.content.strip()
            
            if not content:
                raise VisionProviderError("Empty response from Groq")
            
            return content
            
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise VisionProviderError(f"Groq vision analysis failed: {e}")

    def _call_ollama(self, image: Image.Image, prompt: str) -> str:
        """
        Call Ollama API with image using Qwen3.5 vision parameters
        
        Args:
            image: PIL Image object
            prompt: Prompt string
            
        Returns:
            Response text
        """
        try:
            # Convert image to bytes - Qwen3.5 works best with JPEG
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            image_data = img_bytes.getvalue()
            
            # Call Ollama with Qwen3.5 vision-optimized parameters
            # Per official docs: temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5
            response = self.ollama_client.chat(
                model=self.ollama_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_data]
                }],
                options={
                    'temperature': 0.7,
                    'top_p': 0.8,
                    'top_k': 20,
                    'presence_penalty': 1.5,
                    'num_predict': 500
                }
            )
            
            if 'message' not in response or 'content' not in response['message']:
                raise VisionAnalysisError(f"Invalid response from Ollama: {response}")
            
            content = response['message']['content'].strip()
            
            # Check if response is empty (vision not working)
            if not content:
                raise VisionAnalysisError("Empty response - vision may not be enabled in this model")
            
            return content
            
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise VisionAnalysisError(f"Ollama API call failed: {e}")
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from Ollama
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed dictionary
        """
        try:
            # Try to extract JSON from response
            # Sometimes Ollama adds text before/after JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
            else:
                json_str = response_text
            
            # Parse JSON
            data = json.loads(json_str)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            
            # Return structured fallback
            return {
                'description': response_text[:500],
                'category': 'other',
                'tags': [],
                'is_product': False,
                'is_service_related': False,
                'associations': [],
                'confidence': 0.5
            }
    
    def _map_category(self, category_str: str) -> ImageCategory:
        """
        Map category string to ImageCategory enum

        Args:
            category_str: Category string from model

        Returns:
            ImageCategory enum value
        """
        if not category_str:
            return ImageCategory.OTHER
        
        # Handle if already an ImageCategory
        if isinstance(category_str, ImageCategory):
            return category_str
        
        category_map = {
            'product': ImageCategory.PRODUCT,
            'service': ImageCategory.SERVICE,
            'food': ImageCategory.FOOD,
            'destination': ImageCategory.DESTINATION,
            'person': ImageCategory.PERSON,
            'document': ImageCategory.DOCUMENT,
            'logo': ImageCategory.LOGO,
            'other': ImageCategory.OTHER,
        }

        category_lower = category_str.lower().strip()

        return category_map.get(category_lower, ImageCategory.OTHER)
    
    def _create_fallback_analysis(
        self,
        image: ExtractedImage,
        error: str
    ) -> ImageAnalysis:
        """
        Create fallback analysis when vision fails
        
        Args:
            image: ExtractedImage object
            error: Error message
            
        Returns:
            Fallback ImageAnalysis
        """
        return ImageAnalysis(
            image_id=image.image_id,
            description=f"Vision analysis unavailable: {error}",
            category=ImageCategory.OTHER,
            tags=[],
            is_product=False,
            is_service_related=False,
            suggested_associations=[],
            confidence=0.0,
            analyzed_at=datetime.now(),
            metadata={
                'error': error,
                'fallback': True,
                'model': self.ollama_model if self.provider == 'ollama' else self.groq_model
            }
        )
    
    def check_model_availability(self) -> bool:
        """
        Check if Ollama model is available in Ollama

        Returns:
            True if available
        """
        if self.provider != 'ollama':
            return True  # Groq doesn't need this check
        
        try:
            from ollama import list

            models = list()
            model_names = [m['name'] for m in models]

            # Check for exact match or partial match
            if self.ollama_model in model_names:
                return True

            # Check for partial match
            for name in model_names:
                if self.ollama_model.split(':')[0] in name:
                    logger.info(f"Using similar model: {name}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            return False

    def pull_model_if_needed(self):
        """
        Pull Ollama model if not available
        """
        if not self.check_model_availability():
            logger.info(f"Pulling model {self.ollama_model} from Ollama...")

            try:
                from ollama import pull
                pull(self.ollama_model)
                logger.info(f"Model {self.ollama_model} pulled successfully")
            except Exception as e:
                logger.error(f"Failed to pull model: {e}")
                raise VisionAgentError(f"Cannot pull model: {e}")


class VisionAnalysisInput:
    """
    Input for vision analysis
    """
    def __init__(
        self,
        image: ExtractedImage,
        context: str = "",
        job_id: str = ""
    ):
        self.image = image
        self.context = context
        self.job_id = job_id


class VisionAnalysisOutput:
    """
    Output from vision analysis
    """
    def __init__(
        self,
        job_id: str,
        success: bool,
        analyses: List[ImageAnalysis],
        total_images: int,
        processing_time: float,
        errors: List[str]
    ):
        self.job_id = job_id
        self.success = success
        self.analyses = analyses
        self.total_images = total_images
        self.processing_time = processing_time
        self.errors = errors
