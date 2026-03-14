# Multimodal Processing: Agentic Business Digitization Framework

## Overview

Multimodal processing handles non-text content (images, videos) to extract business-relevant information. This is critical for businesses that rely heavily on visual content (restaurants, travel agencies, retail stores).

## Vision AI Strategy

### Claude Sonnet 4 Vision Capabilities

**Why Claude Vision?**
- Best-in-class image understanding
- Detailed descriptive output
- Context-aware analysis
- JSON-structured responses
- Handles multiple images in single request

### Vision Agent Architecture

```python
class VisionAgent:
    """
    Intelligent image analysis using Claude's vision
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.max_tokens = 1000
        self.model = "claude-sonnet-4-20250514"
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=50,
            max_tokens_per_minute=20000
        )
    
    async def analyze_image(
        self, 
        image: ExtractedImage,
        context: str = ""
    ) -> ImageAnalysis:
        """
        Analyze single image with optional context
        """
        # Encode image to base64
        image_data = self.encode_image(image.file_path)
        
        # Build context-aware prompt
        prompt = self.build_vision_prompt(context)
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Call Claude Vision API
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image.mime_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        # Parse structured response
        analysis = self.parse_vision_response(response.content[0].text)
        
        return ImageAnalysis(
            image_id=image.image_id,
            description=analysis['description'],
            category=ImageCategory(analysis['category']),
            tags=analysis['tags'],
            is_product=analysis['is_product'],
            is_service_related=analysis['is_service_related'],
            suggested_associations=analysis.get('associations', []),
            confidence=analysis.get('confidence', 0.8),
            analyzed_at=datetime.now(),
            metadata=analysis.get('metadata', {})
        )
```

### Vision Prompting Strategy

#### Product Image Prompt

```python
def build_product_vision_prompt(self, context: str) -> str:
    """
    Optimized prompt for product image analysis
    """
    return f"""
    Analyze this product image in detail for a business digitization system.
    
    Context from documents: {context[:300] if context else "No additional context"}
    
    Provide a JSON response with the following structure:
    {{
        "description": "Detailed 3-4 sentence description of the product shown",
        "category": "product",
        "product_name": "Best guess of product name based on image",
        "tags": ["tag1", "tag2", "tag3", ...],
        "is_product": true,
        "is_service_related": false,
        "visual_attributes": {{
            "color": "predominant color",
            "style": "modern/vintage/minimalist/etc",
            "setting": "studio/lifestyle/packshot/etc"
        }},
        "suggested_specifications": {{
            "material": "if visible",
            "size": "if determinable",
            "features": ["feature1", "feature2"]
        }},
        "associations": ["suggested product names this could match"],
        "confidence": 0.0-1.0
    }}
    
    Guidelines:
    - Be specific and descriptive
    - Focus on business-relevant details
    - Identify brand names or logos if visible
    - Note quality indicators (professional photography, lighting)
    - Suggest product category (electronics, clothing, food, etc.)
    """
```

#### Service/Destination Image Prompt

```python
def build_service_vision_prompt(self, context: str) -> str:
    """
    Optimized prompt for service/destination images
    """
    return f"""
    Analyze this image which may represent a service, destination, or experience.
    
    Context from documents: {context[:300] if context else "No additional context"}
    
    Provide a JSON response:
    {{
        "description": "Detailed 3-4 sentence description of what's shown",
        "category": "service|destination|food|experience|other",
        "location_type": "if applicable: beach/mountain/city/restaurant/hotel/etc",
        "tags": ["tag1", "tag2", ...],
        "is_product": false,
        "is_service_related": true,
        "visual_attributes": {{
            "setting": "indoor/outdoor/natural/urban",
            "time_of_day": "if determinable",
            "weather": "if visible",
            "crowd_level": "empty/moderate/crowded"
        }},
        "service_indicators": {{
            "activity_type": "dining/touring/adventure/relaxation/etc",
            "difficulty_level": "if applicable",
            "suitable_for": ["families", "couples", "solo travelers", etc]
        }},
        "associations": ["suggested service/package names"],
        "confidence": 0.0-1.0
    }}
    
    Guidelines:
    - Identify location characteristics
    - Note activities or experiences visible
    - Describe atmosphere and ambiance
    - Identify target audience indicators
    """
```

