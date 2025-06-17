"""
Document parsing service using LlamaParse API for structured content extraction.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Configuration from environment variables
LLAMAPARSE_API_KEY = os.getenv("LLAMAPARSE_API_KEY")
LLAMAPARSE_API_BASE_URL = os.getenv("LLAMAPARSE_API_BASE_URL", "https://api.cloud.llamaindex.ai/api/parsing")
LLAMAPARSE_TIMEOUT = int(os.getenv("LLAMAPARSE_TIMEOUT", "300"))  # 5 minutes default
LLAMAPARSE_MAX_POLL_ATTEMPTS = int(os.getenv("LLAMAPARSE_MAX_POLL_ATTEMPTS", "60"))  # 60 attempts = ~5 minutes
LLAMAPARSE_POLL_INTERVAL = int(os.getenv("LLAMAPARSE_POLL_INTERVAL", "5"))  # 5 seconds between polls


class ParsingError(Exception):
    """Custom exception for parsing-related errors."""
    pass


class LlamaParseService:
    """Service class for LlamaParse operations."""
    
    def __init__(self):
        """Initialize the LlamaParse service."""
        if not LLAMAPARSE_API_KEY:
            raise ParsingError("LLAMAPARSE_API_KEY environment variable is required")
        
        self.api_key = LLAMAPARSE_API_KEY
        self.base_url = LLAMAPARSE_API_BASE_URL
        self.timeout = LLAMAPARSE_TIMEOUT
        self.max_poll_attempts = LLAMAPARSE_MAX_POLL_ATTEMPTS
        self.poll_interval = LLAMAPARSE_POLL_INTERVAL
        
        # Try to import and initialize LlamaParse
        try:
            from llama_parse import LlamaParse
            self.parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",  # Request markdown output
                verbose=True,
                language="en"  # English language for medical documents
            )
            logger.info("LlamaParse service initialized successfully")
        except ImportError:
            raise ParsingError("llama-parse package not installed. Run: pip install llama-parse")
        except Exception as e:
            raise ParsingError(f"Failed to initialize LlamaParse: {str(e)}")
    
    def parse_document(self, file_path: str) -> str:
        """
        Parse a document using LlamaParse and return markdown content.
        
        Args:
            file_path (str): Path to the document file
            
        Returns:
            str: Parsed content in markdown format
            
        Raises:
            ParsingError: If parsing fails
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"Starting LlamaParse processing for: {file_path}")
            start_time = time.time()
            
            # Parse the document
            documents = self.parser.load_data(str(file_path))
            
            if not documents:
                raise ParsingError("No content could be extracted from the document")
            
            # Combine all document text (LlamaParse can split large docs into multiple parts)
            markdown_content = ""
            for doc in documents:
                if hasattr(doc, 'text'):
                    markdown_content += doc.text + "\n\n"
                else:
                    markdown_content += str(doc) + "\n\n"
            
            processing_time = time.time() - start_time
            logger.info(f"LlamaParse processing completed in {processing_time:.2f} seconds")
            logger.info(f"Extracted {len(markdown_content)} characters of markdown content")
            
            return markdown_content.strip()
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"LlamaParse processing failed: {str(e)}")
            raise ParsingError(f"Document parsing failed: {str(e)}")


def perform_llamaparse(file_path: str) -> str:
    """
    Parse a PDF document using LlamaParse API and return markdown content.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Parsed content in markdown format
        
    Raises:
        ParsingError: If parsing fails
        FileNotFoundError: If the input file doesn't exist
    """
    start_time = time.time()
    
    # Validate input file
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    # Check supported file types
    supported_extensions = ['.pdf', '.docx', '.doc', '.txt', '.md']
    if file_extension not in supported_extensions:
        raise ParsingError(f"Unsupported file type: {file_extension}. Supported: {supported_extensions}")
    
    try:
        # Initialize parsing service
        parser_service = LlamaParseService()
        logger.info(f"Starting document parsing for: {file_path}")
        
        # Parse the document
        markdown_content = parser_service.parse_document(str(file_path))
        
        processing_time = time.time() - start_time
        logger.info(f"Document parsing completed in {processing_time:.2f} seconds")
        
        return markdown_content
        
    except Exception as e:
        logger.error(f"Document parsing failed: {str(e)}")
        raise


