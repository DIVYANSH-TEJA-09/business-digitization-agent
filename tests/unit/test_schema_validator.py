"""
Unit tests for backend.validation.schema_validator — SchemaValidator.

Covers:
    - Empty profile validation (completeness = 0, no hard errors)
    - Fully populated profile validation (valid, high completeness)
    - Email format validation (valid / invalid)
    - Website format validation
    - Discount > base price → error
    - Product / service without name → warning
    - Cross-field consistency (product type ↔ products list)
    - Field scores structure and ranges
    - Completeness score range [0, 1]
"""

import pytest

from backend.models.schemas import (
    BusinessInfo,
    BusinessProfile,
    BusinessType,
    ContactInfo,
    FieldScore,
    Location,
    Pricing,
    Product,
    Service,
    ValidationResult,
)
from backend.validation.schema_validator import SchemaValidator


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def validator() -> SchemaValidator:
    return SchemaValidator()


# =============================================================================
# Basic validation results
# =============================================================================

class TestValidationResult:

    def test_returns_validation_result(self, validator):
        profile = BusinessProfile()
        result = validator.validate(profile)
        assert isinstance(result, ValidationResult)

    def test_empty_profile_is_invalid_or_warns(self, validator):
        """Empty profile may not be *invalid* (no hard errors), but should warn."""
        result = validator.validate(BusinessProfile())
        # No hard errors expected from an empty profile
        assert result.is_valid is True
        # But should have warnings about missing fields
        assert len(result.warnings) > 0

    def test_is_valid_when_no_errors(self, validator, business_profile):
        result = validator.validate(business_profile)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validated_at_is_set(self, validator):
        result = validator.validate(BusinessProfile())
        assert result.validated_at is not None

    def test_completeness_score_range(self, validator):
        profile = BusinessProfile()
        result = validator.validate(profile)
        assert 0.0 <= result.completeness_score <= 1.0

    def test_full_profile_has_higher_completeness(
        self, validator, business_profile, empty_profile
    ):
        full_result = validator.validate(business_profile)
        empty_result = validator.validate(empty_profile)
        assert full_result.completeness_score > empty_result.completeness_score

    def test_empty_profile_completeness_is_zero_or_low(self, validator):
        result = validator.validate(BusinessProfile())
        assert result.completeness_score == 0.0


# =============================================================================
# Business info validation
# =============================================================================