#### Food/Menu Image Prompt

```python
def build_food_vision_prompt(self, context: str) -> str:
    """
    Specialized prompt for food/menu images
    """
    return f"""
    Analyze this food or menu image.
    
    Context: {context[:300] if context else "No context"}
    
    JSON response:
    {{
        "description": "Detailed description of food/dishes shown",
        "category": "food",
        "cuisine_type": "Italian/Chinese/Indian/etc",
        "dishes_visible": [
            {{
                "name": "estimated dish name",
                "description": "brief description",
                "presentation_style": "plating style"
            }}
        ],
        "tags": ["cuisine type", "dish names", "ingredients visible"],
        "is_product": true,
        "is_service_related": true,
        "visual_attributes": {{
            "presentation_quality": "casual/fine_dining/street_food",
            "portion_size": "small/medium/large",
            "color_palette": "appetizing/vibrant/etc"
        }},
        "menu_indicators": {{
            "price_visible": true/false,
            "dish_count": number if menu,
            "menu_type": "a_la_carte/set_menu/etc"
        }},
        "confidence": 0.0-1.0
    }}
    """
```

### Batch Image Processing

```python
async def analyze_images_batch(
    self, 
    images: List[ExtractedImage],
    context: str = ""
) -> List[ImageAnalysis]:
    """
    Process multiple images efficiently
    """
    # Group images into batches of 5 for parallel processing
    batch_size = 5
    batches = [images[i:i+batch_size] for i in range(0, len(images), batch_size)]
    
    all_analyses = []
    
    for batch in batches:
        # Process batch in parallel
        tasks = [
            self.analyze_image(img, context) 
            for img in batch
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle errors gracefully
        for img, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Vision analysis failed for {img.image_id}: {result}")
                all_analyses.append(self.create_fallback_analysis(img))
            else:
                all_analyses.append(result)
    
    return all_analyses

def create_fallback_analysis(self, image: ExtractedImage) -> ImageAnalysis:
    """
    Create minimal analysis when vision AI fails
    """
    return ImageAnalysis(
        image_id=image.image_id,
        description="Image analysis unavailable",
        category=ImageCategory.OTHER,
        tags=[],
        is_product=False,
        is_service_related=False,
        suggested_associations=[],
        confidence=0.0,
        analyzed_at=datetime.now(),
        metadata={'error': 'vision_analysis_failed'}
    )
```

## Image Association Logic

### Matching Images to Products/Services

```python
class ImageAssociationEngine:
    """
    Associate images with products or services
    """
    
    def associate_images(
        self,
        images: List[ImageAnalysis],
        products: List[Product],
        services: List[Service],
        page_index: PageIndex
    ) -> dict:
        """
        Match images to inventory items
        """
        associations = {
            'product_associations': {},
            'service_associations': {},
            'unassociated': []
        }
        
        # Associate product images
        for product in products:
            matched_images = self.match_images_to_product(
                product, images, page_index
            )
            if matched_images:
                associations['product_associations'][product.product_id] = matched_images
        
        # Associate service images
        for service in services:
            matched_images = self.match_images_to_service(
                service, images, page_index
            )
            if matched_images:
                associations['service_associations'][service.service_id] = matched_images
        
        # Track unassociated images
        associated_ids = set()
        for imgs in associations['product_associations'].values():
            associated_ids.update(img.image_id for img in imgs)
        for imgs in associations['service_associations'].values():
            associated_ids.update(img.image_id for img in imgs)
        
        associations['unassociated'] = [
            img for img in images 
            if img.image_id not in associated_ids
        ]
        
        return associations
    
    def match_images_to_product(
        self,
        product: Product,
        images: List[ImageAnalysis],
        page_index: PageIndex
    ) -> List[ImageAnalysis]:
        """
        Find images that belong to this product
        """
        matched = []
        
        for image in images:
            if not image.is_product:
                continue
            
            # Strategy 1: Direct name matching
            if product.name and self.name_match(product.name, image):
                matched.append(image)
                continue
            
            # Strategy 2: Tag overlap
            if self.tag_overlap(product.tags, image.tags) > 0.5:
                matched.append(image)
                continue
            
            # Strategy 3: Context proximity
            if self.context_proximity(product, image, page_index) > 0.7:
                matched.append(image)
                continue
        
        return matched
    
    def name_match(self, product_name: str, image: ImageAnalysis) -> bool:
        """
        Check if product name appears in image analysis
        """
        product_name_lower = product_name.lower()
        
        # Check description
        if product_name_lower in image.description.lower():
            return True
        
        # Check suggested associations
        for association in image.suggested_associations:
            if product_name_lower in association.lower():
                return True
        
        return False
    
    def tag_overlap(self, tags1: List[str], tags2: List[str]) -> float:
        """
        Calculate tag similarity (Jaccard index)
        """
        if not tags1 or not tags2:
            return 0.0
        
        set1 = set(tag.lower() for tag in tags1)
        set2 = set(tag.lower() for tag in tags2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def context_proximity(
        self,
        product: Product,
        image: ImageAnalysis,
        page_index: PageIndex
    ) -> float:
        """
        Check if image and product appear in similar context
        """
        # Get pages mentioning product
        product_pages = self.find_product_pages(product, page_index)
        
        # Get page where image was found
        image_page = self.find_image_page(image, page_index)
        
        # Check if same document/page
        if image_page and image_page in product_pages:
            return 1.0
        
        return 0.0
```

