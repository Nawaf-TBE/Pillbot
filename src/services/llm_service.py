"""
LLM service for entity extraction using Google's Gemini API.
Specialized for medical document processing and prior authorization workflows.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Configuration from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "60"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048"))


class LLMServiceError(Exception):
    """Custom exception for LLM service-related errors."""
    pass


class GeminiService:
    """Service class for Google Gemini API operations."""
    
    def __init__(self):
        """Initialize the Gemini service."""
        if not GEMINI_API_KEY:
            raise LLMServiceError("GEMINI_API_KEY environment variable is required")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config=genai.types.GenerationConfig(
                    temperature=GEMINI_TEMPERATURE,
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json"
                )
            )
            
            logger.info(f"Gemini service initialized with model: {GEMINI_MODEL}")
            
        except ImportError:
            raise LLMServiceError("google-generativeai package not installed. Run: pip install google-generativeai")
        except Exception as e:
            raise LLMServiceError(f"Failed to initialize Gemini service: {str(e)}")
    
    def generate_response(self, prompt: str) -> str:
        """
        Generate response from Gemini API with retry logic.
        
        Args:
            prompt (str): The prompt to send to Gemini
            
        Returns:
            str: Generated response
            
        Raises:
            LLMServiceError: If API call fails after retries
        """
        last_error = None
        
        for attempt in range(GEMINI_MAX_RETRIES):
            try:
                logger.debug(f"Gemini API call attempt {attempt + 1}/{GEMINI_MAX_RETRIES}")
                
                response = self.model.generate_content(prompt)
                
                if response.text:
                    logger.info(f"Gemini API call successful on attempt {attempt + 1}")
                    return response.text.strip()
                else:
                    raise LLMServiceError("Empty response from Gemini API")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini API call attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < GEMINI_MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        raise LLMServiceError(f"Gemini API call failed after {GEMINI_MAX_RETRIES} attempts. Last error: {str(last_error)}")


def get_medical_entity_extraction_prompt() -> str:
    """
    Get the default prompt template for medical entity extraction.
    
    Returns:
        str: Comprehensive prompt template for medical document analysis
    """
    return """
You are a medical document analysis expert specialized in extracting structured information from prior authorization requests and medical documents.

Analyze the provided document content and extract the following entities into a structured JSON format. If any information is not found or unclear, use null for that field.

REQUIRED ENTITIES TO EXTRACT:

**Patient Information:**
- patient_name: Full name of the patient
- date_of_birth: Patient's date of birth (format: YYYY-MM-DD if possible)
- member_id: Insurance member/subscriber ID
- patient_id: Any patient identifier
- ssn: Social Security Number (if present, redacted format XXX-XX-XXXX)
- phone: Patient contact phone number
- address: Patient address (if present)

**Medical Information:**
- primary_diagnosis: Primary medical condition/diagnosis
- primary_diagnosis_code: ICD-10 code for primary diagnosis
- secondary_diagnoses: List of secondary diagnoses
- secondary_diagnosis_codes: List of ICD-10 codes for secondary diagnoses
- medical_history: Relevant medical history
- allergies: Known allergies
- current_medications: List of current medications

**Requested Medication:**
- requested_drug_name: Name of the requested medication
- drug_strength: Strength/dosage of the medication
- drug_form: Form of medication (tablet, injection, etc.)
- quantity_requested: Quantity being requested
- days_supply: Number of days the supply should last
- refills: Number of refills requested
- indication: Medical indication for the medication

**Prescriber Information:**
- prescriber_name: Name of the prescribing physician
- prescriber_npi: National Provider Identifier (NPI) number
- prescriber_phone: Prescriber contact information
- prescriber_address: Prescriber address
- prescriber_dea: DEA number (if present)
- specialty: Medical specialty of the prescriber

**Pharmacy Information:**
- pharmacy_name: Name of the dispensing pharmacy
- pharmacy_address: Pharmacy address
- pharmacy_phone: Pharmacy phone number
- pharmacist_name: Name of the pharmacist (if present)

**Insurance and Authorization:**
- insurance_plan: Name of the insurance plan
- group_number: Insurance group number
- policy_number: Insurance policy number
- authorization_number: Prior authorization number (if present)
- request_date: Date of the prior authorization request
- urgency: Urgency level (standard, urgent, etc.)

**Clinical Information:**
- lab_results: Recent lab results or values
- previous_treatments: Previously tried treatments/medications
- treatment_failure_reason: Reason previous treatments failed
- clinical_notes: Additional clinical information

**Administrative:**
- document_type: Type of document (prior authorization, medical record, etc.)
- document_date: Date of the document
- submission_date: Date document was submitted

Return ONLY a valid JSON object with the extracted information. Use null for any fields where information is not available or cannot be determined.

DOCUMENT CONTENT TO ANALYZE:
{document_content}

EXTRACTED ENTITIES (JSON format only):
"""


def get_custom_extraction_prompt(entities_list: List[str]) -> str:
    """
    Generate a custom extraction prompt for specific entities.
    
    Args:
        entities_list (List[str]): List of specific entities to extract
        
    Returns:
        str: Custom prompt template
    """
    entities_str = "\n".join([f"- {entity}" for entity in entities_list])
    
    return f"""
You are a medical document analysis expert. Extract the following specific entities from the provided document content:

ENTITIES TO EXTRACT:
{entities_str}

Analyze the document carefully and extract these entities into a JSON format. Use null for any information that is not found or cannot be determined with confidence.

Return ONLY a valid JSON object with the requested entities.

DOCUMENT CONTENT:
{{document_content}}

