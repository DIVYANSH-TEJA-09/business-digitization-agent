"""
Module: exceptions.py
Purpose: Custom exception hierarchy for the business digitization pipeline.

All exceptions inherit from a base DigitizationError to allow
both specific and catch-all error handling patterns.
"""


class DigitizationError(Exception):
    """Base exception for all digitization pipeline errors."""
    pass


class FileProcessingError(DigitizationError):
    """Errors related to file handling and processing."""
    pass


class UnsupportedFileTypeError(FileProcessingError):
    """Raised when file format is not supported."""
    def __init__(self, file_type: str, file_path: str = ""):
        self.file_type = file_type
        self.file_path = file_path
        super().__init__(
            f"Unsupported file type '{file_type}'"
            + (f" for file: {file_path}" if file_path else "")
        )


class CorruptedFileError(FileProcessingError):
    """Raised when a file is corrupted or unreadable."""
    pass


class ZipExtractionError(FileProcessingError):
    """Raised when ZIP extraction fails."""
    pass


class ZipBombError(ZipExtractionError):
    """Raised when a ZIP bomb is detected."""
    pass


class FileTooLargeError(FileProcessingError):
    """Raised when a file exceeds the size limit."""
    def __init__(self, file_size: int, max_size: int):
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(
            f"File size {file_size / (1024*1024):.1f}MB exceeds "
            f"maximum {max_size / (1024*1024):.1f}MB"
        )


class DocumentParsingError(DigitizationError):
    """Errors during document text/content extraction."""
    pass


class TableExtractionError(DigitizationError):
    """Errors during table detection and extraction."""
    pass


class MediaExtractionError(DigitizationError):
    """Errors during image/video extraction."""
    pass


class LLMError(DigitizationError):
    """Errors related to LLM API calls (Groq/Ollama)."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is hit."""
    def __init__(self, provider: str, retry_after: float = 0):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"{provider} rate limit exceeded. "
            f"Retry after {retry_after}s."
        )


class LLMConnectionError(LLMError):
    """Raised when LLM API is unreachable."""
    pass


class SchemaValidationError(DigitizationError):
    """Errors during schema validation."""
    pass


class IndexingError(DigitizationError):
    """Errors during document indexing."""
    pass