## Video Processing

### Video Metadata Extraction

```python
class VideoProcessor:
    """
    Video file handling and metadata extraction
    """
    
    def process_video(self, video_path: str) -> VideoMetadata:
        """
        Extract metadata without full processing
        """
        try:
            probe = ffmpeg.probe(video_path)
            
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            return VideoMetadata(
                file_path=video_path,
                duration=float(probe['format']['duration']),
                width=int(video_stream['width']),
                height=int(video_stream['height']),
                codec=video_stream['codec_name'],
                frame_rate=self.parse_frame_rate(video_stream['r_frame_rate']),
                file_size=int(probe['format']['size']),
                format=probe['format']['format_name']
            )
        
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return self.create_fallback_metadata(video_path)
    
    def extract_thumbnail(self, video_path: str, timestamp: float = 1.0) -> str:
        """
        Extract frame as thumbnail
        """
        output_path = f"{video_path}_thumb.jpg"
        
        try:
            (
                ffmpeg
                .input(video_path, ss=timestamp)
                .filter('scale', 640, -1)
                .output(output_path, vframes=1)
                .overwrite_output()
                .run(quiet=True)
            )
            
            return output_path
        
        except Exception as e:
            logger.error(f"Thumbnail extraction failed: {e}")
            return None
```

### Video Frame Analysis (Optional)

```python
async def analyze_video_frames(
    self, 
    video_path: str,
    sample_rate: int = 30  # Extract 1 frame per 30 seconds
) -> List[ImageAnalysis]:
    """
    Analyze key frames from video
    """
    # Extract frames at intervals
    frames = self.extract_frames(video_path, sample_rate)
    
    # Analyze each frame with vision AI
    analyses = []
    for i, frame_path in enumerate(frames):
        try:
            # Create temporary ExtractedImage
            temp_image = ExtractedImage(
                image_id=f"video_frame_{i}",
                file_path=frame_path,
                width=0,
                height=0,
                file_size=os.path.getsize(frame_path),
                mime_type="image/jpeg",
                extraction_method="video_frame",
                is_embedded=True
            )
            
            # Analyze with vision agent
            analysis = await self.vision_agent.analyze_image(temp_image)
            analyses.append(analysis)
        
        except Exception as e:
            logger.warning(f"Frame analysis failed: {e}")
        
        finally:
            # Cleanup temporary frame
            if os.path.exists(frame_path):
                os.remove(frame_path)
    
    return analyses
```

## Image Quality Assessment

