# PriorAuthAutomation Setup Guide

This guide will help you set up the PriorAuthAutomation system with all its services, including the new LLM entity extraction functionality.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Internet connection for API access

## Installation Steps

### 1. Clone and Setup Environment

```bash
# Navigate to your project directory
cd PillBot/PriorAuthAutomation

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. API Keys Configuration

The system requires API keys for various services. Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit the `.env` file with your actual API keys:

```env
# Mistral API (for OCR of scanned documents)
MISTRAL_API_KEY=your_mistral_api_key_here

# LlamaParse API (for document parsing) 
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here

# Google Gemini API (for entity extraction)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Gemini Configuration
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT=60
GEMINI_MAX_RETRIES=3
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_OUTPUT_TOKENS=2048
```

### 3. Obtaining API Keys

#### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key
5. Add to your `.env` file: `GEMINI_API_KEY=your_key_here`

#### LlamaParse API Key
1. Visit [LlamaCloud](https://cloud.llamaindex.ai/)
2. Sign up for an account
3. Navigate to API Keys section
4. Generate a new API key
5. Add to your `.env` file: `LLAMAPARSE_API_KEY=your_key_here`

#### Mistral API Key (Optional)
1. Visit [Mistral AI Platform](https://console.mistral.ai/)
2. Create an account
3. Generate an API key
4. Add to your `.env` file: `MISTRAL_API_KEY=your_key_here`

## Testing the Installation

### 1. Test Individual Services

```bash
# Test data storage
python src/test_data_store.py

# Test LLM entity extraction (requires GEMINI_API_KEY)
python src/test_llm_service.py

# Test document parsing (requires LLAMAPARSE_API_KEY)
python src/test_parsing_service.py

# Test pdfplumber extraction (no API key required)
python src/test_pdfplumber_service.py

# Test OCR service (requires MISTRAL_API_KEY)
python src/test_ocr_service.py
```

### 2. Test Complete Pipeline

```bash
# Run the main pipeline
python src/main.py

# Test with a specific PDF
python src/main.py path/to/your/document.pdf
```

## Service Configuration

### LLM Service (Gemini) Configuration

The LLM service can be customized via environment variables:

```env
# Model selection
GEMINI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro for higher quality

# Response characteristics
GEMINI_TEMPERATURE=0.1  # Lower for consistency, higher for creativity
GEMINI_MAX_OUTPUT_TOKENS=2048  # Maximum response length

# Reliability settings
GEMINI_TIMEOUT=60  # Request timeout in seconds
GEMINI_MAX_RETRIES=3  # Number of retry attempts
```

### Performance Optimization

For production use, consider these settings:

```env
# For high accuracy
GEMINI_MODEL=gemini-1.5-pro
GEMINI_TEMPERATURE=0.05
GEMINI_MAX_OUTPUT_TOKENS=4096

# For fast processing
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_OUTPUT_TOKENS=2048
```

## Expected Output

### Successful Service Status

When properly configured, you should see:

```
🔧 Service Status:
--------------------
OCR: Mistral Vision OCR
  Model: pixtral-12b-2409
  API Key: ✅
Parser: LlamaParse API
  Output: markdown
  API Key: ✅
  Formats: .pdf, .docx, .doc, .txt, .md
LLM: Google Gemini API
  Model: gemini-1.5-flash
  API Key: ✅
  Output: JSON
```

### LLM Entity Extraction Results

```
🧠 Starting entity extraction with Gemini API...
✅ Entity extraction completed!
   🎯 Extracted entities: 18/25 fields
   📊 Confidence score: 0.72
   ⚡ Processing time: 2.3 seconds
   🔍 Key entities found:
      patient_name: Sarah Michelle Johnson
      requested_drug_name: Jardiance
      prescriber_name: Dr. Michael Chen, MD
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# If you see module import errors
pip install --upgrade -r requirements.txt

# Ensure you're in the correct directory
cd PillBot/PriorAuthAutomation
```

#### 2. API Key Issues
```bash
# Verify API keys are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GEMINI_API_KEY:', bool(os.getenv('GEMINI_API_KEY')))"
```

#### 3. Permission Errors
```bash
# On Unix systems, ensure proper permissions
chmod +x src/*.py
```

### Service-Specific Troubleshooting

#### LLM Service Issues

**Problem**: `LLMServiceError: GEMINI_API_KEY environment variable is required`
**Solution**: 
1. Ensure `.env` file exists in project root
2. Verify GEMINI_API_KEY is set correctly
3. Check API key validity at Google AI Studio

**Problem**: `google-generativeai package not installed`
**Solution**:
```bash
pip install google-generativeai==0.3.2
```

**Problem**: API quota exceeded
**Solution**:
1. Check your usage at Google AI Studio
2. Consider upgrading to a paid plan
3. Implement rate limiting in production

#### Parsing Service Issues

**Problem**: LlamaParse API errors
**Solution**:
1. Verify API key at LlamaCloud
2. Check document format compatibility
3. Ensure internet connectivity

## Production Deployment

### Environment Variables

For production, set these environment variables:

```bash
export GEMINI_API_KEY="your_production_key"
export LLAMAPARSE_API_KEY="your_production_key"
export MISTRAL_API_KEY="your_production_key"
export GEMINI_MODEL="gemini-1.5-pro"
export GEMINI_TEMPERATURE="0.05"
```

### Security Considerations

1. **Never commit API keys** to version control
2. Use **environment-specific** configuration files
3. **Rotate API keys** regularly
4. **Monitor API usage** and set alerts
5. **Implement rate limiting** for production workloads

### Performance Monitoring

```python
# Monitor processing times
from services.llm_service import get_llm_service_info
info = get_llm_service_info()
print(f"Current model: {info['model']}")
print(f"Configuration: {info}")
```

## Next Steps

1. **Configure API keys** following the guide above
2. **Run test scripts** to verify functionality
3. **Process sample documents** with the main pipeline
4. **Customize extraction rules** for your specific document types
5. **Monitor performance** and adjust settings as needed

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review service documentation:
   - [Google Gemini API Docs](https://ai.google.dev/docs)
   - [LlamaParse Documentation](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
   - [Mistral API Docs](https://docs.mistral.ai/)
3. Verify your API keys and quotas
4. Test individual services in isolation

## Advanced Configuration

### Custom Prompts

You can customize the LLM extraction prompts:

```python
from services.llm_service import extract_entities_with_gemini

custom_prompt = """
Extract only patient name and requested medication from this document:
{document_content}

Return JSON with: patient_name, requested_drug_name
"""

result = extract_entities_with_gemini(document_content, custom_prompt)
```

### Batch Processing

For processing multiple documents:

```python
import os
from services.parsing_service import perform_combined_parsing

pdf_dir = "path/to/pdfs"
for filename in os.listdir(pdf_dir):
    if filename.endswith('.pdf'):
        pdf_path = os.path.join(pdf_dir, filename)
        result = perform_combined_parsing(pdf_path)
        # Process result...
```

This completes the setup guide for the PriorAuthAutomation system with LLM entity extraction capabilities! 