def perform_llamaparse_with_metadata(file_path: str) -> Dict[str, Any]:
    """
    Parse a document using LlamaParse and return both content and metadata.
    
    Args:
        file_path (str): Path to the document file
        
    Returns:
        Dict[str, Any]: Dictionary containing parsed content and metadata
    """
    start_time = time.time()
    
    try:
        # Parse the document
        markdown_content = perform_llamaparse(file_path)
        
        file_path = Path(file_path)
        processing_time = time.time() - start_time
        
        # Analyze the content
        lines = markdown_content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        word_count = len(markdown_content.split())
        
        # Extract headers (lines starting with #)
        headers = [line.strip() for line in lines if line.strip().startswith('#')]
        
        # Basic document structure analysis
        has_tables = '|' in markdown_content
        has_lists = any(line.strip().startswith(('-', '*', '+')) for line in lines)
        has_headers = len(headers) > 0
        
        result = {
            "markdown_content": markdown_content,
            "metadata": {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "processing_time_seconds": round(processing_time, 2),
                "parsing_method": "llamaparse_api",
                "content_stats": {
                    "total_characters": len(markdown_content),
                    "total_lines": len(lines),
                    "non_empty_lines": len(non_empty_lines),
                    "word_count": word_count,
                    "header_count": len(headers),
                    "has_tables": has_tables,
                    "has_lists": has_lists,
                    "has_headers": has_headers
                },
                "extracted_headers": headers[:10]  # First 10 headers
            }
        }
        
        logger.info(f"Document parsing completed with metadata")
        return result
        
    except Exception as e:
        logger.error(f"Document parsing with metadata failed: {str(e)}")
        raise