```python
class ImageQualityChecker:
    """
    Assess image quality for business use
    """
    
    def assess_quality(self, image_path: str) -> dict:
        """
        Check if image meets quality standards
        """
        with Image.open(image_path) as img:
            width, height = img.size
            
            quality_score = {
                'resolution': self.check_resolution(width, height),
                'aspect_ratio': self.check_aspect_ratio(width, height),
                'file_size': self.check_file_size(image_path),
                'format': self.check_format(img),
                'overall': 0.0
            }
            
            # Calculate overall score
            quality_score['overall'] = sum(quality_score.values()) / 4
            
            return quality_score
    
    def check_resolution(self, width: int, height: int) -> float:
        """
        Score based on resolution (0.0 to 1.0)
        """
        pixels = width * height
        
        if pixels >= 1920 * 1080:  # Full HD or better
            return 1.0
        elif pixels >= 1280 * 720:  # HD
            return 0.8
        elif pixels >= 640 * 480:  # VGA
            return 0.6
        else:
            return 0.4
    
    def check_aspect_ratio(self, width: int, height: int) -> float:
        """
        Check if aspect ratio is standard
        """
        ratio = width / height
        
        # Common aspect ratios: 16:9, 4:3, 1:1, 3:2
        standard_ratios = [16/9, 4/3, 1.0, 3/2]
        
        # Find closest standard ratio
        closest_diff = min(abs(ratio - sr) for sr in standard_ratios)
        
        if closest_diff < 0.1:
            return 1.0
        elif closest_diff < 0.2:
            return 0.8
        else:
            return 0.6
```

## Image Deduplication

```python
class ImageDeduplicator:
    """
    Identify and remove duplicate images
    """
    
    def deduplicate(self, images: List[ExtractedImage]) -> List[ExtractedImage]:
        """
        Remove duplicate images using perceptual hashing
        """
        seen_hashes = {}
        unique_images = []
        
        for image in images:
            # Calculate perceptual hash
            img_hash = self.calculate_perceptual_hash(image.file_path)
            
            # Check for near-duplicates
            is_duplicate = False
            for existing_hash in seen_hashes.keys():
                if self.hamming_distance(img_hash, existing_hash) < 5:
                    is_duplicate = True
                    logger.info(f"Duplicate image found: {image.image_id}")
                    break
            
            if not is_duplicate:
                seen_hashes[img_hash] = image
                unique_images.append(image)
        
        return unique_images
    
    def calculate_perceptual_hash(self, image_path: str, hash_size: int = 8) -> str:
        """
        Calculate perceptual hash for image comparison
        """
        with Image.open(image_path) as img:
            # Convert to grayscale
            img = img.convert('L')
            
            # Resize to hash_size x hash_size
            img = img.resize((hash_size, hash_size), Image.Resampling.LANCZOS)
            
            # Get pixel data
            pixels = list(img.getdata())
            
            # Calculate average
            avg = sum(pixels) / len(pixels)
            
            # Create hash
            bits = ''.join('1' if pixel > avg else '0' for pixel in pixels)
            
            return bits
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hashes
        """
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
```

## Token Management for Vision API

```python
class VisionTokenManager:
    """
    Manage API token usage for vision processing
    """
    
    def __init__(self):
        self.total_tokens_used = 0
        self.max_tokens_per_job = 50000  # Budget per digitization job
        
    def estimate_tokens(self, image: ExtractedImage) -> int:
        """
        Estimate token cost for image analysis
        """
        # Claude Vision: ~1000-2000 tokens per image analysis
        # Varies based on image size and complexity
        base_tokens = 1500
        
        # Adjust for image size
        size_multiplier = min(image.file_size / (500 * 1024), 1.5)
        
        return int(base_tokens * size_multiplier)
    
    def can_process(self, image: ExtractedImage) -> bool:
        """
        Check if we're within token budget
        """
        estimated = self.estimate_tokens(image)
        return self.total_tokens_used + estimated < self.max_tokens_per_job
    
    def record_usage(self, tokens_used: int):
        """
        Track actual token usage
        """
        self.total_tokens_used += tokens_used
        logger.info(f"Vision tokens used: {tokens_used} (total: {self.total_tokens_used})")
```

## Conclusion

This multimodal processing strategy provides:
- **Intelligent image analysis** using Claude's vision capabilities
- **Context-aware prompting** for accurate categorization
- **Image-to-inventory association** logic
- **Quality assessment** for business usability
- **Deduplication** to reduce redundancy
- **Token management** for cost control

The vision-powered approach enables rich metadata extraction from visual content, significantly enhancing the digitization process for visually-oriented businesses.
