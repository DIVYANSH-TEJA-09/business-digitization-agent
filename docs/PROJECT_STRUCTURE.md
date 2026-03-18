# Digi-Biz Project Structure

digi-biz/
├── backend/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Pydantic settings loader
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── file_discovery.py        # Agent 1: ZIP extraction & classification
│   │   ├── document_parsing.py      # Agent 2: PDF/DOCX parsing
│   │   ├── table_extraction.py      # Agent 3: Table detection
│   │   ├── media_extraction.py      # Agent 4: Image/video extraction
│   │   ├── vision_agent.py          # Agent 5: Qwen vision analysis
│   │   ├── indexing.py              # Agent 6: Page index builder
│   │   ├── schema_mapping.py        # Agent 7: Groq schema mapping
│   │   └── validation.py            # Agent 8: Profile validation
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── excel_parser.py
│   │   └── parser_factory.py
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── index_builder.py
│   │   ├── keyword_extractor.py
│   │   └── retriever.py
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── schema_validator.py
│   │   └── completeness.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py               # Pydantic data models
│   │   └── enums.py                 # FileType, TableType, etc.
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── file_classifier.py
│   │   ├── storage_manager.py
│   │   ├── text_utils.py
│   │   ├── table_utils.py
│   │   ├── media_utils.py
│   │   ├── groq_client.py           # Groq API wrapper
│   │   └── ollama_client.py         # Ollama API wrapper
│   └── pipelines/
│       ├── __init__.py
│       └── digitization_pipeline.py # Main orchestrator
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── types/
│   └── package.json
├── storage/                         # Created at runtime
│   ├── uploads/
│   ├── extracted/
│   ├── profiles/
│   ├── index/
│   └── temp/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── agents/
│   │   ├── test_file_discovery.py
│   │   ├── test_document_parsing.py
│   │   └── ...
│   ├── parsers/
│   ├── utils/
│   └── fixtures/                    # Test data
│       ├── sample_business_1/
│       └── sample_business_2/
├── docs/
│   ├── API.md
│   └── USER_MANUAL.md
├── .env.example
├── .env                             # (gitignored - your actual config)
├── .gitignore
├── requirements.txt
├── pytest.ini
├── mypy.ini
└── README.md
