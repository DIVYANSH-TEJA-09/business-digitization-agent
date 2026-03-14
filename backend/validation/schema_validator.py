"""
Module: schema_validator.py
Purpose: Validation Agent — validates business profiles for completeness and quality.

Checks field population, data format validity, and calculates
completeness scores across different profile sections.
"""

from typing import List, Optional

from backend.models.schemas import (
    BusinessProfile,
    BusinessType,
    FieldScore,
    ValidationError,
    ValidationResult,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaValidator:
    """
    Validates business profiles for data quality and completeness.

    Checks:
        - Required field population
        - Data format validity (email, phone, URLs)
        - Cross-field consistency
        - Completeness scoring by category
    """

    def validate(self, profile: BusinessProfile) -> ValidationResult:
        """
        Validate a business profile.

        Args:
            profile: BusinessProfile to validate

        Returns:
            ValidationResult with errors, warnings, and scores
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Validate business info
        self._validate_business_info(profile, errors, warnings)

        # Validate products
        if profile.products:
            self._validate_products(profile.products, errors, warnings)

        # Validate services
        if profile.services:
            self._validate_services(profile.services, errors, warnings)

        # Cross-field validation
        self._validate_cross_fields(profile, errors, warnings)

        # Calculate completeness scores
        field_scores = self._calculate_field_scores(profile)
        completeness = self._overall_completeness(field_scores)

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            completeness_score=completeness,
            field_scores=field_scores,
        )

        logger.info(
            f"Validation complete: "
            f"{len(errors)} errors, {len(warnings)} warnings, "
            f"completeness: {completeness:.0%}"
        )

        return result

    def _validate_business_info(
        self,
        profile: BusinessProfile,
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> None:
        """Validate core business information."""
        info = profile.business_info

        if not info.name:
            warnings.append(ValidationError(
                field="business_info.name",
                error_type="missing",
                message="Business name not found in documents",
                severity="warning",
            ))

        if not info.description:
            warnings.append(ValidationError(
                field="business_info.description",
                error_type="missing",
                message="Business description not extracted",
                severity="warning",
            ))

        # Validate email format
        if info.contact and info.contact.email:
            if "@" not in info.contact.email:
                errors.append(ValidationError(
                    field="business_info.contact.email",
                    error_type="format",
                    message=f"Invalid email: {info.contact.email}",
                    severity="error",
                ))

        # Validate website format
        if info.contact and info.contact.website:
            website = info.contact.website
            if not website.startswith(("http://", "https://", "www.")):
                warnings.append(ValidationError(
                    field="business_info.contact.website",
                    error_type="format",
                    message=f"Website may be invalid: {website}",
                    severity="warning",
                ))

    def _validate_products(
        self,
        products: list,
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> None:
        """Validate product entries."""
        for i, product in enumerate(products):
            if not product.name:
                warnings.append(ValidationError(
                    field=f"products[{i}].name",
                    error_type="missing",
                    message=f"Product {i+1} has no name",
                    severity="warning",
                ))

            if product.pricing:
                if (
                    product.pricing.discount_price is not None
                    and product.pricing.base_price is not None
                    and product.pricing.discount_price > product.pricing.base_price
                ):
                    errors.append(ValidationError(
                        field=f"products[{i}].pricing",
                        error_type="logic",
                        message=f"Product {i+1} discount exceeds base price",
                        severity="error",
                    ))

    def _validate_services(
        self,
        services: list,
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> None:
        """Validate service entries."""
        for i, service in enumerate(services):
            if not service.name:
                warnings.append(ValidationError(
                    field=f"services[{i}].name",
                    error_type="missing",
                    message=f"Service {i+1} has no name",
                    severity="warning",
                ))

    def _validate_cross_fields(
        self,
        profile: BusinessProfile,
        errors: List[ValidationError],
        warnings: List[ValidationError],
    ) -> None:
        """Cross-field validation checks."""
        # Product business should have products
        if profile.business_type == BusinessType.PRODUCT and not profile.products:
            warnings.append(ValidationError(
                field="products",
                error_type="consistency",
                message="Business classified as product-type but no products found",
                severity="warning",
            ))

        # Service business should have services
        if profile.business_type == BusinessType.SERVICE and not profile.services:
            warnings.append(ValidationError(
                field="services",
                error_type="consistency",
                message="Business classified as service-type but no services found",
                severity="warning",
            ))

    def _calculate_field_scores(
        self, profile: BusinessProfile
    ) -> dict:
        """Calculate completeness scores for each field category."""
        scores = {}

        # Business Info scoring
        info = profile.business_info
        info_fields = [
            info.name, info.description, info.category,
            info.location, info.contact, info.working_hours,
        ]
        info_total = len(info_fields)
        info_populated = sum(1 for f in info_fields if f)

        scores["business_info"] = FieldScore(
            category="business_info",
            total_fields=info_total,
            populated_fields=info_populated,
            score=info_populated / info_total if info_total > 0 else 0,
        )

        # Products scoring
        if profile.products:
            prod_total = 0
            prod_populated = 0
            for p in profile.products:
                fields = [p.name, p.description, p.pricing, p.category]
                prod_total += len(fields)
                prod_populated += sum(1 for f in fields if f)

            scores["products"] = FieldScore(
                category="products",
                total_fields=prod_total,
                populated_fields=prod_populated,
                score=prod_populated / prod_total if prod_total > 0 else 0,
            )

        # Services scoring
        if profile.services:
            svc_total = 0
            svc_populated = 0
            for s in profile.services:
                fields = [s.name, s.description, s.pricing, s.category, s.details]
                svc_total += len(fields)
                svc_populated += sum(1 for f in fields if f)

            scores["services"] = FieldScore(
                category="services",
                total_fields=svc_total,
                populated_fields=svc_populated,
                score=svc_populated / svc_total if svc_total > 0 else 0,
            )

        return scores

    def _overall_completeness(self, field_scores: dict) -> float:
        """Calculate overall completeness from category scores."""
        if not field_scores:
            return 0.0

        total_fields = sum(s.total_fields for s in field_scores.values())
        populated = sum(s.populated_fields for s in field_scores.values())

        return populated / total_fields if total_fields > 0 else 0.0
