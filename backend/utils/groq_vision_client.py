"""
Groq Vision Client

Uses Groq API for fast, reliable image analysis.
Supports Llama 3.2 Vision and other vision models.
"""
import os
import io
import time
import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime
from PIL import Image

from backend.models.schemas import ImageAnalysis
from backend.models.enums import ImageCategory
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class GroqVisionClient:
    """
    Groq API client for vision analysis
    
    Models available:
    - llama-3.2-90b-vision-preview (recommended)
    - llama-3.2-11b-vision-preview
    - llaVA-1.5-34b
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.2-90b-vision-preview",
        timeout: int = 30
    ):
        """
        Initialize Groq Vision Client
        
        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Vision model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.timeout = timeout
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Groq client"""
        if not self.api_key:
            raise ValueError(
                "Groq API key not provided. "
                "Set GROQ_API_KEY environment variable or pass api_key parameter.\n"
                "Get your key at: https://console.groq.com"
            )
        
        try:
            from groq import Groq
            self.client = Groq(
                api_key=self.api_key,
                timeout=self.timeout
            )
            logger.info(f"Groq Vision Client initialized with model: {self.model}")
        except ImportError:
            logger.error("groq package not installed. Run: pip install groq")
            raise ImportError("groq package required. Run: pip install groq")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    def analyze_image(
        self,
        image_path: str,
        context: str = "",
        prompt: Optional[str] = None
    ) -> ImageAnalysis:
        """
        Analyze image using Groq Vision API
        
        Args:
            image_path: Path to image file
            context: Optional context from documents
            prompt: Custom prompt (uses default if None)
            
        Returns:
            ImageAnalysis object
        """
        start_time = time.time()
        
        # Load and encode image
        image_data = self._encode_image(image_path)
        
        # Build prompt
        if not prompt:
            prompt = self._build_prompt(context)
        
        # Call Groq API
        response = self._call_groq(image_data, prompt)
        
        # Parse response
        analysis_data = self._parse_response(response)
        
        # Create ImageAnalysis
        analysis = ImageAnalysis(
            image_id=f"groq_{os.path.basename(image_path)}",
            description=analysis_data.get('description', ''),
            category=self._map_category(analysis_data.get('category', 'other')),
            tags=analysis_data.get('tags', []),
            is_product=analysis_data.get('is_product', False),
            is_service_related=analysis_data.get('is_service_related', False),
            suggested_associations=analysis_data.get('associations', []),
            confidence=analysis_data.get('confidence', 0.85),
            analyzed_at=datetime.now(),
            metadata={
                'model': self.model,
                'provider': 'groq',
                'processing_time': time.time() - start_time,
                'context_used': bool(context)
            }
        )
        
        logger.info(
            f"Groq vision analysis complete: {analysis.category.value} "
            f"({analysis.confidence:.2f}) in {analysis.metadata['processing_time']:.2f}s"
        )
        
        return analysis
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Get MIME type
        mime_type = self._get_mime_type(image_path)
        
        # Encode to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Return data URL format
        return f"data:{mime_type};base64,{base64_image}"
    
    def _get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension"""
        ext = os.path.splitext(image_path)[1].lower()
        
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        
        return mime_map.get(ext, 'image/jpeg')
    
    def _build_prompt(self, context: str = "") -> str:
        """
        Build prompt for image analysis
        
        Args:
            context: Optional context from documents
            
        Returns:
            Prompt string
        """
        base_prompt = """
Analyze this image for a business digitization system.

Provide your response as JSON with this exact structure:
{
    "description": "Detailed 2-3 sentence description of what's shown",
    "category": "product|service|food|destination|person|document|logo|other",
    "tags": ["tag1", "tag2", "tag3"],
    "is_product": true|false,
    "is_service_related": true|false,
    "associations": ["suggested product/service names this could relate to"],
    "confidence": 0.0-1.0
}

Guidelines:
- Be specific and descriptive
- Focus on business-relevant details
- Identify text, logos, or brand names if visible
- For food: identify cuisine type and dishes
- For products: note colors, style, packaging
- Respond ONLY with valid JSON, no additional text
"""
        
        if context:
            base_prompt = f"""
Context from source document:
{context[:500]}

{base_prompt}
"""
        
        return base_prompt
    
    def _call_groq(self, image_data: str, prompt: str) -> str:
        """
        Call Groq Vision API
        
        Args:
            image_data: Base64 encoded image (data URL format)
            prompt: Prompt string
            
        Returns:
            Response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=1000,
                timeout=self.timeout * 1000  # Groq uses milliseconds
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise Exception(f"Groq vision analysis failed: {e}")
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from Groq
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed dictionary
        """
        try:
            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
            else:
                json_str = response_text
            
            data = json.loads(json_str)
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            
            # Fallback
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
        """Map category string to ImageCategory enum"""
        category_map = {
            'product': ImageCategory.PRODUCT,
            'service': ImageCategory.SERVICE,
            'food': ImageCategory.FOOD,
            'destination': ImageCategory.DESTINATION,
            'person': ImageCategory.PERSON,
            'document': ImageCategory.DOCUMENT,
            'logo': ImageCategory.LOGO,
        }
        
        return category_map.get(category_str.lower().strip(), ImageCategory.OTHER)
    
    def check_connection(self) -> bool:
        """
        Check if Groq API is accessible
        
        Returns:
            True if connection works
        """
        try:
            # Simple API call to check connection
            self.client.models.list()
            logger.info("Groq API connection successful")
            return True
        except Exception as e:
            logger.error(f"Groq API connection failed: {e}")
            return False
    
    def get_available_models(self) -> list:
        """
        Get list of available vision models
        
        Returns:
            List of model names
        """
        try:
            models = self.client.models.list()
            vision_models = [
                m.id for m in models 
                if 'vision' in m.id.lower() or 'llava' in m.id.lower()
            ]
            return vision_models
        except Exception:
            return []


# Example usage
if __name__ == "__main__":
    # Test Groq Vision
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print("Usage: python groq_vision_client.py <image_path>")
        sys.exit(1)
    
    try:
        client = GroqVisionClient()
        
        print(f"Analyzing image: {image_path}")
        print(f"Model: {client.model}")
        
        analysis = client.analyze_image(image_path)
        
        print("\n" + "="*60)
        print("Analysis Results:")
        print("="*60)
        print(f"Category: {analysis.category.value}")
        print(f"Confidence: {analysis.confidence:.0%}")
        print(f"Description: {analysis.description}")
        print(f"Tags: {', '.join(analysis.tags)}")
        print(f"Is Product: {analysis.is_product}")
        print(f"Is Service: {analysis.is_service_related}")
        print(f"Processing Time: {analysis.metadata['processing_time']:.2f}s")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
