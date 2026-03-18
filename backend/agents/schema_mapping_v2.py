"""
Schema Mapping Agent - REWRITTEN FOR ACTUAL EXTRACTION

This version actually reads document text and extracts real data.
"""
import os
import json
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.models.schemas import (
    SchemaMappingInput,
    SchemaMappingOutput,
    BusinessProfile,
    BusinessInfo,
    Location,
    ContactInfo,
    Pricing,
    ExtractionMetadata,
    PageIndex,
    ParsedDocument,
)
from backend.models.enums import BusinessType
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaMappingAgent:
    """Extracts ACTUAL data from documents using focused LLM prompts"""
    
    def __init__(self, groq_model: str = None, timeout: int = 120):
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.timeout = timeout
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            if not api_key:
                raise ValueError(
                    f"GROQ_API_KEY not set or empty. "
                    f"Key in env: {'GROQ_API_KEY' in os.environ}, "
                    f"Length: {len(os.environ.get('GROQ_API_KEY', ''))}"
                )
            self.client = Groq(api_key=api_key, timeout=self.timeout)
            logger.info(f"Groq client initialized: {self.groq_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            raise
    
    def map_to_schema(self, input: SchemaMappingInput) -> SchemaMappingOutput:
        start_time = time.time()
        errors = []
        
        try:
            # Step 1: Classify business type
            business_type = self._classify_business_type(input.page_index)
            logger.info(f"Business type: {business_type.value}")
            
            # Step 2: Extract business info
            business_info = self._extract_business_info(input.page_index)
            logger.info(f"Business name: {business_info.name}")
            
            # Step 3: Extract services from EACH document
            services = self._extract_services_from_documents(input.page_index)
            logger.info(f"Extracted {len(services)} services")
            
            # Create profile
            profile = BusinessProfile(
                profile_id=f"profile_{input.job_id}",
                business_type=business_type,
                business_info=business_info,
                services=services if services else None,
                extraction_metadata=ExtractionMetadata(
                    extraction_date=datetime.now(),
                    processing_time=time.time() - start_time,
                    source_files_count=input.page_index.metadata.get('total_documents', 0),
                    llm_calls_made=len(input.page_index.documents) + 2,
                    confidence_score=0.8,
                    extraction_method="groq_llm",
                    version="2.0"
                )
            )
            
            return SchemaMappingOutput(
                job_id=input.job_id,
                success=True,
                profile=profile,
                processing_time=time.time() - start_time,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Schema mapping failed: {e}")
            errors.append(str(e))
            return SchemaMappingOutput(
                job_id=input.job_id,
                success=False,
                profile=None,
                processing_time=time.time() - start_time,
                errors=errors
            )
    
    def _get_full_document_text(self, doc: ParsedDocument) -> str:
        """Get complete text from all pages of a document"""
        texts = []
        for page in doc.pages:
            if page.text and page.text.strip():
                texts.append(f"[Page {page.number}]\n{page.text}")
        return "\n\n".join(texts)
    
    def _classify_business_type(self, page_index: PageIndex) -> BusinessType:
        """Simple keyword-based classification"""
        text_sample = ""
        for doc in list(page_index.documents.values())[:2]:
            text_sample += self._get_full_document_text(doc)[:1000]
        
        text_lower = text_sample.lower()
        
        if any(word in text_lower for word in ['trek', 'hike', 'expedition', 'adventure']):
            return BusinessType.SERVICE
        elif any(word in text_lower for word in ['product', 'item', 'buy', 'sell']):
            return BusinessType.PRODUCT
        else:
            return BusinessType.SERVICE
    
    def _extract_business_info(self, page_index: PageIndex) -> BusinessInfo:
        """Extract business info from all documents"""
        # Combine text from first 3 documents
        combined_text = ""
        for doc in list(page_index.documents.values())[:3]:
            combined_text += self._get_full_document_text(doc)[:2000]
        
        prompt = f"""Extract company information from this text:

{combined_text[:4000]}

Return JSON:
{{"name": "company name", "description": "2 sentence description", "category": "type of business", "email": "email if found", "phone": "phone if found", "website": "website if found"}}

Return ONLY JSON."""

        try:
            response = self._call_groq(prompt, max_tokens=500)
            data = self._parse_json(response)
            
            return BusinessInfo(
                name=data.get('name'),
                description=data.get('description'),
                category=data.get('category'),
                contact=ContactInfo(
                    email=data.get('email'),
                    phone=data.get('phone'),
                    website=data.get('website')
                )
            )
        except Exception as e:
            logger.warning(f"Business info extraction failed: {e}")
            return BusinessInfo()
    
    def _extract_services_from_documents(self, page_index: PageIndex) -> List[dict]:
        """Extract services by processing EACH document separately"""
        services = []
        
        for doc_id, doc in page_index.documents.items():
            doc_name = os.path.basename(doc.source_file)
            
            # Skip non-PDF/DOCX
            if not doc_name.endswith(('.pdf', '.docx')):
                continue
            
            # Get full text
            full_text = self._get_full_document_text(doc)
            
            if len(full_text.strip()) < 100:
                logger.warning(f"Skipping {doc_name}: too little text")
                continue
            
            logger.info(f"Extracting from: {doc_name}")
            
            # Extract service data
            service_data = self._extract_service_from_text(full_text, doc_name)
            
            if service_data and service_data.get('name'):
                services.append(service_data)
        
        return services
    
    def _extract_service_from_text(self, text: str, doc_name: str) -> Optional[dict]:
        """Extract service/product data - OPTIMIZED FOR SPEED (2 API calls)"""
        
        # Stage 1: Extract EVERYTHING in one call
        combined_prompt = f"""Analyze this business document and extract all information as JSON:

{text[:7000]}

Return JSON:
{{
  "name": "product/service name",
  "description": "2-3 sentence description",
  "category": "type of business",
  "price": number or null,
  "currency": "INR",
  "details": {{"key": "value"}} for any structured data,
  "inclusions": ["what's included"],
  "exclusions": ["what's not included"],
  "policies": {{"cancellation": "text"}},
  "faqs": [{{"question": "Q", "answer": "A"}}]
}}

Return ONLY JSON. Use null for missing fields."""

        data = self._call_groq(combined_prompt, max_tokens=1500)
        extracted = self._parse_json(data)
        
        # Build service object
        service = {
            'service_id': f"svc_{doc_name[:20].replace(' ', '_').lower()}",
            'name': extracted.get('name') or doc_name.replace('.pdf', '').replace('.docx', ''),
            'description': extracted.get('description') or f"Business offering - {doc_name}",
            'category': extracted.get('category') or 'General',
            'pricing': {
                'base_price': extracted.get('price'),
                'currency': extracted.get('currency', 'INR'),
                'price_type': 'per unit'
            } if extracted.get('price') else None,
            'details': extracted.get('details', {}),
            'inclusions': extracted.get('inclusions', []),
            'exclusions': extracted.get('exclusions', []),
            'cancellation_policy': extracted.get('policies', {}).get('cancellation'),
            'faqs': extracted.get('faqs', []),
            'tags': [extracted.get('category', 'business').lower()]
        }
        
        # Remove empty pricing
        if not service['pricing']:
            del service['pricing']
        
        return service
    
    def _call_groq(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Groq API with timeout"""
        try:
            response = self.client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=30000  # 30 second timeout per call
            )
            content = response.choices[0].message.content
            return content if content else ""
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return "{}"  # Return empty JSON on error
    
    def _parse_json(self, text: str) -> dict:
        """Parse JSON from response, handling markdown code blocks"""
        if not text:
            return {}
        
        # Remove markdown code blocks
        if '```' in text:
            text = text.split('```')[1].split('```')[0]
            if text.startswith('json'):
                text = text[4:]
        
        try:
            return json.loads(text.strip())
        except:
            logger.warning(f"Failed to parse JSON: {text[:200]}")
            return {}