def check_parsing_availability() -> bool:
    """
    Check if LlamaParse service is available and properly configured.
    
    Returns:
        bool: True if parsing service is available, False otherwise
    """
    try:
        if not LLAMAPARSE_API_KEY:
            logger.warning("LLAMAPARSE_API_KEY not found in environment variables")
            return False
        
        # Try to initialize the service
        try:
            from llama_parse import LlamaParse
            # Test initialization without making API calls
            parser = LlamaParse(api_key=LLAMAPARSE_API_KEY, result_type="markdown")
            logger.info("LlamaParse service configuration verified")
            return True
        except ImportError:
            logger.error("llama-parse package not installed")
            return False
        except Exception as e:
            logger.error(f"LlamaParse initialization failed: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"Parsing service not available: {str(e)}")
        return False


def get_parsing_service_info() -> Dict[str, Any]:
    """
    Get information about the parsing service configuration.
    
    Returns:
        Dict[str, Any]: Service information
    """
    return {
        "service_name": "LlamaParse API",
        "api_base_url": LLAMAPARSE_API_BASE_URL,
        "timeout_seconds": LLAMAPARSE_TIMEOUT,
        "max_poll_attempts": LLAMAPARSE_MAX_POLL_ATTEMPTS,
        "poll_interval_seconds": LLAMAPARSE_POLL_INTERVAL,
        "api_key_configured": bool(LLAMAPARSE_API_KEY),
        "supported_formats": [".pdf", ".docx", ".doc", ".txt", ".md"],
        "output_format": "markdown",
        "features": [
            "Structured content extraction",
            "Table preservation",
            "Header hierarchy detection", 
            "List formatting",
            "Metadata extraction"
        ]
    }


def extract_document_sections(markdown_content: str) -> Dict[str, str]:
    """
    Extract common document sections from parsed markdown content.
    Useful for medical/prior authorization documents.
    
    Args:
        markdown_content (str): Parsed markdown content
        
    Returns:
        Dict[str, str]: Dictionary of extracted sections
    """
    sections = {}
    current_section = "introduction"
    current_content = []
    
    lines = markdown_content.split('\n')
    
    # Common medical document section keywords
    section_keywords = {
        "patient": ["patient", "member", "subscriber"],
        "diagnosis": ["diagnosis", "condition", "medical history"],
        "medication": ["medication", "drug", "prescription", "therapy"],
        "physician": ["physician", "doctor", "provider", "prescriber"],
        "insurance": ["insurance", "coverage", "plan", "policy"],
        "authorization": ["authorization", "approval", "request"],
        "clinical": ["clinical", "lab", "test", "result"],
        "treatment": ["treatment", "procedure", "intervention"]
    }
    
    for line in lines:
        line = line.strip()
        
        # Check if this is a header
        if line.startswith('#'):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
                current_content = []
            
            # Determine new section based on header content
            header_text = line.lstrip('#').strip().lower()
            current_section = "other"
            
            for section_name, keywords in section_keywords.items():
                if any(keyword in header_text for keyword in keywords):
                    current_section = section_name
                    break
            
            # Use header text as section name if no keywords match
            if current_section == "other":
                current_section = header_text.replace(' ', '_')[:50]  # Limit length
        
        # Add content to current section
        if line:
            current_content.append(line)
    
    # Add final section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def analyze_prior_auth_document(markdown_content: str) -> Dict[str, Any]:
    """
    Analyze parsed markdown content specifically for prior authorization documents.
    
    Args:
        markdown_content (str): Parsed markdown content
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    analysis = {
        "document_type": "unknown",
        "confidence": 0.0,
        "key_fields_found": [],
        "missing_fields": [],
        "sections": {},
        "entities": {}
    }
    
    content_lower = markdown_content.lower()
    
    # Prior authorization document indicators
    pa_indicators = [
        "prior authorization", "pre-authorization", "preauthorization",
        "prior auth", "pa request", "authorization request"
    ]
    
    # Check if this looks like a prior auth document
    pa_score = sum(1 for indicator in pa_indicators if indicator in content_lower)
    
    if pa_score > 0:
        analysis["document_type"] = "prior_authorization"
        analysis["confidence"] = min(pa_score / len(pa_indicators), 1.0)
    
    # Key fields to look for
    key_fields = {
        "patient_name": ["patient name", "member name", "subscriber"],
        "date_of_birth": ["date of birth", "dob", "birth date"],
        "member_id": ["member id", "subscriber id", "policy number"],
        "medication": ["medication", "drug name", "prescription"],
        "diagnosis": ["diagnosis", "condition", "icd"],
        "physician": ["physician", "doctor", "prescriber", "provider"],
        "npi": ["npi", "provider id"],
        "pharmacy": ["pharmacy", "dispensing"],
        "quantity": ["quantity", "supply", "days supply"],
        "strength": ["strength", "dosage", "mg", "ml"]
    }
    
    found_fields = []
    for field, keywords in key_fields.items():
        if any(keyword in content_lower for keyword in keywords):
            found_fields.append(field)
    
    analysis["key_fields_found"] = found_fields
    analysis["missing_fields"] = [field for field in key_fields.keys() if field not in found_fields]
    
    # Extract sections
    analysis["sections"] = extract_document_sections(markdown_content)
    
    # Simple entity extraction (could be enhanced with NLP)
    entities = {}
    lines = markdown_content.split('\n')
    for line in lines:
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if any(field_keyword in key for field_keyword in ["name", "patient", "member"]):
                entities["patient_name"] = value
            elif any(field_keyword in key for field_keyword in ["medication", "drug"]):
                entities["medication"] = value
            elif any(field_keyword in key for field_keyword in ["diagnosis", "condition"]):
                entities["diagnosis"] = value
    
    analysis["entities"] = entities
    
    return analysis


def extract_with_pdfplumber(file_path: str, extraction_rules: Dict) -> Dict:
    """
    Extract specific data from PDF using pdfplumber based on extraction rules.
    
    Args:
        file_path (str): Path to the PDF file
        extraction_rules (Dict): Dictionary defining extraction rules with structure:
            {
                "bounding_boxes": {
                    "field_name": {"x0": float, "y0": float, "x1": float, "y1": float, "page": int}
                },
                "table_extraction": {
                    "page": int,
                    "table_settings": dict,
                    "columns_of_interest": list
                },
                "regex_patterns": {
                    "field_name": {"pattern": str, "flags": int, "page": int or "all"}
                },
                "text_search": {
                    "field_name": {"search_terms": list, "context_lines": int, "page": int or "all"}
                }
            }
    
    Returns:
        Dict: Extracted data organized by extraction method and field name
    """
    try:
        import pdfplumber
    except ImportError:
        raise ParsingError("pdfplumber package not installed. Run: pip install pdfplumber")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_path = Path(file_path)
    if file_path.suffix.lower() != '.pdf':
        raise ParsingError(f"pdfplumber only supports PDF files, got: {file_path.suffix}")
    
    logger.info(f"Starting pdfplumber extraction for: {file_path}")
    start_time = time.time()
    
    extracted_data = {
        "bounding_box_data": {},
        "table_data": {},
        "regex_data": {},
        "text_search_data": {},
        "metadata": {
            "file_path": str(file_path),
            "extraction_timestamp": time.time(),
            "total_pages": 0,
            "processing_time_seconds": 0
        }
    }
    
    try:
        with pdfplumber.open(file_path) as pdf:
            extracted_data["metadata"]["total_pages"] = len(pdf.pages)
            
            # Extract data using bounding boxes
            if "bounding_boxes" in extraction_rules:
                logger.info("Processing bounding box extractions")
                for field_name, bbox_config in extraction_rules["bounding_boxes"].items():
                    try:
                        page_num = bbox_config.get("page", 0)
                        if page_num < len(pdf.pages):
                            page = pdf.pages[page_num]
                            bbox = (bbox_config["x0"], bbox_config["y0"], 
                                   bbox_config["x1"], bbox_config["y1"])
                            
                            # Extract text from bounding box
                            cropped = page.crop(bbox)
                            text = cropped.extract_text()
                            
                            extracted_data["bounding_box_data"][field_name] = {
                                "text": text.strip() if text else "",
                                "bbox": bbox,
                                "page": page_num,
                                "confidence": 1.0 if text and text.strip() else 0.0
                            }
                            logger.debug(f"Extracted '{field_name}' from bbox: {text[:50] if text else 'No text'}")
                    except Exception as e:
                        logger.error(f"Failed to extract bounding box data for '{field_name}': {str(e)}")
                        extracted_data["bounding_box_data"][field_name] = {
                            "text": "",
                            "bbox": bbox_config,
                            "page": page_num,
                            "confidence": 0.0,
                            "error": str(e)
                        }
            
            # Extract table data
            if "table_extraction" in extraction_rules:
                logger.info("Processing table extractions")
                table_config = extraction_rules["table_extraction"]
                page_num = table_config.get("page", 0)
                
                if page_num < len(pdf.pages):
                    page = pdf.pages[page_num]
                    table_settings = table_config.get("table_settings", {})
                    columns_of_interest = table_config.get("columns_of_interest", [])
                    
                    try:
                        # Extract all tables from the page
                        # Use default settings if table_settings contains invalid parameters
                        try:
                            tables = page.extract_tables(**table_settings)
                        except TypeError as e:
                            logger.warning(f"Invalid table settings, using defaults: {e}")
                            # Use basic table extraction without custom settings
                            tables = page.extract_tables()
                        
                        processed_tables = []
                        for i, table in enumerate(tables):
                            if table:
                                # Convert table to list of dictionaries if headers are available
                                if len(table) > 1:
                                    headers = table[0]
                                    rows = table[1:]
                                    
                                    # Filter columns if specified
                                    if columns_of_interest:
                                        col_indices = []
                                        filtered_headers = []
                                        for col_name in columns_of_interest:
                                            if col_name in headers:
                                                idx = headers.index(col_name)
                                                col_indices.append(idx)
                                                filtered_headers.append(col_name)
                                        
                                        if col_indices:
                                            filtered_rows = []
                                            for row in rows:
                                                filtered_row = [row[idx] if idx < len(row) else "" for idx in col_indices]
                                                filtered_rows.append(filtered_row)
                                            
                                            processed_table = {
                                                "headers": filtered_headers,
                                                "rows": filtered_rows,
                                                "row_count": len(filtered_rows)
                                            }
                                        else:
                                            processed_table = {
                                                "headers": headers,
                                                "rows": rows,
                                                "row_count": len(rows)
                                            }
                                    else:
                                        processed_table = {
                                            "headers": headers,
                                            "rows": rows,
                                            "row_count": len(rows)
                                        }
                                    
                                    processed_tables.append(processed_table)
                        
                        extracted_data["table_data"] = {
                            "tables": processed_tables,
                            "table_count": len(processed_tables),
                            "page": page_num
                        }
                        logger.info(f"Extracted {len(processed_tables)} tables from page {page_num}")
                        
                    except Exception as e:
                        logger.error(f"Failed to extract table data: {str(e)}")
                        extracted_data["table_data"] = {
                            "tables": [],
                            "table_count": 0,
                            "page": page_num,
                            "error": str(e)
                        }
            
            # Extract data using regex patterns
            if "regex_patterns" in extraction_rules:
                logger.info("Processing regex pattern extractions")
                for field_name, regex_config in extraction_rules["regex_patterns"].items():
                    pattern = regex_config["pattern"]
                    flags = regex_config.get("flags", 0)
                    target_page = regex_config.get("page", "all")
                    
                    matches = []
                    
                    try:
                        compiled_pattern = re.compile(pattern, flags)
                        
                        if target_page == "all":
                            pages_to_search = range(len(pdf.pages))
                        else:
                            pages_to_search = [target_page] if target_page < len(pdf.pages) else []
                        
                        for page_num in pages_to_search:
                            page = pdf.pages[page_num]
                            page_text = page.extract_text()
                            
                            if page_text:
                                page_matches = compiled_pattern.findall(page_text)
                                for match in page_matches:
                                    matches.append({
                                        "match": match,
                                        "page": page_num
                                    })
                        
                        extracted_data["regex_data"][field_name] = {
                            "pattern": pattern,
                            "matches": matches,
                            "match_count": len(matches)
                        }
                        logger.debug(f"Found {len(matches)} matches for pattern '{field_name}'")
                        
                    except Exception as e:
                        logger.error(f"Failed to process regex pattern for '{field_name}': {str(e)}")
                        extracted_data["regex_data"][field_name] = {
                            "pattern": pattern,
                            "matches": [],
                            "match_count": 0,
                            "error": str(e)
                        }
            
            # Extract data using text search
            if "text_search" in extraction_rules:
                logger.info("Processing text search extractions")
                for field_name, search_config in extraction_rules["text_search"].items():
                    search_terms = search_config["search_terms"]
                    context_lines = search_config.get("context_lines", 2)
                    target_page = search_config.get("page", "all")
                    
                    found_contexts = []
                    
                    try:
                        if target_page == "all":
                            pages_to_search = range(len(pdf.pages))
                        else:
                            pages_to_search = [target_page] if target_page < len(pdf.pages) else []
                        
                        for page_num in pages_to_search:
                            page = pdf.pages[page_num]
                            page_text = page.extract_text()
                            
                            if page_text:
                                lines = page_text.split('\n')
                                
                                for i, line in enumerate(lines):
                                    for term in search_terms:
                                        if term.lower() in line.lower():
                                            # Extract context around the match
                                            start_idx = max(0, i - context_lines)
                                            end_idx = min(len(lines), i + context_lines + 1)
                                            context = '\n'.join(lines[start_idx:end_idx])
                                            
                                            found_contexts.append({
                                                "search_term": term,
                                                "matched_line": line.strip(),
                                                "context": context,
                                                "page": page_num,
                                                "line_number": i
                                            })
                        
                        extracted_data["text_search_data"][field_name] = {
                            "search_terms": search_terms,
                            "contexts": found_contexts,
                            "match_count": len(found_contexts)
                        }
                        logger.debug(f"Found {len(found_contexts)} text search matches for '{field_name}'")
                        
                    except Exception as e:
                        logger.error(f"Failed to process text search for '{field_name}': {str(e)}")
                        extracted_data["text_search_data"][field_name] = {
                            "search_terms": search_terms,
                            "contexts": [],
                            "match_count": 0,
                            "error": str(e)
                        }
        
        processing_time = time.time() - start_time
        extracted_data["metadata"]["processing_time_seconds"] = round(processing_time, 2)
        
        logger.info(f"pdfplumber extraction completed in {processing_time:.2f} seconds")
        return extracted_data
        
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {str(e)}")
        raise ParsingError(f"pdfplumber extraction failed: {str(e)}")


def perform_combined_parsing(file_path: str, extraction_rules: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Combine LlamaParse's structured output with pdfplumber's precise extractions.
    
    Args:
        file_path (str): Path to the document file
        extraction_rules (Optional[Dict]): Rules for pdfplumber extraction
        
    Returns:
        Dict[str, Any]: Combined parsing results
    """
    start_time = time.time()
    
    combined_results = {
        "llamaparse_results": {},
        "pdfplumber_results": {},
        "combined_analysis": {},
        "metadata": {
            "file_path": str(file_path),
            "parsing_timestamp": time.time(),
            "processing_time_seconds": 0,
            "methods_used": []
        }
    }
    
    # First, try LlamaParse for structured content
    try:
        if check_parsing_availability():
            logger.info("Starting LlamaParse extraction")
            llamaparse_result = perform_llamaparse_with_metadata(file_path)
            combined_results["llamaparse_results"] = llamaparse_result
            combined_results["metadata"]["methods_used"].append("llamaparse")
            
            # Analyze the LlamaParse output
            if "markdown_content" in llamaparse_result:
                combined_results["combined_analysis"]["prior_auth_analysis"] = analyze_prior_auth_document(
                    llamaparse_result["markdown_content"]
                )
        else:
            logger.warning("LlamaParse service not available, skipping structured parsing")
            combined_results["llamaparse_results"] = {"error": "LlamaParse service not available"}
    
    except Exception as e:
        logger.error(f"LlamaParse extraction failed: {str(e)}")
        combined_results["llamaparse_results"] = {"error": str(e)}
    
    # Then, use pdfplumber for precise extractions if rules are provided
    if extraction_rules and file_path.lower().endswith('.pdf'):
        try:
            logger.info("Starting pdfplumber extraction")
            pdfplumber_result = extract_with_pdfplumber(file_path, extraction_rules)
            combined_results["pdfplumber_results"] = pdfplumber_result
            combined_results["metadata"]["methods_used"].append("pdfplumber")
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {str(e)}")
            combined_results["pdfplumber_results"] = {"error": str(e)}
    else:
        if not extraction_rules:
            logger.info("No extraction rules provided, skipping pdfplumber extraction")
        elif not file_path.lower().endswith('.pdf'):
            logger.info("File is not a PDF, skipping pdfplumber extraction")
        combined_results["pdfplumber_results"] = {"skipped": "No extraction rules provided or file is not PDF"}
    
    # Combine insights from both methods
    combined_analysis = combined_results["combined_analysis"]
    
    # If we have both results, create enhanced analysis
    if ("llamaparse_results" in combined_results and "markdown_content" in combined_results["llamaparse_results"] and
        "pdfplumber_results" in combined_results and "bounding_box_data" in combined_results["pdfplumber_results"]):
        
        # Cross-validate findings
        bbox_data = combined_results["pdfplumber_results"]["bounding_box_data"]
        markdown_content = combined_results["llamaparse_results"]["markdown_content"]
        
        validation_results = {}
        for field_name, bbox_result in bbox_data.items():
            if bbox_result.get("text"):
                # Check if the bbox text appears in the markdown content
                bbox_text = bbox_result["text"].lower().strip()
                markdown_lower = markdown_content.lower()
                
                validation_results[field_name] = {
                    "bbox_text": bbox_result["text"],
                    "found_in_markdown": bbox_text in markdown_lower,
                    "confidence": bbox_result.get("confidence", 0.0)
                }
        
        combined_analysis["cross_validation"] = validation_results
    
    processing_time = time.time() - start_time
    combined_results["metadata"]["processing_time_seconds"] = round(processing_time, 2)
    
    logger.info(f"Combined parsing completed in {processing_time:.2f} seconds using methods: {combined_results['metadata']['methods_used']}")
    
    return combined_results 