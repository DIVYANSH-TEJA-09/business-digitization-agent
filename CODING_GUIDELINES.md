# Coding Guidelines: Agentic Business Digitization Framework

## Overview

These guidelines ensure code quality, maintainability, and consistency across the project. All contributors must follow these standards.

## General Principles

### 1. Code Quality Hierarchy
1. **Correctness** - Code must work correctly
2. **Security** - No vulnerabilities
3. **Readability** - Easy to understand
4. **Performance** - Efficient execution
5. **Maintainability** - Easy to modify

### 2. Python Zen
Follow PEP 20 (The Zen of Python):
- Explicit is better than implicit
- Simple is better than complex
- Readability counts
- Errors should never pass silently

## Python Coding Standards

### File Organization

```python
"""
Module: document_parser.py
Purpose: Parse various document formats into structured data

This module provides parsers for PDF, DOCX, and other business documents.
It follows the factory pattern for extensibility.

Author: Team Name
Created: YYYY-MM-DD
"""

# Standard library imports
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Third-party imports
import pdfplumber
from pydantic import BaseModel, Field
from anthropic import Anthropic

# Local imports
from backend.utils.logger import get_logger
from backend.models.schemas import ParsedDocument, Page

# Module constants
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
SUPPORTED_FORMATS = ['pdf', 'docx', 'doc']

# Initialize module logger
logger = get_logger(__name__)
```

### Naming Conventions

```python
# Classes: PascalCase
class DocumentParser:
    pass

class PDFParser:
    pass

# Functions and methods: snake_case
def parse_document(file_path: str) -> ParsedDocument:
    pass

def extract_text_from_page(page: Page) -> str:
    pass

# Constants: UPPER_CASE
MAX_PAGES = 1000
DEFAULT_ENCODING = 'utf-8'

# Private methods/variables: _leading_underscore
def _internal_helper():
    pass

_cache = {}

# Module-level variables: snake_case
default_config = {}
```

### Type Hints

**Always use type hints** for function parameters and return values:

```python
# Good
def process_file(
    file_path: str,
    max_size: int = 1000,
    encoding: str = 'utf-8'
) -> ParsedDocument:
    """
    Process a file and return parsed document.
    
    Args:
        file_path: Path to the file to process
        max_size: Maximum file size in KB
        encoding: File encoding to use
        
    Returns:
        ParsedDocument object containing extracted data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is too large
    """
    pass

# Complex types
from typing import List, Dict, Optional, Union, Tuple

def get_documents(
    ids: List[str],
    include_metadata: bool = True
) -> Dict[str, Optional[ParsedDocument]]:
    pass

# Type aliases for clarity
PageList = List[Page]
DocumentMap = Dict[str, ParsedDocument]

def batch_process(docs: PageList) -> DocumentMap:
    pass
```

### Error Handling

```python
class DocumentParsingError(Exception):
    """Base exception for document parsing errors"""
    pass

class UnsupportedFormatError(DocumentParsingError):
    """Raised when document format is not supported"""
    pass

class CorruptedFileError(DocumentParsingError):
    """Raised when file is corrupted or unreadable"""
    pass

# Good error handling pattern
def parse_pdf(file_path: str) -> ParsedDocument:
    """
    Parse PDF file with comprehensive error handling.
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.endswith('.pdf'):
            raise UnsupportedFormatError(
                f"Expected PDF file, got: {file_path}"
            )
        
        with pdfplumber.open(file_path) as pdf:
            return self._extract_content(pdf)
            
    except pdfplumber.PDFSyntaxError as e:
        logger.error(f"Corrupted PDF: {file_path}")
        raise CorruptedFileError(f"Cannot parse corrupted PDF: {e}") from e
        
    except Exception as e:
        logger.exception(f"Unexpected error parsing {file_path}")
        raise DocumentParsingError(f"Failed to parse PDF: {e}") from e
    
    finally:
        # Cleanup if needed
        pass

# Never use bare except
# Bad
try:
    risky_operation()
except:  # Don't do this!
    pass

# Good
try:
    risky_operation()
except SpecificException as e:
    handle_specific_error(e)
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Logging

```python
import logging
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class DocumentProcessor:
    def process(self, file_path: str) -> ParsedDocument:
        logger.info(f"Starting document processing: {file_path}")
        
        try:
            result = self._do_processing(file_path)
            logger.info(
                f"Successfully processed {file_path}: "
                f"{result.total_pages} pages"
            )
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to process {file_path}: {e}",
                extra={'file_path': file_path, 'error_type': type(e).__name__}
            )
            raise

