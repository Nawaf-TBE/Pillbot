#!/usr/bin/env python3
"""
Patient Data Extractor Module

Provides functionality to:
1. Analyze blank forms and generate extraction schemas  
2. Extract structured patient data from scanned documents
3. Generate clean output documents with extracted information
"""

import json
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import logging
from dataclasses import dataclass, asdict

# Import existing services
from src.services.ocr_service import TesseractOCRService
from src.services.llm_service import GeminiService
from src.services.parsing_service import LlamaParseService

logger = logging.getLogger(__name__)

@dataclass
class ExtractedField:
    """Represents an extracted field with metadata"""
    name: str
    value: Any
    field_type: str
    confidence: float
    source_location: Optional[str] = None
    validation_status: str = "valid"

@dataclass 
class PatientSchema:
    """Represents a patient data schema"""
    schema_name: str
    version: str
    description: str
    fields: Dict[str, Dict[str, Any]]
    created_date: str
    source_document: str

class PatientDataExtractor:
    """Main class for patient data extraction workflow"""
    
    def __init__(self, output_directory: str = "data/patient_extraction"):
        """Initialize the patient data extractor"""
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.ocr_service = TesseractOCRService()
        self.llm_service = GeminiService()
        self.parsing_service = LlamaParseService()
        
        # Schema storage
        self.schemas_directory = self.output_directory / "schemas"
        self.schemas_directory.mkdir(exist_ok=True)
        
        logger.info(f"PatientDataExtractor initialized")
    
    def analyze_blank_form(self, form_path: str, schema_name: str = None) -> PatientSchema:
        """
        Analyze a blank form to generate an extraction schema
        
        Args:
            form_path: Path to the blank form (PDF, image, etc.)
            schema_name: Optional name for the schema
            
        Returns:
            PatientSchema object
        """
        logger.info(f"Analyzing blank form: {form_path}")
        
        if schema_name is None:
            schema_name = f"schema_{Path(form_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract form structure
        form_structure = self._extract_form_structure(form_path)
        
        # Generate schema using LLM analysis
        schema_fields = self._generate_schema_with_llm(form_structure, form_path)
        
        # Create schema object
        schema = PatientSchema(
            schema_name=schema_name,
            version="1.0", 
            description=f"Auto-generated schema from {Path(form_path).name}",
            fields=schema_fields,
            created_date=datetime.now().isoformat(),
            source_document=str(form_path)
        )
        
        # Save schema
        self._save_schema(schema)
        
        logger.info(f"Schema generated successfully: {schema_name}")
        return schema
    
    def _extract_form_structure(self, form_path: str) -> Dict[str, Any]:
        """Extract structural information from a blank form"""
        logger.info("Extracting form structure...")
        
        form_data = {
            "text_content": "",
            "form_fields": [],
            "visual_elements": []
        }
        
        try:
            # Parse document using existing parsing service
            parsing_result = self.parsing_service.parse_document(form_path)
            form_data["text_content"] = parsing_result if isinstance(parsing_result, str) else ""
            
            # Analyze PDF form fields if it's a PDF
            if form_path.lower().endswith('.pdf'):
                pdf_fields = self._analyze_pdf_form_fields(form_path)
                form_data["form_fields"] = pdf_fields
                
                # OCR analysis for PDF
                ocr_result = self.ocr_service.perform_ocr_on_pdf(form_path)
                if ocr_result.get("success"):
                    form_data["visual_elements"] = ocr_result.get("word_data", [])
                    if not form_data["text_content"]:
                        form_data["text_content"] = ocr_result.get("text", "")
            else:
                # OCR analysis for image files
                ocr_result = self.ocr_service.perform_ocr_on_image(form_path)
                if ocr_result.get("success"):
                    form_data["visual_elements"] = ocr_result.get("word_data", [])
                    if not form_data["text_content"]:
                        form_data["text_content"] = ocr_result.get("text", "")
            
        except Exception as e:
            logger.error(f"Error extracting form structure: {e}")
        
        return form_data
    
    def _analyze_pdf_form_fields(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Analyze PDF form fields to understand structure"""
        fields = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                widgets = list(page.widgets())
                
                for widget in widgets:
                    field_info = {
                        "name": widget.field_name or "unknown",
                        "type": widget.field_type_string,
                        "page": page_num + 1,
                        "rect": [widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1],
                        "required": bool(widget.field_flags & 2),
                    }
                    fields.append(field_info)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error analyzing PDF form fields: {e}")
        
        return fields
    
    def _generate_schema_with_llm(self, form_structure: Dict[str, Any], form_path: str) -> Dict[str, Dict[str, Any]]:
        """Use LLM to analyze form structure and generate comprehensive schema"""
        
        # Prepare context for LLM
        context_text = form_structure.get("text_content", "")[:8000]  # Limit text length
        form_fields = form_structure.get("form_fields", [])
        
        # Create detailed prompt for schema generation
        prompt = f"""
Analyze this blank patient form and generate a comprehensive data extraction schema.

Form Text Content:
{context_text}

Form Fields Found: {len(form_fields)}
Fields: {[f.get('name', 'unknown') for f in form_fields[:20]]}

Please identify all patient information fields that would typically need to be extracted from completed versions of this form. For each field, provide:

1. Field name (snake_case format)
2. Data type (string, date, number, phone, email, address, text, list_of_strings, boolean)
3. Description of what the field contains
4. Whether it's typically required
5. Alternative names/labels that might be used for this field

Focus on common patient intake fields like:
- Demographics (name, DOB, gender, address, phone, email)
- Medical information (allergies, medications, medical history, diagnosis)
- Insurance information (member ID, group number, insurance company)
- Emergency contacts (name, phone, relationship)
- Provider information (doctor name, NPI, clinic)

Return ONLY a valid JSON object with this exact structure:
{{
    "field_name": {{
        "type": "string",
        "description": "Description of the field",
        "required": true,
        "alternative_names": ["list", "of", "possible", "labels"],
        "validation_pattern": "regex pattern if applicable"
    }}
}}

Important: Return ONLY the JSON object, no additional text or explanation.
"""
        
        try:
            # Call LLM service for schema generation
            llm_response = self.llm_service.generate_response(prompt)
            
            if llm_response:
                # Try to parse the LLM response as JSON
                schema_fields = self._parse_llm_schema_response(llm_response)
                if schema_fields:
                    return schema_fields
            
        except Exception as e:
            logger.error(f"Error in LLM schema generation: {e}")
        
        # Fallback: Generate basic schema from form fields and common patterns
        return self._generate_fallback_schema(form_structure)
    
    def _parse_llm_schema_response(self, llm_response: Any) -> Dict[str, Dict[str, Any]]:
        """Parse and validate LLM response for schema generation"""
        schema_fields = {}
        
        try:
            # If the response is already a dictionary
            if isinstance(llm_response, dict):
                for field_name, field_config in llm_response.items():
                    if isinstance(field_config, dict) and "type" in field_config:
                        schema_fields[field_name] = {
                            "type": field_config.get("type", "string"),
                            "description": field_config.get("description", ""),
                            "required": field_config.get("required", False),
                            "alternative_names": field_config.get("alternative_names", []),
                            "validation_pattern": field_config.get("validation_pattern")
                        }
            
            # If it's a string, try to parse as JSON
            elif isinstance(llm_response, str):
                try:
                    parsed_response = json.loads(llm_response)
                    return self._parse_llm_schema_response(parsed_response)
                except json.JSONDecodeError:
                    logger.warning("Could not parse LLM response as JSON")
                    
        except Exception as e:
            logger.error(f"Error parsing LLM schema response: {e}")
        
        return schema_fields
    
    def _generate_fallback_schema(self, form_structure: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Generate a basic fallback schema if LLM analysis fails"""
        schema_fields = {}
        
        # Common patient intake fields as fallback
        common_fields = {
            "patient_first_name": {
                "type": "string",
                "description": "Patient's first name",
                "required": True,
                "alternative_names": ["first name", "given name", "fname", "first", "patient name"],
                "validation_pattern": None
            },
            "patient_last_name": {
                "type": "string",
                "description": "Patient's last name", 
                "required": True,
                "alternative_names": ["last name", "surname", "family name", "lname", "lastname"],
                "validation_pattern": None
            },
            "date_of_birth": {
                "type": "date",
                "description": "Patient's date of birth",
                "required": True,
                "alternative_names": ["DOB", "birth date", "birthdate", "date of birth", "birthday"],
                "validation_pattern": r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"
            },
            "phone_number": {
                "type": "phone", 
                "description": "Patient's phone number",
                "required": True,
                "alternative_names": ["phone", "telephone", "mobile", "cell phone", "contact number"],
                "validation_pattern": r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}"
            },
            "email_address": {
                "type": "email",
                "description": "Patient's email address",
                "required": False,
                "alternative_names": ["email", "e-mail", "email address"],
                "validation_pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            },
            "address": {
                "type": "address",
                "description": "Patient's home address",
                "required": True,
                "alternative_names": ["home address", "street address", "mailing address", "address"],
                "validation_pattern": None
            },
            "allergies": {
                "type": "list_of_strings",
                "description": "Patient's known allergies",
                "required": False,
                "alternative_names": ["allergy", "allergies", "allergic to", "drug allergies", "food allergies"],
                "validation_pattern": None
            },
            "medical_history": {
                "type": "text",
                "description": "Patient's medical history summary",
                "required": False,
                "alternative_names": ["past medical history", "medical background", "health history", "history"],
                "validation_pattern": None
            },
            "emergency_contact_name": {
                "type": "string", 
                "description": "Emergency contact person's name",
                "required": False,
                "alternative_names": ["emergency contact", "in case of emergency", "ICE contact", "contact name"],
                "validation_pattern": None
            },
            "emergency_contact_phone": {
                "type": "phone",
                "description": "Emergency contact phone number",
                "required": False,
                "alternative_names": ["emergency phone", "emergency number", "contact phone"],
                "validation_pattern": r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}"
            },
            "insurance_member_id": {
                "type": "string",
                "description": "Insurance member ID number",
                "required": False,
                "alternative_names": ["member id", "member number", "insurance id", "policy number"],
                "validation_pattern": None
            },
            "insurance_company": {
                "type": "string",
                "description": "Insurance company name",
                "required": False,
                "alternative_names": ["insurance", "insurer", "insurance company", "plan"],
                "validation_pattern": None
            }
        }
        
        # Add fields detected from form analysis
        form_fields = form_structure.get("form_fields", [])
        text_content = form_structure.get("text_content", "").lower()
        
        # Look for additional field patterns in the text
        additional_patterns = {
            "gender": ["gender", "sex", "male", "female"],
            "ssn": ["ssn", "social security", "social security number"],
            "marital_status": ["marital status", "married", "single", "divorced"],
            "occupation": ["occupation", "job", "work", "employer"],
            "referring_physician": ["referring physician", "doctor", "provider", "physician"]
        }
        
        for field_name, keywords in additional_patterns.items():
            if any(keyword in text_content for keyword in keywords):
                schema_fields[field_name] = {
                    "type": "string",
                    "description": f"Patient's {field_name.replace('_', ' ')}",
                    "required": False,
                    "alternative_names": keywords,
                    "validation_pattern": None
                }
        
        # Merge common fields with detected fields
        schema_fields.update(common_fields)
        
        return schema_fields
    
    def _save_schema(self, schema: PatientSchema):
        """Save schema to file"""
        schema_file = self.schemas_directory / f"{schema.schema_name}.json"
        
        with open(schema_file, 'w') as f:
            json.dump(asdict(schema), f, indent=2)
        
        logger.info(f"Schema saved to: {schema_file}")
    
    def extract_patient_data(self, document_path: str, schema_name: str = None, 
                           output_format: str = "markdown") -> Dict[str, Any]:
        """
        Extract patient data from a filled document using a schema
        
        Args:
            document_path: Path to the filled patient document
            schema_name: Name of the schema to use (if None, uses most recent)
            output_format: Output format ('json', 'markdown')
            
        Returns:
            Dictionary containing extraction results
        """
        logger.info(f"Extracting patient data from: {document_path}")
        
        # Load schema
        schema = self._load_schema(schema_name)
        if not schema:
            raise ValueError(f"No suitable schema found. Available schemas: {self.list_schemas()}")
        
        # Extract text from document
        document_text = self._extract_document_text(document_path)
        
        # Extract data using schema
        extracted_fields = self._extract_fields_with_schema(document_text, schema, document_path)
        
        # Generate output document
        output_doc = self._generate_output_document(extracted_fields, schema, document_path, output_format)
        
        # Calculate success metrics
        success_rate = self._calculate_success_rate(extracted_fields, schema)
        
        # Prepare results
        results = {
            "document_path": str(document_path),
            "schema_used": schema.schema_name,
            "extraction_timestamp": datetime.now().isoformat(),
            "extracted_fields": {field.name: asdict(field) for field in extracted_fields},
            "output_document": output_doc,
            "success_rate": success_rate,
            "total_fields": len(schema.fields),
            "extracted_count": len([f for f in extracted_fields if f.value is not None])
        }
        
        # Save results
        self._save_extraction_results(results, document_path)
        
        return results
    
    def _load_schema(self, schema_name: str = None) -> Optional[PatientSchema]:
        """Load specified schema or most recent schema"""
        
        if schema_name:
            schema_file = self.schemas_directory / f"{schema_name}.json"
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                return PatientSchema(**schema_data)
        
        # Load most recent schema
        schema_files = list(self.schemas_directory.glob("*.json"))
        if schema_files:
            latest_schema = max(schema_files, key=lambda f: f.stat().st_mtime)
            with open(latest_schema, 'r') as f:
                schema_data = json.load(f)
            logger.info(f"Using schema: {latest_schema.stem}")
            return PatientSchema(**schema_data)
        
        return None
    
    def _extract_document_text(self, document_path: str) -> str:
        """Extract text from document using available services"""
        try:
            # Try parsing service first
            parsing_result = self.parsing_service.parse_document(document_path)
            if isinstance(parsing_result, str) and parsing_result.strip():
                return parsing_result
            
            # Fallback to OCR
            if document_path.lower().endswith('.pdf'):
                ocr_result = self.ocr_service.perform_ocr_on_pdf(document_path)
            else:
                ocr_result = self.ocr_service.perform_ocr_on_image(document_path)
                
            if ocr_result.get("success") and ocr_result.get("text"):
                return ocr_result["text"]
            
        except Exception as e:
            logger.error(f"Error extracting document text: {e}")
        
        return ""
    
    def _extract_fields_with_schema(self, document_text: str, schema: PatientSchema, 
                                  document_path: str) -> List[ExtractedField]:
        """Extract fields from document text using schema definition"""
        extracted_fields = []
        
        # Create extraction prompt for LLM
        prompt = self._create_extraction_prompt(schema, document_text)
        
        try:
            # Use LLM for intelligent extraction
            llm_response = self.llm_service.generate_response(prompt)
            
            if llm_response:
                extracted_fields = self._parse_extraction_results(
                    llm_response, schema
                )
        
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
        
        # Fallback: Rule-based extraction for missing fields
        if len(extracted_fields) < len(schema.fields) * 0.5:  # If less than 50% extracted
            logger.info("Using fallback rule-based extraction")
            fallback_fields = self._rule_based_extraction(document_text, schema)
            
            # Merge results, prioritizing LLM results
            field_names = {f.name for f in extracted_fields}
            for fallback_field in fallback_fields:
                if fallback_field.name not in field_names:
                    extracted_fields.append(fallback_field)
        
        return extracted_fields
    
    def _create_extraction_prompt(self, schema: PatientSchema, document_text: str) -> str:
        """Create a detailed prompt for LLM-based extraction"""
        
        field_descriptions = []
        for field_name, field_config in schema.fields.items():
            desc = f"- {field_name} ({field_config['type']}): {field_config['description']}"
            if field_config.get('alternative_names'):
                alt_names = field_config['alternative_names'][:3]  # Limit to first 3
                desc += f" [Also: {', '.join(alt_names)}]"
            field_descriptions.append(desc)
        
        prompt = f"""
Extract patient information from this document. Find values for these fields:

{chr(10).join(field_descriptions)}

Document Text:
{document_text[:8000]}

Instructions:
1. Extract exact values as they appear in the document
2. For dates, prefer YYYY-MM-DD format but preserve original if unclear
3. For phone numbers, preserve original formatting
4. For lists (allergies, medications), separate items with commas
5. If field not found, return "NOT_FOUND"
6. If field unclear/partial, return "UNCLEAR: [what you can read]"
7. Provide confidence 0.0-1.0 for each field

Return ONLY valid JSON in this format:
{{
    "field_name": {{
        "value": "extracted_value_or_NOT_FOUND_or_UNCLEAR",
        "confidence": 0.95,
        "source_text": "relevant snippet from document"
    }}
}}

Important: Return ONLY the JSON object, no additional text.
"""
        return prompt
    
    def _parse_extraction_results(self, llm_results: Any, schema: PatientSchema) -> List[ExtractedField]:
        """Parse LLM extraction results into ExtractedField objects"""
        extracted_fields = []
        
        try:
            # Handle different response formats
            if isinstance(llm_results, str):
                llm_results = json.loads(llm_results)
            
            if not isinstance(llm_results, dict):
                logger.warning("LLM results not in expected format")
                return extracted_fields
            
            for field_name, field_config in schema.fields.items():
                if field_name in llm_results:
                    result = llm_results[field_name]
                    
                    if isinstance(result, dict):
                        value = result.get("value", "NOT_FOUND")
                        confidence = float(result.get("confidence", 0.0))
                        source_text = result.get("source_text", "")
                    else:
                        # Handle simple value format
                        value = str(result)
                        confidence = 0.5
                        source_text = ""
                    
                    # Determine validation status
                    validation_status = "valid"
                    if value == "NOT_FOUND":
                        validation_status = "missing"
                        value = None
                    elif value.startswith("UNCLEAR"):
                        validation_status = "unclear"
                    elif not self._validate_field_value(value, field_config):
                        validation_status = "invalid"
                    
                    extracted_field = ExtractedField(
                        name=field_name,
                        value=value,
                        field_type=field_config.get("type", "string"),
                        confidence=confidence,
                        source_location=source_text,
                        validation_status=validation_status
                    )
                    
                    extracted_fields.append(extracted_field)
                else:
                    # Field not found in results
                    extracted_field = ExtractedField(
                        name=field_name,
                        value=None,
                        field_type=field_config.get("type", "string"),
                        confidence=0.0,
                        validation_status="missing"
                    )
                    extracted_fields.append(extracted_field)
        
        except Exception as e:
            logger.error(f"Error parsing extraction results: {e}")
        
        return extracted_fields
    
    def _rule_based_extraction(self, document_text: str, schema: PatientSchema) -> List[ExtractedField]:
        """Fallback rule-based extraction using regex patterns"""
        extracted_fields = []
        
        # Common extraction patterns
        patterns = {
            "phone": r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}",
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "date": r"\d{1,2}[/-]\d{1,2}[/-]\d{4}",
            "ssn": r"\d{3}-?\d{2}-?\d{4}"
        }
        
        for field_name, field_config in schema.fields.items():
            field_type = field_config.get("type", "string")
            
            # Try pattern matching for specific types
            if field_type in patterns:
                matches = re.findall(patterns[field_type], document_text)
                if matches:
                    value = matches[0]
                    confidence = 0.7
                    
                    extracted_field = ExtractedField(
                        name=field_name,
                        value=value,
                        field_type=field_type,
                        confidence=confidence,
                        validation_status="valid"
                    )
                    extracted_fields.append(extracted_field)
                    continue
            
            # Try searching by alternative names
            alternative_names = field_config.get("alternative_names", [])
            for alt_name in alternative_names:
                # Look for pattern: "field_name: value" or "field_name value"
                patterns_to_try = [
                    rf"{re.escape(alt_name)}\s*:?\s*([^\n\r;,]+)",
                    rf"{re.escape(alt_name)}\s+([^\n\r;,]+)",
                    rf"^{re.escape(alt_name)}\s*(.+)$"
                ]
                
                for pattern in patterns_to_try:
                    match = re.search(pattern, document_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value = match.group(1).strip()
                        # Clean up common artifacts
                        value = re.sub(r'^[:\-_\s]+|[:\-_\s]+$', '', value)
                        
                        if value and len(value) > 1:  # Valid extraction
                            confidence = 0.6
                            
                            extracted_field = ExtractedField(
                                name=field_name,
                                value=value,
                                field_type=field_type,
                                confidence=confidence,
                                validation_status="valid"
                            )
                            extracted_fields.append(extracted_field)
                            break
                
                if any(f.name == field_name for f in extracted_fields):
                    break  # Found this field, move to next
        
        return extracted_fields
    
    def _validate_field_value(self, value: str, field_config: Dict) -> bool:
        """Validate extracted field value against schema configuration"""
        if not value or value in ["NOT_FOUND", ""] or value.startswith("UNCLEAR"):
            return False
        
        validation_pattern = field_config.get("validation_pattern")
        if validation_pattern:
            return bool(re.match(validation_pattern, value))
        
        return True
    
    def _generate_output_document(self, fields: List[ExtractedField], schema: PatientSchema,
                                document_path: str, output_format: str) -> str:
        """Generate clean output document with extracted data"""
        
        if output_format.lower() == "json":
            return self._generate_json_output(fields, schema, document_path)
        else:
            return self._generate_markdown_output(fields, schema, document_path)
    
    def _generate_json_output(self, fields: List[ExtractedField], schema: PatientSchema,
                            document_path: str) -> str:
        """Generate JSON output document"""
        output_data = {
            "extraction_metadata": {
                "source_document": str(document_path),
                "schema_used": schema.schema_name,
                "extraction_date": datetime.now().isoformat(),
                "total_fields": len(schema.fields),
                "extracted_fields": len([f for f in fields if f.value is not None])
            },
            "patient_data": {}
        }
        
        for field in fields:
            output_data["patient_data"][field.name] = {
                "value": field.value,
                "confidence": field.confidence,
                "status": field.validation_status
            }
        
        return json.dumps(output_data, indent=2)
    
    def _generate_markdown_output(self, fields: List[ExtractedField], schema: PatientSchema,
                                document_path: str) -> str:
        """Generate Markdown output document"""
        
        md_content = f"""# Patient Information Report

**Source Document:** {Path(document_path).name}  
**Extraction Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Schema Used:** {schema.schema_name}

## Extracted Patient Data

"""
        
        # Group fields by category for better organization
        demographic_fields = []
        contact_fields = []
        medical_fields = []
        insurance_fields = []
        other_fields = []
        
        for field in fields:
            field_name = field.name.lower()
            if any(term in field_name for term in ['name', 'birth', 'dob', 'gender', 'sex', 'age']):
                demographic_fields.append(field)
            elif any(term in field_name for term in ['phone', 'email', 'address', 'contact', 'emergency']):
                contact_fields.append(field)
            elif any(term in field_name for term in ['allerg', 'medical', 'history', 'medication', 'diagnosis']):
                medical_fields.append(field)
            elif any(term in field_name for term in ['insurance', 'member', 'policy', 'group']):
                insurance_fields.append(field)
            else:
                other_fields.append(field)
        
        def format_field_section(section_title: str, field_list: List[ExtractedField]):
            if not field_list:
                return ""
            
            content = f"### {section_title}\n\n"
            for field in field_list:
                # Status icon based on validation
                if field.validation_status == "valid":
                    status_icon = "✅"
                elif field.validation_status == "unclear":
                    status_icon = "⚠️"
                else:
                    status_icon = "❌"
                
                # Format value display
                if field.value is not None:
                    value_display = str(field.value)
                    confidence_display = f" (confidence: {field.confidence:.1f})"
                else:
                    value_display = "*[NOT FOUND]*"
                    confidence_display = ""
                
                # Clean field name for display
                display_name = field.name.replace('_', ' ').title()
                
                content += f"* **{display_name}:** {value_display}{confidence_display} {status_icon}\n"
            
            return content + "\n"
        
        # Add sections
        md_content += format_field_section("Demographics", demographic_fields)
        md_content += format_field_section("Contact Information", contact_fields)
        md_content += format_field_section("Medical Information", medical_fields)
        md_content += format_field_section("Insurance Information", insurance_fields)
        md_content += format_field_section("Other Information", other_fields)
        
        # Add extraction summary
        total_fields = len(fields)
        successful_extractions = len([f for f in fields if f.value is not None])
        success_rate = (successful_extractions / total_fields) * 100 if total_fields > 0 else 0
        
        md_content += f"""---

### Extraction Summary

* **Total Fields:** {total_fields}
* **Successfully Extracted:** {successful_extractions}
* **Success Rate:** {success_rate:.1f}%
* **Schema Used:** {schema.schema_name}

*Report generated automatically by PatientDataExtractor*
"""
        
        return md_content
    
    def _calculate_success_rate(self, fields: List[ExtractedField], schema: PatientSchema) -> float:
        """Calculate extraction success rate"""
        total_fields = len(schema.fields)
        successful_extractions = len([f for f in fields if f.value is not None])
        return (successful_extractions / total_fields) * 100 if total_fields > 0 else 0
    
    def _save_extraction_results(self, results: Dict[str, Any], document_path: str):
        """Save extraction results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_name = Path(document_path).stem
        results_file = self.output_directory / f"extraction_{doc_name}_{timestamp}.json"
        
        # Also save the markdown output as a separate file
        if "output_document" in results:
            md_file = self.output_directory / f"report_{doc_name}_{timestamp}.md"
            with open(md_file, 'w') as f:
                f.write(results["output_document"])
            logger.info(f"Markdown report saved to: {md_file}")
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Extraction results saved to: {results_file}")
    
    def list_schemas(self) -> List[str]:
        """List available schemas"""
        schema_files = list(self.schemas_directory.glob("*.json"))
        return [f.stem for f in schema_files]
    
    def get_schema_info(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific schema"""
        schema_file = self.schemas_directory / f"{schema_name}.json"
        if schema_file.exists():
            with open(schema_file, 'r') as f:
                return json.load(f)
        return None


# CLI interface
def main():
    """Command line interface for patient data extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Patient Data Extractor")
    parser.add_argument("command", choices=["analyze-form", "extract-data", "list-schemas", "schema-info"], 
                       help="Command to execute")
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--schema-name", help="Schema name to use")
    parser.add_argument("--output-format", choices=["json", "markdown"], 
                       default="markdown", help="Output format for extraction")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize extractor
    extractor = PatientDataExtractor()
    
    try:
        if args.command == "analyze-form":
            if not args.input:
                print("Error: --input is required for analyze-form command")
                return
            
            # Analyze blank form to generate schema
            schema = extractor.analyze_blank_form(args.input, args.schema_name)
            print(f"\n✅ Schema generated successfully!")
            print(f"   Name: {schema.schema_name}")
            print(f"   Fields: {len(schema.fields)}")
            print(f"   Description: {schema.description}")
            
            # Show field summary
            print(f"\n📋 Fields identified:")
            for field_name, field_config in schema.fields.items():
                required_marker = "* " if field_config.get("required") else "  "
                print(f"   {required_marker}{field_name} ({field_config['type']}) - {field_config['description']}")
            
        elif args.command == "extract-data":
            if not args.input:
                print("Error: --input is required for extract-data command")
                return
            
            # Extract data from filled document
            results = extractor.extract_patient_data(
                args.input, 
                args.schema_name, 
                args.output_format
            )
            
            print(f"\n✅ Extraction completed!")
            print(f"   Success Rate: {results['success_rate']:.1f}%")
            print(f"   Fields Extracted: {results['extracted_count']}/{results['total_fields']}")
            print(f"   Schema Used: {results['schema_used']}")
            
            print(f"\n📄 Generated Report:")
            print("=" * 80)
            print(results['output_document'])
            
        elif args.command == "list-schemas":
            # List available schemas
            schemas = extractor.list_schemas()
            if schemas:
                print(f"\n📚 Available schemas ({len(schemas)}):")
                for schema in schemas:
                    print(f"   • {schema}")
            else:
                print("\n❌ No schemas found. Use 'analyze-form' to create one.")
                
        elif args.command == "schema-info":
            if not args.schema_name:
                print("Error: --schema-name is required for schema-info command")
                return
                
            # Show schema details
            schema_info = extractor.get_schema_info(args.schema_name)
            if schema_info:
                print(f"\n📋 Schema: {args.schema_name}")
                print(f"   Description: {schema_info['description']}")
                print(f"   Version: {schema_info['version']}")
                print(f"   Created: {schema_info['created_date']}")
                print(f"   Source: {schema_info['source_document']}")
                print(f"   Fields: {len(schema_info['fields'])}")
                
                print(f"\n📝 Field Details:")
                for field_name, field_config in schema_info['fields'].items():
                    required = "Required" if field_config.get("required") else "Optional"
                    print(f"   • {field_name} ({field_config['type']}) - {required}")
                    print(f"     {field_config['description']}")
            else:
                print(f"❌ Schema '{args.schema_name}' not found")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Command failed: {e}", exc_info=True)


if __name__ == "__main__":
    main() 