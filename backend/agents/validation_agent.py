"""
Validation Agent

Validates business profiles for schema compliance, completeness, and data quality.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.schemas import (
    BusinessProfile,
    BusinessInfo,
    Product,
    Service,
    ValidationError as ProfileValidationError,
    ValidationInput as ValidationInputSchema,
)
from backend.models.enums import BusinessType
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class ValidationOutput(BaseModel):
    """
    Output from validation
    """
    job_id: str
    is_valid: bool
    errors: List[ProfileValidationError] = Field(default_factory=list)
    warnings: List[ProfileValidationError] = Field(default_factory=list)
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    field_scores: Dict[str, float] = Field(default_factory=dict)
    validated_profile: Optional[BusinessProfile] = None
    validated_at: datetime = Field(default_factory=datetime.now)


class ValidationAgent:
    """
    Validates business profiles
    
    Features:
    - Schema validation
    - Completeness scoring
    - Data quality checks
    - Business rule validation
    - Anomaly detection
    """
    
    def __init__(self):
        """Initialize Validation Agent"""
        self.errors = []
        self.warnings = []
    
    def validate(self, input: ValidationInputSchema) -> ValidationOutput:
        """
        Validate business profile
        
        Args:
            input: Validation input with profile
            
        Returns:
            ValidationOutput with results
        """
        start_time = datetime.now()
        self.errors = []
        self.warnings = []
        
        logger.info(f"Starting validation for job {input.job_id}")
        
        try:
            profile = input.profile
            
            if not profile:
                return ValidationOutput(
                    job_id=input.job_id,
                    is_valid=False,
                    errors=[ProfileValidationError(
                        field="profile",
                        error_type="missing",
                        message="No profile to validate",
                        severity="error"
                    )],
                    warnings=[],
                    completeness_score=0.0,
                    field_scores={},
                    validated_profile=None,
                    validated_at=datetime.now()
                )
            
            # Step 1: Validate business info
            self._validate_business_info(profile.business_info)
            
            # Step 2: Validate products (if applicable)
            if profile.business_type == BusinessType.PRODUCT or profile.business_type == BusinessType.MIXED:
                if profile.products:
                    self._validate_products(profile.products)
                else:
                    self.warnings.append(ProfileValidationError(
                        field="products",
                        error_type="missing",
                        message="Product business has no products",
                        severity="warning"
                    ))
            
            # Step 3: Validate services (if applicable)
            if profile.business_type == BusinessType.SERVICE or profile.business_type == BusinessType.MIXED:
                if profile.services:
                    self._validate_services(profile.services)
                else:
                    self.warnings.append(ProfileValidationError(
                        field="services",
                        error_type="missing",
                        message="Service business has no services",
                        severity="warning"
                    ))
            
            # Step 4: Calculate completeness score
            completeness_score = self._calculate_completeness(profile)
            field_scores = self._calculate_field_scores(profile)
            
            # Step 5: Determine validity
            is_valid = len(self.errors) == 0
            
            logger.info(
                f"Validation complete: {is_valid}, "
                f"completeness: {completeness_score:.0%}, "
                f"{len(self.errors)} errors, {len(self.warnings)} warnings"
            )
            
            return ValidationOutput(
                job_id=input.job_id,
                is_valid=is_valid,
                errors=self.errors,
                warnings=self.warnings,
                completeness_score=completeness_score,
                field_scores=field_scores,
                validated_profile=profile,
                validated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationOutput(
                job_id=input.job_id,
                is_valid=False,
                errors=[ProfileValidationError(
                    field="profile",
                    error_type="validation_error",
                    message=str(e),
                    severity="error"
                )],
                warnings=[],
                completeness_score=0.0,
                field_scores={},
                validated_profile=None,
                validated_at=datetime.now()
            )
    
    def _validate_business_info(self, business_info: BusinessInfo):
        """
        Validate business information
        
        Args:
            business_info: BusinessInfo object
        """
        if not business_info:
            self.errors.append(ProfileValidationError(
                field="business_info",
                error_type="missing",
                message="Business information is missing",
                severity="error"
            ))
            return
        
        # Check name
        if not business_info.name:
            self.warnings.append(ProfileValidationError(
                field="business_info.name",
                error_type="missing",
                message="Business name not found",
                severity="warning"
            ))
        
        # Check description
        if not business_info.description:
            self.warnings.append(ProfileValidationError(
                field="business_info.description",
                error_type="missing",
                message="Business description not found",
                severity="warning"
            ))
        elif len(business_info.description) < 20:
            self.warnings.append(ProfileValidationError(
                field="business_info.description",
                error_type="too_short",
                message="Business description is too short (< 20 chars)",
                severity="warning"
            ))
        
        # Validate contact info
        if business_info.contact:
            self._validate_contact(business_info.contact)
        
        # Validate location
        if business_info.location:
            self._validate_location(business_info.location)
        
        # Validate working hours
        if business_info.working_hours:
            self._validate_working_hours(business_info.working_hours)
    
    def _validate_contact(self, contact):
        """
        Validate contact information
        
        Args:
            contact: ContactInfo object
        """
        # Validate email
        if contact.email:
            if not self._is_valid_email(contact.email):
                self.errors.append(ProfileValidationError(
                    field="business_info.contact.email",
                    error_type="invalid_format",
                    message=f"Invalid email format: {contact.email}",
                    severity="error"
                ))
        
        # Validate phone
        if contact.phone:
            if not self._is_valid_phone(contact.phone):
                self.warnings.append(ProfileValidationError(
                    field="business_info.contact.phone",
                    error_type="invalid_format",
                    message=f"Phone number format may be invalid: {contact.phone}",
                    severity="warning"
                ))
        
        # Validate website
        if contact.website:
            if not self._is_valid_url(contact.website):
                self.warnings.append(ProfileValidationError(
                    field="business_info.contact.website",
                    error_type="invalid_format",
                    message=f"Website URL may be invalid: {contact.website}",
                    severity="warning"
                ))
    
    def _validate_location(self, location):
        """
        Validate location information
        
        Args:
            location: Location object
        """
        # Check if at least one field is present
        if not any([location.address, location.city, location.state, location.country]):
            self.warnings.append(ProfileValidationError(
                field="business_info.location",
                error_type="incomplete",
                message="Location has no address, city, state, or country",
                severity="warning"
            ))
    
    def _validate_working_hours(self, working_hours):
        """
        Validate working hours
        
        Args:
            working_hours: WorkingHours object
        """
        # Check if at least one day is present
        days = [
            working_hours.monday,
            working_hours.tuesday,
            working_hours.wednesday,
            working_hours.thursday,
            working_hours.friday,
            working_hours.saturday,
            working_hours.sunday
        ]
        
        if not any(days):
            self.warnings.append(ProfileValidationError(
                field="business_info.working_hours",
                error_type="missing",
                message="No working hours specified",
                severity="warning"
            ))
    
    def _validate_products(self, products: List[Product]):
        """
        Validate product list
        
        Args:
            products: List of Product objects
        """
        if not products:
            return
        
        for i, product in enumerate(products):
            prefix = f"products[{i}]"
            
            # Check name
            if not product.name:
                self.warnings.append(ProfileValidationError(
                    field=f"{prefix}.name",
                    error_type="missing",
                    message=f"Product {i+1} has no name",
                    severity="warning"
                ))
            
            # Validate pricing
            if product.pricing:
                self._validate_pricing(product.pricing, f"{prefix}.pricing")
    
    def _validate_services(self, services: List[Service]):
        """
        Validate service list
        
        Args:
            services: List of Service objects
        """
        if not services:
            return
        
        for i, service in enumerate(services):
            prefix = f"services[{i}]"
            
            # Check name
            if not service.name:
                self.warnings.append(ProfileValidationError(
                    field=f"{prefix}.name",
                    error_type="missing",
                    message=f"Service {i+1} has no name",
                    severity="warning"
                ))
            
            # Check description
            if not service.description:
                self.warnings.append(ProfileValidationError(
                    field=f"{prefix}.description",
                    error_type="missing",
                    message=f"Service {i+1} has no description",
                    severity="warning"
                ))
            
            # Validate pricing
            if service.pricing:
                self._validate_pricing(service.pricing, f"{prefix}.pricing")
    
    def _validate_pricing(self, pricing, prefix: str):
        """
        Validate pricing information
        
        Args:
            pricing: Pricing object
            prefix: Field prefix for error messages
        """
        # Check base price
        if pricing.base_price is not None:
            if pricing.base_price < 0:
                self.errors.append(ProfileValidationError(
                    field=f"{prefix}.base_price",
                    error_type="invalid_value",
                    message="Base price cannot be negative",
                    severity="error"
                ))
            elif pricing.base_price > 1000000:
                self.warnings.append(ProfileValidationError(
                    field=f"{prefix}.base_price",
                    error_type="suspicious_value",
                    message=f"Base price seems very high: {pricing.base_price}",
                    severity="warning"
                ))
        
        # Check discount price
        if pricing.discount_price is not None:
            if pricing.discount_price < 0:
                self.errors.append(ProfileValidationError(
                    field=f"{prefix}.discount_price",
                    error_type="invalid_value",
                    message="Discount price cannot be negative",
                    severity="error"
                ))
            elif pricing.base_price and pricing.discount_price > pricing.base_price:
                self.errors.append(ProfileValidationError(
                    field=f"{prefix}.discount_price",
                    error_type="invalid_value",
                    message="Discount price cannot be higher than base price",
                    severity="error"
                ))
    
    def _calculate_completeness(self, profile: BusinessProfile) -> float:
        """
        Calculate overall completeness score
        
        Args:
            profile: BusinessProfile object
            
        Returns:
            Completeness score (0.0-1.0)
        """
        scores = []
        
        # Business info completeness (40% weight)
        business_score = self._score_business_info(profile.business_info)
        scores.append(business_score * 0.4)
        
        # Products completeness (30% weight)
        if profile.products:
            product_score = self._score_products(profile.products)
            scores.append(product_score * 0.3)
        
        # Services completeness (30% weight)
        if profile.services:
            service_score = self._score_services(profile.services)
            scores.append(service_score * 0.3)
        
        return min(sum(scores), 1.0)
    
    def _score_business_info(self, business_info: BusinessInfo) -> float:
        """
        Score business info completeness
        
        Args:
            business_info: BusinessInfo object
            
        Returns:
            Score (0.0-1.0)
        """
        if not business_info:
            return 0.0
        
        score = 0.0
        total = 0.0
        
        # Name (important)
        total += 2.0
        if business_info.name:
            score += 2.0
        
        # Description
        total += 1.0
        if business_info.description:
            score += 1.0
        
        # Contact
        total += 1.0
        if business_info.contact:
            if business_info.contact.email:
                score += 0.5
            if business_info.contact.phone:
                score += 0.5
        
        # Location
        total += 1.0
        if business_info.location:
            if business_info.location.city:
                score += 0.5
            if business_info.location.address:
                score += 0.5
        
        return min(score / total, 1.0)
    
    def _score_products(self, products: List[Product]) -> float:
        """
        Score products completeness
        
        Args:
            products: List of Product objects
            
        Returns:
            Score (0.0-1.0)
        """
        if not products:
            return 0.0
        
        scores = []
        for product in products:
            product_score = 0.0
            
            if product.name:
                product_score += 0.3
            if product.description:
                product_score += 0.2
            if product.pricing and product.pricing.base_price:
                product_score += 0.3
            if product.specifications:
                product_score += 0.2
            
            scores.append(product_score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _score_services(self, services: List[Service]) -> float:
        """
        Score services completeness
        
        Args:
            services: List of Service objects
            
        Returns:
            Score (0.0-1.0)
        """
        if not services:
            return 0.0
        
        scores = []
        for service in services:
            service_score = 0.0
            
            if service.name:
                service_score += 0.25
            if service.description:
                service_score += 0.25
            if service.pricing and service.pricing.base_price:
                service_score += 0.25
            if service.details or service.itinerary:
                service_score += 0.25
            
            scores.append(service_score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_field_scores(self, profile: BusinessProfile) -> Dict[str, float]:
        """
        Calculate individual field scores
        
        Args:
            profile: BusinessProfile object
            
        Returns:
            Dictionary of field scores
        """
        return {
            'business_info': self._score_business_info(profile.business_info),
            'products': self._score_products(profile.products) if profile.products else 0.0,
            'services': self._score_services(profile.services) if profile.services else 0.0
        }
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email string
            
        Returns:
            True if valid
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """
        Validate phone number (basic check)
        
        Args:
            phone: Phone string
            
        Returns:
            True if likely valid
        """
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it has at least 7 digits
        digits = re.sub(r'\D', '', cleaned)
        return len(digits) >= 7
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format
        
        Args:
            url: URL string
            
        Returns:
            True if valid
        """
        pattern = r'^https?://[^\s]+$'
        return bool(re.match(pattern, url))


class ValidationInput:
    """
    Input for validation - DEPRECATED, use ValidationInputSchema from schemas
    """
    pass  # Use schema ValidationInput instead
