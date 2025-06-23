# PriorAuthAutomation

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-blue.svg)](https://ai.google.dev/)
[![LlamaParse](https://img.shields.io/badge/Parse-LlamaParse-green.svg)](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
[![Tesseract OCR](https://img.shields.io/badge/OCR-Tesseract-orange.svg)](https://github.com/tesseract-ocr/tesseract)

A comprehensive Python system for automating prior authorization document processing with AI-powered entity extraction and advanced document analysis capabilities.

## 🚀 Key Features

- **🤖 AI-Powered Entity Extraction**: Google Gemini API for intelligent medical data extraction
- **📄 Multi-Stage Processing**: OCR → Parsing → Entity Extraction → Validation
- **🔀 Hybrid Document Analysis**: LlamaParse + pdfplumber for comprehensive processing
- **🏥 Medical Intelligence**: Specialized for prior authorization workflows
- **⚙️ Production Ready**: Error handling, logging, audit trails, and monitoring
- **🎯 Configurable Extraction**: Custom rules for different document types

## Features

### Core Document Processing
- **PDF Analysis**: Detects native vs scanned documents using pypdf
- **Intelligent OCR**: Conditional OCR using Tesseract for scanned documents only
- **Advanced Parsing**: LlamaParse API integration for structured content extraction
- **Precise Extraction**: pdfplumber integration for targeted data extraction using custom rules
- **Combined Processing**: Hybrid approach combining multiple extraction methods with cross-validation

### Data Management
- **JSON Storage**: Persistent document storage with metadata tracking
- **Stage Tracking**: Multi-stage processing with individual result storage
- **Document Lifecycle**: Complete audit trail from ingestion to completion

### Prior Authorization Intelligence
- **Medical Document Analysis**: Automatic detection of PA-specific fields
- **Entity Extraction**: Patient, medication, diagnosis, and physician information
- **Field Validation**: Cross-validation between extraction methods

## Installation

```bash
# Clone and navigate to the project
cd PriorAuthAutomation

# Install Tesseract OCR (system dependency)
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables (only needed for LlamaParse)
cp .env.example .env
# Edit .env and add your LlamaParse API key
```

## Dependencies

```
# Core dependencies
pypdf==4.0.1

# OCR dependencies (Tesseract)
pytesseract==0.3.10
opencv-python==4.8.1.78
Pillow==10.1.0
PyMuPDF==1.23.8

# Document parsing
llama-parse==0.4.4

# Utilities
python-dotenv==1.0.0  # Still needed for LlamaParse API key
requests==2.31.0  # Still needed for LlamaParse API

# Development dependencies
reportlab==4.0.8
```

## Configuration

### System Requirements

**Tesseract OCR** must be installed on your system:
- **macOS**: `brew install tesseract`
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **Windows**: Download from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

### Environment Variables

```bash
# LlamaParse API (for document parsing) 
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here

# Optional settings
LLAMAPARSE_TIMEOUT=300
```

## Core Services

### 1. PDF Utilities (`pdf_utils.py`)
- `check_pdf_is_native(pdf_path)` - Detects if PDF has selectable text
- `get_pdf_page_count(pdf_path)` - Returns page count
- `get_pdf_info(pdf_path)` - Comprehensive PDF metadata

### 2. OCR Service (`ocr_service.py`)
- `perform_tesseract_ocr(pdf_path)` - OCR for scanned documents using Tesseract
- Image preprocessing for improved accuracy
- Confidence scoring and structured output
- Support for multiple languages

### 3. Document Parsing (`parsing_service.py`)
- `perform_llamaparse(file_path)` - Structured content extraction
- `analyze_prior_auth_document(content)` - Medical document analysis
- `extract_with_pdfplumber(file_path, extraction_rules)` - **NEW: Precise rule-based extraction**
- `perform_combined_parsing(file_path, extraction_rules)` - **NEW: Hybrid extraction with cross-validation**

### 4. Data Storage (`data_store.py`)
- `save_document_metadata(doc_id, metadata)` - Document lifecycle tracking
- `save_processed_data(doc_id, stage, data)` - Stage-based result storage
- `get_processed_data(doc_id, stage)` - Retrieve specific stage results

## Advanced Extraction with pdfplumber

### Extraction Rules Structure

```python
extraction_rules = {
    "bounding_boxes": {
        "patient_id": {
            "x0": 400, "y0": 700, "x1": 550, "y1": 750,  # Coordinates in points
            "page": 0  # Page number (0-indexed)
        }
    },
    "table_extraction": {
        "page": 0,
        "table_settings": {},  # pdfplumber table extraction settings
        "columns_of_interest": ["Medication", "Dosage", "Quantity"]
    },
    "regex_patterns": {
        "member_ids": {
            "pattern": r"[A-Z]{2,3}\d{6,9}",
            "flags": 0,
            "page": "all"  # Search all pages or specific page number
        }
    },
    "text_search": {
        "patient_info": {
            "search_terms": ["Patient Name", "DOB", "Member ID"],
            "context_lines": 2,  # Lines of context around matches
            "page": "all"
        }
    }
}
```

### Extraction Capabilities

1. **Bounding Box Extraction**: Extract text from specific rectangular areas
2. **Table Processing**: Intelligent table detection and column filtering
3. **Regex Pattern Matching**: Find structured data like IDs, dates, medications
4. **Contextual Text Search**: Locate information with surrounding context
5. **Cross-Validation**: Compare results between LlamaParse and pdfplumber

## Usage Examples

### Basic Usage

```python
# Test complete pipeline
python src/main.py [optional_pdf_path]

# Test individual services
python src/test_data_store.py       # Data storage
python src/test_ocr_service.py      # OCR functionality
python src/test_parsing_service.py  # LlamaParse
python src/test_pdfplumber_service.py  # pdfplumber extraction
python src/test_llm_service.py      # LLM entity extraction
```

### Advanced Processing

```python
from services.parsing_service import perform_combined_parsing

# Create custom extraction rules
extraction_rules = {
    "bounding_boxes": {
        "patient_id": {"x0": 400, "y0": 700, "x1": 550, "y1": 750, "page": 0}
    },
    "regex_patterns": {
        "medications": {
            "pattern": r"[A-Z][a-z]+\s+\d+(?:\.\d+)?\s*(?:mg|ml|g)",
            "page": "all"
        }
    }
}

# Perform combined extraction
result = perform_combined_parsing("document.pdf", extraction_rules)

# Access results
llamaparse_data = result["llamaparse_results"]
pdfplumber_data = result["pdfplumber_results"] 
cross_validation = result["combined_analysis"]["cross_validation"]
```

### LLM Entity Extraction

```python
from services.llm_service import extract_entities_with_gemini, extract_specific_entities

# Extract all medical entities from document content
document_content = "Patient Name: John Smith, DOB: 01/15/1980..."
result = extract_entities_with_gemini(document_content)

entities = result["extracted_entities"]
validation = result["validation"]
metadata = result["metadata"]

# Extract specific entities only
specific_entities = ["patient_name", "requested_drug_name", "prescriber_name"]
specific_result = extract_specific_entities(document_content, specific_entities)

# Key extracted entities
patient_name = entities.get("patient_name")
requested_drug = entities.get("requested_drug_name")
primary_diagnosis = entities.get("primary_diagnosis")
prescriber_npi = entities.get("prescriber_npi")
```

## Processing Pipeline

1. **Document Ingestion**: PDF analysis and metadata extraction
2. **OCR Decision**: Conditional OCR based on text detectability  
3. **Structured Parsing**: LlamaParse for comprehensive content extraction
4. **Precise Extraction**: pdfplumber for targeted field extraction
5. **Cross-Validation**: Compare and validate results between methods
6. **Entity Extraction**: Gemini LLM for medical entity extraction and structuring
7. **Medical Analysis**: Prior authorization specific field detection
8. **Data Persistence**: Store all results with audit trail

## Output Data Structure

### LLM Entity Extraction Results

```json
{
  "extracted_entities": {
    "patient_name": "Sarah Michelle Johnson",
    "date_of_birth": "1985-03-22",
    "member_id": "BC987654321",
    "primary_diagnosis": "Type 2 Diabetes Mellitus",
    "primary_diagnosis_code": "E11.9",
    "requested_drug_name": "Jardiance",
    "drug_strength": "25mg",
    "prescriber_name": "Dr. Michael Chen, MD",
    "prescriber_npi": "1234567890",
    "insurance_plan": "Blue Cross Blue Shield PPO Gold",
    "pharmacy_name": "CVS Pharmacy #12345",
    "allergies": ["Sulfa drugs", "Penicillin"],
    "current_medications": ["Metformin 1000mg", "Lisinopril 10mg"],
    "lab_results": "HbA1c: 8.2%, Fasting Glucose: 165 mg/dL"
  },
  "validation": {
    "validated_entities": {...},
    "validation_report": {
      "total_fields": 25,
      "populated_fields": 18,
      "empty_fields": 7,
      "confidence_score": 0.72,
      "validation_issues": []
    }
  },
  "metadata": {
    "model_used": "gemini-1.5-flash",
    "processing_time_seconds": 2.3,
    "temperature": 0.1,
    "prompt_template": "default_medical"
  }
}
```

### Extraction Results

```json
{
  "bounding_box_data": {
    "patient_id": {
      "text": "AB123456",
      "bbox": [400, 700, 550, 750],
      "page": 0,
      "confidence": 1.0
    }
  },
  "regex_data": {
    "medications": {
      "pattern": "[A-Z][a-z]+\\s+\\d+mg",
      "matches": [
        {"match": "Lisinopril 10mg", "page": 0},
        {"match": "Amlodipine 5mg", "page": 1}
      ],
      "match_count": 2
    }
  },
  "text_search_data": {
    "patient_info": {
      "contexts": [
        {
          "search_term": "Patient Name",
          "matched_line": "Patient Name: John Smith",
          "context": "... surrounding text ...",
          "page": 0,
          "line_number": 5
        }
      ]
    }
  }
}
```

## API Integration

### Mistral API (OCR)
- **Model**: pixtral-12b-2409
- **Purpose**: High-accuracy OCR for scanned medical documents
- **Cost Optimization**: Only used when native text is not available

### LlamaParse API (Parsing)
- **Output**: Structured markdown with preserved formatting
- **Features**: Table extraction, header hierarchy, metadata analysis
- **Medical Intelligence**: Prior authorization field recognition

### Google Gemini API (Entity Extraction)
- **Model**: gemini-1.5-flash (configurable)
- **Purpose**: Intelligent entity extraction from medical documents
- **Features**: Medical-specific prompt engineering, JSON validation
- **Entities**: Patient info, medications, diagnoses, prescriber details, insurance info

## Data Storage

Documents are stored in the `data/` directory:
- `{document_id}_metadata.json` - Document lifecycle and status
- `{document_id}_processed.json` - Stage-based processing results

### Processing Stages
- `pdf_analysis` - Basic PDF information and metadata
- `ocr` - OCR results (if performed)
- `parsing` - LlamaParse structured extraction
- `pdfplumber_extraction` - Precise field extraction
- `combined_parsing` - Hybrid results with cross-validation
- `llm_entity_extraction` - Gemini API entity extraction with validation
- `prior_auth_analysis` - Medical document analysis

## Testing

### Comprehensive Test Suite

```bash
# Data storage functionality
python src/test_data_store.py

# OCR service (requires MISTRAL_API_KEY)
python src/test_ocr_service.py

# Document parsing (requires LLAMAPARSE_API_KEY)  
python src/test_parsing_service.py

# Precise extraction with pdfplumber
python src/test_pdfplumber_service.py

# LLM entity extraction (requires GEMINI_API_KEY)
python src/test_llm_service.py

# Complete pipeline integration
python src/main.py
```

### Sample Output

```
🧪 Testing pdfplumber Extraction Service
✅ Extraction completed successfully!
   Processing time: 0.02 seconds
   Total pages processed: 3

🔍 Regex Pattern Results:
   member_ids: 3 matches
   medications_with_dosage: 3 matches  
   icd_codes: 2 matches
   dates: 7 matches

🔎 Text Search Results:
   patient_demographics: 4 contexts found
   medical_info: 3 contexts found
   prescription_info: 8 contexts found
```

## Architecture Benefits

### Intelligent Processing
- **Cost Optimization**: OCR only when needed
- **Accuracy**: Multiple extraction methods with validation
- **Flexibility**: Configurable extraction rules per document type

### Production Ready
- **Error Handling**: Comprehensive exception management
- **Logging**: Detailed processing logs for debugging
- **Scalability**: Modular design for easy extension
- **Audit Trail**: Complete processing history

### Medical Document Expertise
- **Prior Authorization Intelligence**: Automatic PA field detection
- **Medical Entity Recognition**: Patient, medication, diagnosis extraction
- **Healthcare Workflows**: Designed for medical document processing

## Future Enhancements

- Custom extraction rule templates for different PA forms
- Machine learning models for improved field detection
- Integration with healthcare APIs and databases
- Real-time processing capabilities
- Advanced OCR post-processing and correction

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## License

This project is designed for prior authorization automation in healthcare settings. 