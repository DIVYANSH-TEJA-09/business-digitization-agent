"""
Module: schema_mapping.py
Purpose: Schema Mapping Agent — uses GPT-OSS-120B via Groq to extract
         structured business data from document text and tables.

The core intelligence layer. Takes parsed content and maps it to
the business profile schema using LLM reasoning.
"""

import json
from typing import Any, Dict, List, Optional

from backend.models.schemas import (
    BusinessInfo,
    BusinessProfile,
    BusinessType,
    ContactInfo,
    DataProvenance,
    ExtractionMetadata,
    FAQ,
    ImageAnalysis,
    Itinerary,
    Location,
    ParsedDocument,
    Pricing,
    Product,
    Service,
    ServiceDetails,
    Specifications,
    StructuredTable,
    TravelInfo,
    WorkingHours,
)
from backend.utils.llm_client import llm_client
from backend.utils.logger import get_logger
from backend.utils.text_utils import tables_to_markdown, truncate_text

logger = get_logger(__name__)


class SchemaMappingAgent:
    """
    Agent for mapping extracted document data to structured business schemas.

    Uses GPT-OSS-120B via Groq for:
        1. Business type classification (product/service/mixed)
        2. Business info extraction
        3. Product extraction
        4. Service extraction

    CRITICAL: Never fabricates data. Only extracts what exists in source docs.
    """

    def __init__(self):
        self.client = llm_client

    async def map_to_schema(
        self,
        parsed_docs: List[ParsedDocument],
        tables: List[StructuredTable],
        image_analyses: List[ImageAnalysis],
    ) -> BusinessProfile:
        """
        Map all extracted data to a BusinessProfile.

        Args:
            parsed_docs: All parsed documents
            tables: All extracted tables
            image_analyses: Vision analysis results for images

        Returns:
            Complete BusinessProfile
        """
        logger.info("Starting schema mapping...")

        # Build combined context
        context = self._build_context(parsed_docs, tables)

        # Step 1: Classify business type
        business_type = self._classify_business_type(context, image_analyses)
        logger.info(f"Business type: {business_type.value}")

        # Step 2: Extract business info
        business_info = self._extract_business_info(context, image_analyses)

        # Step 3: Extract products (if applicable)
        products = None
        if business_type in (BusinessType.PRODUCT, BusinessType.MIXED):
            products = self._extract_products(context, tables, image_analyses)

        # Step 4: Extract services (if applicable)
        services = None
        if business_type in (BusinessType.SERVICE, BusinessType.MIXED):
            services = self._extract_services(context, tables, image_analyses)

        # Build media list from image analyses
        media_ids = [
            img.image_id for img in image_analyses
            if img.is_product or img.is_service_related
        ]

        profile = BusinessProfile(
            business_type=business_type,
            business_info=business_info,
            products=products,
            services=services,
            extraction_metadata=ExtractionMetadata(
                source_files_count=len(parsed_docs),
                llm_calls_made=self.client.call_count,
                confidence_score=0.75,
            ),
            data_provenance=self._build_provenance(parsed_docs, tables, image_analyses),
        )

        logger.info("Schema mapping complete")
        return profile

    def _build_context(
        self,
        parsed_docs: List[ParsedDocument],
        tables: List[StructuredTable],
    ) -> str:
        """Build a combined context string from all documents and tables."""
        parts = []

        for doc in parsed_docs:
            doc_name = doc.source_file.split("/")[-1].split("\\")[-1]
            parts.append(f"=== Document: {doc_name} ===")
            parts.append(doc.full_text)

        # Add table data
        if tables:
            parts.append("\n=== Extracted Tables ===")
            for table in tables:
                parts.append(f"\nTable ({table.table_type.value}):")
                header_str = " | ".join(table.headers)
                parts.append(header_str)
                for row in table.rows[:20]:  # Limit rows
                    parts.append(" | ".join(row))

        combined = "\n\n".join(parts)
        return truncate_text(combined, max_chars=40000)

    def _classify_business_type(self, context: str, image_analyses: List[ImageAnalysis] = None) -> BusinessType:
        """Classify the business as product, service, or mixed."""
        # Also consider image analysis results
        image_hints = []
        if image_analyses:
            product_images = sum(1 for img in image_analyses if img.is_product)
            service_images = sum(1 for img in image_analyses if img.is_service_related)
            if product_images > service_images:
                image_hints.append("product")
            elif service_images > product_images:
                image_hints.append("service")

        prompt = f"""Analyze the following business documents and determine the business type.

RULES:
- "product" = business sells physical/digital products
- "service" = business provides services (tourism, consulting, etc.)
- "mixed" = business sells both products AND services
- "unknown" = cannot determine from available information

Respond with ONLY one word: product, service, mixed, or unknown

DOCUMENTS:
{context[:10000]}

Business type:"""

        response = self.client.chat_groq(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )

        response_lower = response.strip().lower()
        type_map = {
            "product": BusinessType.PRODUCT,
            "service": BusinessType.SERVICE,
            "mixed": BusinessType.MIXED,
        }
        return type_map.get(response_lower, BusinessType.UNKNOWN)

    def _extract_business_info(self, context: str, image_analyses: List[ImageAnalysis] = None) -> BusinessInfo:
        """Extract core business information."""
        # Add image analysis context if available
        image_context = ""
        if image_analyses:
            product_images = [img for img in image_analyses if img.is_product]
            service_images = [img for img in image_analyses if img.is_service_related]
            if product_images or service_images:
                image_context = "\n\nIMAGE ANALYSIS:\n"
                for img in image_analyses[:10]:  # Limit to first 10
                    image_context += f"- {img.description} (category: {img.category.value}, tags: {', '.join(img.tags)})\n"

        prompt = f"""Extract business information from the following documents.
Return a JSON object with ONLY the fields you can find. Do NOT invent or guess information.
If a field is not found in the documents, set it to null.

Required JSON format:
{{
    "name": "business name or null",
    "description": "brief business description or null",
    "category": "business category or null",
    "location": {{
        "address": "full address or null",
        "city": "city or null",
        "state": "state or null",
        "country": "country or null",
        "postal_code": "postal code or null"
    }},
    "contact": {{
        "phone": "phone number or null",
        "email": "email or null",
        "website": "website URL or null"
    }},
    "working_hours": {{
        "monday": "hours or null",
        "tuesday": "hours or null",
        "wednesday": "hours or null",
        "thursday": "hours or null",
        "friday": "hours or null",
        "saturday": "hours or null",
        "sunday": "hours or null"
    }},
    "payment_methods": ["list of accepted payment methods"],
    "tags": ["relevant business tags"]
}}

DOCUMENTS:
{context[:15000]}
{image_context}

JSON:"""

        response = self.client.chat_groq(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse business info JSON")
            return BusinessInfo()

        return BusinessInfo(
            name=data.get("name"),
            description=data.get("description"),
            category=data.get("category"),
            location=Location(**data["location"]) if data.get("location") else None,
            contact=ContactInfo(**data["contact"]) if data.get("contact") else None,
            working_hours=WorkingHours(**data["working_hours"]) if data.get("working_hours") else None,
            payment_methods=data.get("payment_methods", []),
            tags=data.get("tags", []),
        )

    def _extract_products(
        self,
        context: str,
        tables: List[StructuredTable],
        image_analyses: List[ImageAnalysis],
    ) -> List[Product]:
        """Extract product inventory from documents."""
        # Include pricing tables in context
        pricing_tables = [t for t in tables if t.table_type.value == "pricing"]
        table_context = ""
        if pricing_tables:
            for t in pricing_tables:
                table_context += f"\nPricing Table:\n"
                table_context += " | ".join(t.headers) + "\n"
                for row in t.rows:
                    table_context += " | ".join(row) + "\n"

        prompt = f"""Extract ALL products/items from the following business documents.
Return a JSON object with a "products" array. Do NOT invent products — only extract ones mentioned.

For each product, extract:
{{
    "name": "product name",
    "description": "product description or null",
    "category": "product category or null",
    "pricing": {{
        "base_price": number or null,
        "currency": "INR",
        "discount_price": number or null,
        "price_type": "per unit / per kg / etc or null"
    }},
    "specifications": {{
        "dimensions": "or null",
        "weight": "or null",
        "material": "or null",
        "color": "or null"
    }},
    "tags": ["list of tags"]
}}

DOCUMENTS:
{context[:15000]}

{table_context}

Respond with JSON: {{"products": [...]}}"""

        response = self.client.chat_groq(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            data = json.loads(cleaned_response)
            products_data = data.get("products", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse products JSON")
            return []

        products = []
        for p in products_data:
            try:
                pricing = None
                if p.get("pricing"):
                    pricing = Pricing(
                        base_price=p["pricing"].get("base_price"),
                        currency=p["pricing"].get("currency", "INR"),
                        discount_price=p["pricing"].get("discount_price"),
                        price_type=p["pricing"].get("price_type"),
                    )

                specs = None
                if p.get("specifications"):
                    specs = Specifications(**p["specifications"])

                products.append(Product(
                    name=p.get("name"),
                    description=p.get("description"),
                    category=p.get("category"),
                    pricing=pricing,
                    specifications=specs,
                    tags=p.get("tags", []),
                ))
            except Exception as e:
                logger.debug(f"Error parsing product: {e}")

        return products

    def _extract_services(
        self,
        context: str,
        tables: List[StructuredTable],
        image_analyses: List[ImageAnalysis],
    ) -> List[Service]:
        """Extract service inventory from documents."""
        itinerary_tables = [t for t in tables if t.table_type.value == "itinerary"]
        table_context = ""
        if itinerary_tables:
            for t in itinerary_tables:
                table_context += f"\nItinerary Table:\n"
                table_context += " | ".join(t.headers) + "\n"
                for row in t.rows:
                    table_context += " | ".join(row) + "\n"

        prompt = f"""Extract ALL services from the following business documents.
Return a JSON object with a "services" array. Do NOT invent services.

For each service, extract:
{{
    "name": "service name",
    "description": "service description or null",
    "category": "category or null",
    "pricing": {{
        "base_price": number or null,
        "currency": "INR",
        "price_type": "per person / per group / etc"
    }},
    "details": {{
        "duration": "duration or null",
        "group_size": "group size or null",
        "best_time": "best time to experience or null"
    }},
    "itinerary": [
        {{"day": 1, "title": "Day 1 Title", "activities": ["activity1", "activity2"]}}
    ],
    "inclusions": ["what's included"],
    "exclusions": ["what's not included"],
    "faqs": [{{"question": "...", "answer": "..."}}],
    "cancellation_policy": "policy text or null",
    "tags": ["list of tags"]
}}

DOCUMENTS:
{context[:15000]}

{table_context}

Respond with JSON: {{"services": [...]}}"""

        response = self.client.chat_groq(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            data = json.loads(cleaned_response)
            services_data = data.get("services", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse services JSON")
            return []

        services = []
        for s in services_data:
            try:
                pricing = None
                if s.get("pricing"):
                    pricing = Pricing(
                        base_price=s["pricing"].get("base_price"),
                        currency=s["pricing"].get("currency", "INR"),
                        price_type=s["pricing"].get("price_type"),
                    )

                details = None
                if s.get("details"):
                    details = ServiceDetails(**s["details"])

                itinerary = []
                for it in s.get("itinerary", []):
                    try:
                        itinerary.append(Itinerary(**it))
                    except Exception:
                        pass

                faqs = []
                for faq in s.get("faqs", []):
                    try:
                        faqs.append(FAQ(**faq))
                    except Exception:
                        pass

                services.append(Service(
                    name=s.get("name"),
                    description=s.get("description"),
                    category=s.get("category"),
                    pricing=pricing,
                    details=details,
                    itinerary=itinerary,
                    faqs=faqs,
                    inclusions=s.get("inclusions", []),
                    exclusions=s.get("exclusions", []),
                    cancellation_policy=s.get("cancellation_policy"),
                    tags=s.get("tags", []),
                ))
            except Exception as e:
                logger.debug(f"Error parsing service: {e}")

        return services

    def _build_provenance(
        self,
        parsed_docs: List[ParsedDocument],
        tables: List[StructuredTable],
        image_analyses: List[ImageAnalysis],
    ) -> List[DataProvenance]:
        """Build data provenance tracking for all extracted data."""
        provenance = []

        # Track document sources
        for doc in parsed_docs:
            provenance.append(DataProvenance(
                field_name="document_content",
                source_doc=doc.source_file,
                extraction_method="parser",
                confidence=0.9,
            ))

        # Track table sources
        for table in tables:
            provenance.append(DataProvenance(
                field_name=f"table_{table.table_type.value}",
                source_doc=table.source_doc,
                source_page=table.source_page,
                extraction_method="rule-based",
                confidence=table.confidence,
            ))

        # Track image analysis sources
        for img_analysis in image_analyses:
            provenance.append(DataProvenance(
                field_name=f"image_{img_analysis.category.value}",
                source_doc=img_analysis.image_id,
                extraction_method="vision-ai",
                confidence=img_analysis.confidence,
            ))

        return provenance