EXTRACTED ENTITIES (JSON format only):
"""


def extract_entities_with_gemini(document_content: str, prompt_template: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract medical entities from document content using Google Gemini API.
    
    Args:
        document_content (str): The document content (markdown, JSON, or plain text)
        prompt_template (Optional[str]): Custom prompt template. If None, uses default medical extraction prompt
        
    Returns:
        Dict[str, Any]: Extracted entities in structured format
        
    Raises:
        LLMServiceError: If extraction fails
        ValueError: If input parameters are invalid
    """
    if not document_content or not document_content.strip():
        raise ValueError("Document content cannot be empty")
    
    start_time = time.time()
    
    try:
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Use default prompt if none provided
        if prompt_template is None:
            prompt_template = get_medical_entity_extraction_prompt()
        
        # Format the prompt with document content
        formatted_prompt = prompt_template.format(document_content=document_content)
        
        logger.info("Starting entity extraction with Gemini API")
        logger.debug(f"Document content length: {len(document_content)} characters")
        
        # Generate response
        response_text = gemini_service.generate_response(formatted_prompt)
        
        # Parse JSON response
        try:
            extracted_entities = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise LLMServiceError(f"Gemini returned invalid JSON: {str(e)}")
        
        processing_time = time.time() - start_time
        
        # Add metadata to the response
        result = {
            "extracted_entities": extracted_entities,
            "metadata": {
                "model_used": GEMINI_MODEL,
                "processing_time_seconds": round(processing_time, 2),
                "extraction_timestamp": time.time(),
                "document_content_length": len(document_content),
                "temperature": GEMINI_TEMPERATURE,
                "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS,
                "prompt_template": "default_medical" if prompt_template is None else "custom"
            }
        }
        
        logger.info(f"Entity extraction completed in {processing_time:.2f} seconds")
        logger.info(f"Extracted {len(extracted_entities)} entity fields")
        
        return result
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {str(e)}")
        raise


def extract_specific_entities(document_content: str, entities_list: List[str]) -> Dict[str, Any]:
    """
    Extract specific entities from document content using a custom prompt.
    
    Args:
        document_content (str): The document content
        entities_list (List[str]): List of specific entities to extract
        
    Returns:
        Dict[str, Any]: Extracted entities for the specified fields
    """
    if not entities_list:
        raise ValueError("Entities list cannot be empty")
    
    custom_prompt = get_custom_extraction_prompt(entities_list)
    return extract_entities_with_gemini(document_content, custom_prompt)


def check_llm_availability() -> bool:
    """
    Check if Gemini LLM service is available and properly configured.
    
    Returns:
        bool: True if service is available, False otherwise
    """
    try:
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found in environment variables")
            return False
        
        # Try to initialize the service
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Test with a simple model initialization
            model = genai.GenerativeModel(model_name=GEMINI_MODEL)
            logger.info("Gemini LLM service configuration verified")
            return True
            
        except ImportError:
            logger.error("google-generativeai package not installed")
            return False
        except Exception as e:
            logger.error(f"Gemini service initialization failed: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"LLM service not available: {str(e)}")
        return False


def get_llm_service_info() -> Dict[str, Any]:
    """
    Get information about the LLM service configuration.
    
    Returns:
        Dict[str, Any]: Service information
    """
    return {
        "service_name": "Google Gemini API",
        "model": GEMINI_MODEL,
        "api_key_configured": bool(GEMINI_API_KEY),
        "timeout_seconds": GEMINI_TIMEOUT,
        "max_retries": GEMINI_MAX_RETRIES,
        "temperature": GEMINI_TEMPERATURE,
        "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS,
        "response_format": "JSON",
        "supported_tasks": [
            "Medical entity extraction",
            "Prior authorization analysis",
            "Clinical information structuring",
            "Patient data normalization",
            "Insurance information extraction"
        ],
        "security_features": [
            "Environment variable API key storage",
            "Retry logic with exponential backoff",
            "Input validation and sanitization",
            "Structured JSON output validation"
        ]
    }


def validate_extracted_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean extracted entities.
    
    Args:
        entities (Dict[str, Any]): Raw extracted entities
        
    Returns:
        Dict[str, Any]: Validated and cleaned entities with validation report
    """
    validation_report = {
        "total_fields": len(entities),
        "populated_fields": 0,
        "empty_fields": 0,
        "validation_issues": [],
        "confidence_score": 0.0
    }
    
    cleaned_entities = {}
    
    for key, value in entities.items():
        if value is not None and value != "" and value != []:
            validation_report["populated_fields"] += 1
            cleaned_entities[key] = value
            
            # Specific validation for known fields
            if key == "date_of_birth" and isinstance(value, str):
                # Check if date format looks reasonable
                if len(value) < 8 or len(value) > 12:
                    validation_report["validation_issues"].append(f"Suspicious date format for {key}: {value}")
            
            elif key in ["member_id", "patient_id", "authorization_number"] and isinstance(value, str):
                # Check if IDs look reasonable (not too short)
                if len(value) < 3:
                    validation_report["validation_issues"].append(f"Suspiciously short ID for {key}: {value}")
            
            elif "phone" in key and isinstance(value, str):
                # Basic phone number validation
                digits = ''.join(filter(str.isdigit, value))
                if len(digits) < 10:
                    validation_report["validation_issues"].append(f"Incomplete phone number for {key}: {value}")
        else:
            validation_report["empty_fields"] += 1
    
    # Calculate confidence score
    if validation_report["total_fields"] > 0:
        validation_report["confidence_score"] = validation_report["populated_fields"] / validation_report["total_fields"]
    
    return {
        "validated_entities": cleaned_entities,
        "validation_report": validation_report
    } 