# Logging levels
logger.debug("Detailed debug information")
logger.info("General informational messages")
logger.warning("Warning messages for recoverable issues")
logger.error("Error messages for failures")
logger.critical("Critical errors requiring immediate attention")

# Use structured logging
logger.info(
    "Document processed",
    extra={
        'file_path': file_path,
        'pages': page_count,
        'processing_time': elapsed_time,
        'job_id': job_id
    }
)
```

### Async/Await Patterns

```python
import asyncio
from typing import List

# Async function definition
async def process_document(file_path: str) -> ParsedDocument:
    """
    Asynchronously process document.
    """
    logger.info(f"Processing {file_path}")
    
    # Await async operations
    content = await self._read_file_async(file_path)
    parsed = await self._parse_async(content)
    
    return parsed

# Parallel processing with gather
async def process_multiple(file_paths: List[str]) -> List[ParsedDocument]:
    """
    Process multiple documents in parallel.
    """
    tasks = [process_document(path) for path in file_paths]
    
    # Use gather for parallel execution
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    parsed_docs = []
    for file_path, result in zip(file_paths, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to process {file_path}: {result}")
        else:
            parsed_docs.append(result)
    
    return parsed_docs

# Async context managers
async def process_with_context():
    async with AsyncFileHandler(file_path) as handler:
        data = await handler.read()
        return await handler.process(data)
```

### Pydantic Models

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class BusinessInfo(BaseModel):
    """
    Business profile information.
    
    All fields are optional as they may not be present in source documents.
    """
    name: Optional[str] = Field(None, description="Business name")
    description: Optional[str] = Field(
        None, 
        description="Business description",
        max_length=5000
    )
    contact_email: Optional[str] = Field(None, description="Contact email")
    
    @validator('contact_email')
    def validate_email(cls, v):
        """Validate email format."""
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v
    
    @validator('description')
    def clean_description(cls, v):
        """Clean and normalize description."""
        if v:
            # Remove excessive whitespace
            v = ' '.join(v.split())
        return v
    
    class Config:
        # Enable validation on assignment
        validate_assignment = True
        
        # JSON schema extras
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "description": "Leading provider of...",
                "contact_email": "info@acme.com"
            }
        }
```

### Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.parsers.pdf_parser import PDFParser
from backend.models.schemas import ParsedDocument

# Test fixtures
@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF for testing."""
    pdf_path = tmp_path / "sample.pdf"
    # Create sample PDF content
    create_sample_pdf(pdf_path)
    return str(pdf_path)

@pytest.fixture
def pdf_parser():
    """Create PDFParser instance."""
    return PDFParser()

# Test cases
class TestPDFParser:
    """Test suite for PDFParser."""
    
    def test_parse_valid_pdf(self, pdf_parser, sample_pdf_path):
        """Test parsing a valid PDF file."""
        result = pdf_parser.parse(sample_pdf_path)
        
        assert isinstance(result, ParsedDocument)
        assert result.total_pages > 0
        assert result.file_type == "pdf"
    
    def test_parse_nonexistent_file(self, pdf_parser):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            pdf_parser.parse("nonexistent.pdf")
    
    def test_parse_corrupted_pdf(self, pdf_parser, tmp_path):
        """Test handling of corrupted PDF."""
        corrupted_path = tmp_path / "corrupted.pdf"
        corrupted_path.write_text("not a pdf")
        
        with pytest.raises(CorruptedFileError):
            pdf_parser.parse(str(corrupted_path))
    
    @patch('pdfplumber.open')
    def test_parse_with_mock(self, mock_pdfplumber, pdf_parser):
        """Test parsing with mocked pdfplumber."""
        # Setup mock
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock(extract_text=lambda: "Sample text")]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        # Execute
        result = pdf_parser.parse("dummy.pdf")
        
        # Verify
        assert result.total_pages == 1
        mock_pdfplumber.assert_called_once_with("dummy.pdf")

# Async tests
@pytest.mark.asyncio
async def test_async_processing():
    """Test async document processing."""
    processor = AsyncDocumentProcessor()
    result = await processor.process("test.pdf")
    assert result is not None

# Parametrized tests
@pytest.mark.parametrize("file_ext,expected_type", [
    ("pdf", "pdf"),
    ("docx", "docx"),
    ("doc", "doc"),
])
def test_file_type_detection(file_ext, expected_type):
    """Test file type detection for various extensions."""
    classifier = FileClassifier()
    file_type = classifier.detect_type(f"sample.{file_ext}")
    assert file_type == expected_type
```

### Documentation

```python
def extract_business_info(
    page_index: PageIndex,
    field_names: List[str],
    confidence_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Extract business information fields using RAG.
    
    This function uses the page index to retrieve relevant context
    and then employs an LLM to extract specific fields.
    
    Args:
        page_index: Pre-built inverted index of document pages
        field_names: List of field names to extract (e.g., ['name', 'location'])
        confidence_threshold: Minimum confidence score for extraction (0.0-1.0)
        
    Returns:
        Dictionary mapping field names to extracted values. Fields not found
        or with confidence below threshold are excluded.
        
    Raises:
        ValueError: If page_index is empty or field_names is invalid
        LLMError: If LLM API call fails
        
    Example:
        >>> index = build_page_index(documents)
        >>> info = extract_business_info(
        ...     index,
        ...     ['name', 'location', 'hours'],
        ...     confidence_threshold=0.8
        ... )
        >>> print(info['name'])
        'Acme Corporation'
    
    Note:
        This function makes external API calls to Claude and may take
        several seconds to complete. Consider using async version for
        batch processing.
    
    See Also:
        - extract_business_info_async: Async version of this function
        - build_page_index: Creates the required page index
    """
    if not page_index.documents:
        raise ValueError("page_index is empty")
    
    if not field_names:
        raise ValueError("field_names cannot be empty")
    
    # Implementation...
```

## React/TypeScript Standards

### Component Structure

```typescript
// Good component structure
import React, { useState, useEffect } from 'react';
import { BusinessProfile } from '@/types/profile';
import { Button } from '@/components/ui/button';
import { useProfile } from '@/hooks/useProfile';

interface ProfileViewerProps {
  profileId: string;
  onEdit?: (profile: BusinessProfile) => void;
  className?: string;
}

/**
 * ProfileViewer displays a business profile with conditional rendering
 * based on business type (product, service, or mixed).
 * 
 * @param profileId - Unique identifier for the profile to display
 * @param onEdit - Optional callback when edit button is clicked
 * @param className - Optional CSS classes for styling
 */
export const ProfileViewer: React.FC<ProfileViewerProps> = ({
  profileId,
  onEdit,
  className = ''
}) => {
  const { profile, loading, error } = useProfile(profileId);
  const [isEditing, setIsEditing] = useState(false);
  
  useEffect(() => {
    // Effect logic with cleanup
    return () => {
      // Cleanup
    };
  }, [profileId]);
  
  if (loading) {
    return <LoadingSpinner />;
  }
  
  if (error) {
    return <ErrorDisplay message={error.message} />;
  }
  
  if (!profile) {
    return <NotFound />;
  }
  
  return (
    <div className={`profile-viewer ${className}`}>
      <BusinessInfo info={profile.businessInfo} />
      
      {profile.products && (
        <ProductInventory products={profile.products} />
      )}
      
      {profile.services && (
        <ServiceInventory services={profile.services} />
      )}
    </div>
  );
};

// Export component as default
export default ProfileViewer;
```

### TypeScript Types

```typescript
// types/profile.ts

/**
 * Business type classification
 */
export enum BusinessType {
  PRODUCT = 'product',
  SERVICE = 'service',
  MIXED = 'mixed',
  UNKNOWN = 'unknown'
}

/**
 * Core business information
 */
export interface BusinessInfo {
  name?: string;
  description?: string;
  location?: Location;
  contact?: ContactInfo;
  workingHours?: WorkingHours;
  paymentMethods?: string[];
  tags?: string[];
}

/**
 * Product inventory item
 */
export interface Product {
  productId: string;
  name?: string;
  description?: string;
  pricing?: Pricing;
  specifications?: Specifications;
  media?: string[];
}

/**
 * Complete business profile
 */
export interface BusinessProfile {
  profileId: string;
  businessType: BusinessType;
  businessInfo: BusinessInfo;
  products?: Product[];
  services?: Service[];
  extractionMetadata: ExtractionMetadata;
}

// Type guards
export function isProduct(item: Product | Service): item is Product {
  return 'productId' in item;
}

export function isService(item: Product | Service): item is Service {
  return 'serviceId' in item;
}
```

### Custom Hooks

```typescript
// hooks/useProfile.ts

import { useState, useEffect } from 'react';
import { BusinessProfile } from '@/types/profile';
import { api } from '@/lib/api';

interface UseProfileReturn {
  profile: BusinessProfile | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Custom hook to fetch and manage business profile data.
 * 
 * @param profileId - Profile ID to fetch
 * @returns Profile data, loading state, error, and refetch function
 */
export const useProfile = (profileId: string): UseProfileReturn => {
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await api.getProfile(profileId);
      setProfile(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchProfile();
  }, [profileId]);
  
  return {
    profile,
    loading,
    error,
    refetch: fetchProfile
  };
};
```

## Code Review Checklist

### Before Submitting PR

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Type hints added (Python)
- [ ] Types defined (TypeScript)
- [ ] Documentation updated
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] Error handling implemented
- [ ] Logging added where appropriate
- [ ] Performance considerations addressed

### Reviewer Checklist

- [ ] Code is readable and maintainable
- [ ] Logic is correct
- [ ] Edge cases handled
- [ ] Tests are comprehensive
- [ ] No security vulnerabilities
- [ ] Performance is acceptable
- [ ] Documentation is clear
- [ ] Naming is descriptive

## Git Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(parsing): add OCR fallback for scanned PDFs

Implement OCR using Tesseract as fallback when pdfplumber
fails to extract text from scanned PDFs. Includes image
preprocessing for better accuracy.

Closes #123
```

```
fix(validation): handle null values in email validation

Email validator was throwing errors on null values instead
of gracefully handling them. Updated to treat null as valid
since email is optional field.

Fixes #456
```

## Performance Guidelines

### Python Optimization

```python
# Use list comprehensions over loops
# Good
squares = [x**2 for x in range(100)]

# Bad
squares = []
for x in range(100):
    squares.append(x**2)

# Use generators for large datasets
# Good
def process_large_file(file_path):
    with open(file_path) as f:
        for line in f:
            yield process_line(line)

# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(param):
    # Expensive computation
    return result
```

### React Optimization

```typescript
// Use React.memo for expensive components
export const ExpensiveComponent = React.memo(({ data }) => {
  return <div>{/* Render logic */}</div>;
});

// Use useMemo for expensive calculations
const sortedData = useMemo(() => {
  return data.sort(compareFn);
}, [data]);

// Use useCallback for event handlers
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
```

## Security Guidelines

### Never Commit Secrets

```python
# Bad - hardcoded API key
API_KEY = "sk-ant-api03-..."

# Good - use environment variables
import os
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Good - use .env files (not committed)
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

### Input Validation

```python
# Always validate user input
def process_file_path(file_path: str) -> str:
    """
    Validate and sanitize file path to prevent path traversal.
    """
    # Prevent path traversal
    if '..' in file_path or file_path.startswith('/'):
        raise ValueError("Invalid file path")
    
    # Sanitize
    safe_path = os.path.basename(file_path)
    
    return safe_path
```

## Conclusion

These coding guidelines ensure:
- **Consistency** across the codebase
- **Quality** through standards and reviews
- **Maintainability** via clear documentation
- **Security** through best practices
- **Performance** through optimization patterns

All team members should familiarize themselves with these guidelines and refer to them during development.