class TestBusinessInfoValidation:

    def test_missing_name_generates_warning(self, validator):
        profile = BusinessProfile(
            business_info=BusinessInfo(description="A travel company")
        )
        result = validator.validate(profile)
        field_names = [w.field for w in result.warnings]
        assert "business_info.name" in field_names

    def test_missing_description_generates_warning(self, validator):
        profile = BusinessProfile(
            business_info=BusinessInfo(name="TrekoTrip")
        )
        result = validator.validate(profile)
        field_names = [w.field for w in result.warnings]
        assert "business_info.description" in field_names

    def test_invalid_email_raises_at_schema_level(self, validator):
        """Pydantic itself rejects invalid email before SchemaValidator."""
        from pydantic import ValidationError as PydanticValidationError
        with pytest.raises(PydanticValidationError):
            ContactInfo(email="not-an-email")

    def test_schema_validator_catches_invalid_email_via_model_construct(self, validator):
        """
        Use model_construct to bypass Pydantic validation and verify that
        SchemaValidator's own email check also catches the bad value.
        """
        # Build ContactInfo without running pydantic validators
        invalid_contact = ContactInfo.model_construct(email="bad-email-no-at")
        profile = BusinessProfile(
            business_info=BusinessInfo.model_construct(
                name="Test Biz",
                contact=invalid_contact,
            )
        )
        result = validator.validate(profile)
        error_fields = [e.field for e in result.errors]
        assert "business_info.contact.email" in error_fields
        assert result.is_valid is False

    def test_valid_email_no_error(self, validator):
        profile = BusinessProfile(
            business_info=BusinessInfo(
                name="Test Biz",
                contact=ContactInfo(email="valid@example.com"),
            )
        )
        result = validator.validate(profile)
        error_fields = [e.field for e in result.errors]
        assert "business_info.contact.email" not in error_fields

    def test_invalid_website_generates_warning(self, validator):
        profile = BusinessProfile(
            business_info=BusinessInfo(
                name="Test Biz",
                contact=ContactInfo(website="trekotrip"),  # No http prefix
            )
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert "business_info.contact.website" in warn_fields

    def test_valid_website_no_warning(self, validator):
        profile = BusinessProfile(
            business_info=BusinessInfo(
                name="Test Biz",
                contact=ContactInfo(website="https://trekotrip.in"),
            )
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert "business_info.contact.website" not in warn_fields

    def test_www_website_is_valid(self, validator):
        profile = BusinessProfile(
            business_info=BusinessInfo(
                name="Test Biz",
                contact=ContactInfo(website="www.trekotrip.in"),
            )
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert "business_info.contact.website" not in warn_fields


# =============================================================================
# Product validation
# =============================================================================

class TestProductValidation:

    def test_product_without_name_generates_warning(self, validator):
        profile = BusinessProfile(
            business_type=BusinessType.PRODUCT,
            products=[Product(description="Some product", pricing=Pricing(base_price=100))],
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert any("products[0].name" in f for f in warn_fields)

    def test_discount_exceeds_base_price_generates_error(self, validator):
        """
        Note: Pydantic validates this at model construction time,
        so we test the validator's own logic with a profile that
        somehow bypasses pydantic (unlikely in production — we test
        the cross-check in _validate_products for completeness via
        a manual manipulation or just ensure validator catches it).
        """
        # Pydantic itself raises at construction:
        with pytest.raises(Exception):
            Pricing(base_price=1000.0, discount_price=1500.0)

    def test_valid_product_passes(self, validator, business_profile):
        result = validator.validate(business_profile)
        # No product-related errors
        assert all("products" not in e.field for e in result.errors)


# =============================================================================
# Service validation
# =============================================================================

class TestServiceValidation:

    def test_service_without_name_generates_warning(self, validator):
        profile = BusinessProfile(
            business_type=BusinessType.SERVICE,
            services=[Service(description="Unnamed service")],
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert any("services[0].name" in f for f in warn_fields)


# =============================================================================
# Cross-field validation
# =============================================================================

class TestCrossFieldValidation:

    def test_product_type_without_products_warns(self, validator):
        profile = BusinessProfile(
            business_type=BusinessType.PRODUCT,
            business_info=BusinessInfo(name="Shop"),
            products=None,
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert "products" in warn_fields

    def test_service_type_without_services_warns(self, validator):
        profile = BusinessProfile(
            business_type=BusinessType.SERVICE,
            business_info=BusinessInfo(name="Agency"),
            services=None,
        )
        result = validator.validate(profile)
        warn_fields = [w.field for w in result.warnings]
        assert "services" in warn_fields

    def test_unknown_type_no_cross_field_error(self, validator):
        profile = BusinessProfile(business_type=BusinessType.UNKNOWN)
        result = validator.validate(profile)
        error_fields = [e.field for e in result.errors]
        assert "products" not in error_fields
        assert "services" not in error_fields


# =============================================================================
# Field scores
# =============================================================================

class TestFieldScores:

    def test_field_scores_not_empty_for_populated_profile(
        self, validator, business_profile
    ):
        result = validator.validate(business_profile)
        assert len(result.field_scores) > 0

    def test_business_info_score_present(self, validator, business_profile):
        result = validator.validate(business_profile)
        assert "business_info" in result.field_scores

    def test_field_score_in_range(self, validator, business_profile):
        result = validator.validate(business_profile)
        for key, score in result.field_scores.items():
            assert 0.0 <= score.score <= 1.0, f"{key} score out of range"

    def test_populated_profile_business_info_score_high(
        self, validator, business_profile
    ):
        result = validator.validate(business_profile)
        score = result.field_scores["business_info"].score
        assert score > 0.5

    def test_empty_profile_completeness_is_0(self, validator):
        result = validator.validate(BusinessProfile())
        assert result.completeness_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
