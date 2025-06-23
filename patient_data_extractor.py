#!/usr/bin/env python3
"""
Patient Data Extractor Module

This module provides functionality to:
1. Analyze blank forms and generate extraction schemas
2. Extract structured patient data from scanned documents
3. Generate clean output documents with extracted information

Author: AI Assistant
Date: 2024
"""

import json
import yaml
import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import re
import os
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Import existing services
from src.services.ocr_service import OCRService
from src.services.llm_service import LLMService
from src.services.parsing_service import ParsingService

logger = logging.getLogger(__name__)

class FieldType(Enum):
    """Enumeration of supported field types"""
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    TEXT = "text"
    LIST_OF_STRINGS = "list_of_strings"
    BOOLEAN = "boolean"
    MEDICAL_CODE = "medical_code"

@dataclass
class ExtractedField:
    """Represents an extracted field with metadata"""
    name: str
    value: Any
    field_type: FieldType
    confidence: float
    source_location: Optional[str] = None
    validation_status: str = "valid"  # valid, invalid, unclear, missing

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
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
        self.parsing_service = ParsingService()
        
        # Schema storage
        self.schemas_directory = self.output_directory / "schemas"
        self.schemas_directory.mkdir(exist_ok=True)
        
        logger.info(f"PatientDataExtractor initialized with output directory: {self.output_directory}")
    
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
            "layout_analysis": {},
            "visual_elements": []
        }
        
        try:
            # Parse document using existing parsing service
            parsing_result = self.parsing_service.parse_document(form_path)
            form_data["text_content"] = parsing_result.get("extracted_text", "")
            
            # Analyze PDF form fields if it's a PDF
            if form_path.lower().endswith('.pdf'):
                pdf_fields = self._analyze_pdf_form_fields(form_path)
                form_data["form_fields"] = pdf_fields
            
            # OCR analysis for visual elements
            ocr_result = self.ocr_service.extract_text(form_path)
            if ocr_result.get("success"):
                form_data["visual_elements"] = ocr_result.get("regions", [])
            
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
                        "required": bool(widget.field_flags & 2),  # Required flag
                    }
                    fields.append(field_info)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error analyzing PDF form fields: {e}")
        
        return fields
    
    def _generate_schema_with_llm(self, form_structure: Dict[str, Any], form_path: str) -> Dict[str, Dict[str, Any]]:
        """Use LLM to analyze form structure and generate comprehensive schema"""
        
        # Prepare context for LLM
        context = {
            "form_text": form_structure.get("text_content", "")[:5000],  # Limit text length
            "form_fields": form_structure.get("form_fields", []),
            "visual_elements": len(form_structure.get("visual_elements", [])),
            "document_type": "patient_intake_form"
        }
        
        # LLM prompt for schema generation
        prompt = f"""
Analyze this blank patient form and generate a comprehensive data extraction schema.

Form Text Content:
{context['form_text']}

Form Fields Found: {len(context['form_fields'])}
Visual Elements: {context['visual_elements']}

Please identify all the patient information fields that would typically need to be extracted from completed versions of this form. For each field, provide:

1. Field name (snake_case)
2. Data type (string, date, number, phone, email, address, text, list_of_strings, boolean, medical_code)
3. Description
4. Whether it's required
5. Validation pattern (if applicable)
6. Alternative names/labels that might be used

Focus on common patient intake fields like:
- Demographics (name, DOB, gender, address, phone, email)
- Medical information (allergies, medications, medical history)
- Insurance information
- Emergency contacts
- Consent and signatures

Return your response as a valid JSON object with this structure:
{{
    "field_name": {{
        "type": "string|date|number|phone|email|address|text|list_of_strings|boolean|medical_code",
        "description": "Description of the field",
        "required": true/false,
        "validation_pattern": "regex pattern if applicable",
        "alternative_names": ["list", "of", "possible", "labels"],
        "examples": ["example1", "example2"]
    }}
}}
"""
        
        try:
            # Call LLM service
            llm_result = self.llm_service.extract_entities(
                document_text=context['form_text'],
                schema_name="schema_generation",
                custom_prompt=prompt
            )
            
            if llm_result.get("success") and llm_result.get("extracted_entities"):
                # Parse the LLM response
                schema_fields = self._parse_llm_schema_response(llm_result["extracted_entities"])
                return schema_fields
            
        except Exception as e:
            logger.error(f"Error in LLM schema generation: {e}")
        
        # Fallback: Generate basic schema from form fields
        return self._generate_fallback_schema(form_structure)
    
    def _parse_llm_schema_response(self, llm_response: Dict) -> Dict[str, Dict[str, Any]]:
        """Parse and validate LLM response for schema generation"""
        schema_fields = {}
        
        try:
            # If the response is already structured
            if isinstance(llm_response, dict):
                for field_name, field_config in llm_response.items():
                    if isinstance(field_config, dict):
                        schema_fields[field_name] = {
                            "type": field_config.get("type", "string"),
                            "description": field_config.get("description", ""),
                            "required": field_config.get("required", False),
                            "validation_pattern": field_config.get("validation_pattern"),
                            "alternative_names": field_config.get("alternative_names", []),
                            "examples": field_config.get("examples", [])
                        }
            
        except Exception as e:
            logger.error(f"Error parsing LLM schema response: {e}")
        
        return schema_fields
    
    def _generate_fallback_schema(self, form_structure: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Generate a basic fallback schema if LLM analysis fails"""
        schema_fields = {}
        
        # Common patient intake fields
        common_fields = {
            "patient_first_name": {
                "type": "string",
                "description": "Patient's first name",
                "required": True,
                "alternative_names": ["first name", "given name", "fname"],
                "examples": ["John", "Jane"]
            },
            "patient_last_name": {
                "type": "string", 
                "description": "Patient's last name",
                "required": True,
                "alternative_names": ["last name", "surname", "family name", "lname"],
                "examples": ["Smith", "Johnson"]
            },
            "date_of_birth": {
                "type": "date",
                "description": "Patient's date of birth",
                "required": True,
                "validation_pattern": r"\d{1,2}[/-]\d{1,2}[/-]\d{4}",
                "alternative_names": ["DOB", "birth date", "birthdate"],
                "examples": ["01/15/1985", "1985-01-15"]
            },
            "phone_number": {
                "type": "phone",
                "description": "Patient's phone number",
                "required": True,
                "validation_pattern": r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}",
                "alternative_names": ["phone", "telephone", "mobile"],
                "examples": ["(555) 123-4567", "555-123-4567"]
            },
            "email_address": {
                "type": "email",
                "description": "Patient's email address",
                "required": False,
                "validation_pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "alternative_names": ["email", "e-mail"],
                "examples": ["patient@email.com"]
            },
            "address": {
                "type": "address",
                "description": "Patient's address",
                "required": True,
                "alternative_names": ["home address", "street address", "mailing address"],
                "examples": ["123 Main St, Anytown, ST 12345"]
            },
            "allergies": {
                "type": "list_of_strings",
                "description": "Patient's known allergies",
                "required": False,
                "alternative_names": ["allergy", "allergic to", "drug allergies"],
                "examples": ["Penicillin", "Peanuts", "None known"]
            },
            "medical_history": {
                "type": "text",
                "description": "Patient's medical history summary",
                "required": False,
                "alternative_names": ["past medical history", "medical background", "health history"],
                "examples": ["Hypertension, Diabetes Type 2"]
            },
            "emergency_contact_name": {
                "type": "string",
                "description": "Emergency contact person's name",
                "required": False,
                "alternative_names": ["emergency contact", "in case of emergency", "ICE contact"],
                "examples": ["John Smith (spouse)"]
            },
            "emergency_contact_phone": {
                "type": "phone",
                "description": "Emergency contact phone number",
                "required": False,
                "validation_pattern": r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}",
                "alternative_names": ["emergency phone", "emergency number"],
                "examples": ["(555) 987-6543"]
            }
        }
        
        # Add fields from form analysis if available
        form_fields = form_structure.get("form_fields", [])
        for form_field in form_fields:
            field_name = form_field.get("name", "").lower().replace(" ", "_")
            if field_name and field_name not in common_fields:
                schema_fields[field_name] = {
                    "type": "string",
                    "description": f"Form field: {form_field.get('name', '')}",
                    "required": form_field.get("required", False),
                    "alternative_names": [form_field.get("name", "")],
                    "examples": []
                }
        
        # Merge common fields with form-specific fields
        schema_fields.update(common_fields)
        
        return schema_fields
    
    def _save_schema(self, schema: PatientSchema):
        """Save schema to file"""
        schema_file = self.schemas_directory / f"{schema.schema_name}.json"
        
        with open(schema_file, 'w') as f:
            json.dump(asdict(schema), f, indent=2)
        
        logger.info(f"Schema saved to: {schema_file}")
    
    def extract_patient_data(self, document_path: str, schema_name: str = None, 
                           output_format: str = "json") -> Dict[str, Any]:
        """
        Extract patient data from a filled document using a schema
        
        Args:
            document_path: Path to the filled patient document
            schema_name: Name of the schema to use (if None, tries to auto-detect)
            output_format: Output format ('json', 'markdown', 'yaml')
            
        Returns:
            Dictionary containing extraction results
        """
        logger.info(f"Extracting patient data from: {document_path}")
        
        # Load or detect schema
        schema = self._load_or_detect_schema(schema_name, document_path)
        if not schema:
            raise ValueError(f"No suitable schema found for document: {document_path}")
        
        # Extract text from document
        document_text = self._extract_document_text(document_path)
        
        # Extract data using schema
        extracted_fields = self._extract_fields_with_schema(document_text, schema, document_path)
        
        # Validate extracted data
        validated_fields = self._validate_extracted_fields(extracted_fields, schema)
        
        # Generate output document
        output_doc = self._generate_output_document(validated_fields, schema, document_path, output_format)
        
        # Save results
        results = {
            "document_path": document_path,
            "schema_used": schema.schema_name,
            "extraction_timestamp": datetime.now().isoformat(),
            "extracted_fields": {field.name: asdict(field) for field in validated_fields},
            "output_document": output_doc,
            "success_rate": self._calculate_success_rate(validated_fields, schema)
        }
        
        self._save_extraction_results(results, document_path)
        
        return results
    
    def _load_or_detect_schema(self, schema_name: str, document_path: str) -> Optional[PatientSchema]:
        """Load specified schema or try to detect appropriate schema"""
        
        if schema_name:
            # Load specific schema
            schema_file = self.schemas_directory / f"{schema_name}.json"
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                return PatientSchema(**schema_data)
        
        # Try to auto-detect schema
        # For now, load the most recent schema
        schema_files = list(self.schemas_directory.glob("*.json"))
        if schema_files:
            # Sort by modification time and use the most recent
            latest_schema = max(schema_files, key=os.path.getmtime)
            with open(latest_schema, 'r') as f:
                schema_data = json.load(f)
            logger.info(f"Auto-detected schema: {latest_schema.stem}")
            return PatientSchema(**schema_data)
        
        return None
    
    def _extract_document_text(self, document_path: str) -> str:
        """Extract text from document using available services"""
        try:
            # Try parsing service first
            parsing_result = self.parsing_service.parse_document(document_path)
            if parsing_result.get("extracted_text"):
                return parsing_result["extracted_text"]
            
            # Fallback to OCR
            ocr_result = self.ocr_service.extract_text(document_path)
            if ocr_result.get("success") and ocr_result.get("extracted_text"):
                return ocr_result["extracted_text"]
            
        except Exception as e:
            logger.error(f"Error extracting document text: {e}")
        
        return ""
    
    def _extract_fields_with_schema(self, document_text: str, schema: PatientSchema, 
                                  document_path: str) -> List[ExtractedField]:
        """Extract fields from document text using schema definition"""
        extracted_fields = []
        
        # Prepare context for LLM extraction
        schema_context = {
            "fields": schema.fields,
            "document_text": document_text[:10000],  # Limit text for LLM
            "document_type": "patient_document"
        }
        
        # Create extraction prompt
        prompt = self._create_extraction_prompt(schema, document_text)
        
        try:
            # Use LLM for intelligent extraction
            llm_result = self.llm_service.extract_entities(
                document_text=document_text,
                schema_name="patient_extraction",
                custom_prompt=prompt
            )
            
            if llm_result.get("success") and llm_result.get("extracted_entities"):
                extracted_fields = self._parse_extraction_results(
                    llm_result["extracted_entities"], schema
                )
        
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
        
        # Fallback: Rule-based extraction
        if not extracted_fields:
            extracted_fields = self._rule_based_extraction(document_text, schema)
        
        return extracted_fields
    
    def _create_extraction_prompt(self, schema: PatientSchema, document_text: str) -> str:
        """Create a detailed prompt for LLM-based extraction"""
        
        field_descriptions = []
        for field_name, field_config in schema.fields.items():
            desc = f"- {field_name} ({field_config['type']}): {field_config['description']}"
            if field_config.get('alternative_names'):
                desc += f" [Also known as: {', '.join(field_config['alternative_names'])}]"
            field_descriptions.append(desc)
        
        prompt = f"""
Extract patient information from the following document text. Please find and extract values for these specific fields:

{chr(10).join(field_descriptions)}

Document Text:
{document_text[:8000]}

Instructions:
1. Extract exact values as they appear in the document
2. For dates, use format YYYY-MM-DD if possible
3. For phone numbers, preserve the original formatting
4. For lists (like allergies), separate multiple items with commas
5. If a field is not found, mark it as "NOT_FOUND"
6. If a field is unclear or partially readable, mark it as "UNCLEAR" and include what you can read
7. Provide confidence scores (0.0-1.0) for each extraction

Return results as JSON in this format:
{{
    "field_name": {{
        "value": "extracted_value_or_NOT_FOUND_or_UNCLEAR",
        "confidence": 0.95,
        "source_text": "relevant text snippet from document"
    }}
}}
"""
        return prompt
    
    def _parse_extraction_results(self, llm_results: Dict, schema: PatientSchema) -> List[ExtractedField]:
        """Parse LLM extraction results into ExtractedField objects"""
        extracted_fields = []
        
        for field_name, field_config in schema.fields.items():
            if field_name in llm_results:
                result = llm_results[field_name]
                
                value = result.get("value", "NOT_FOUND")
                confidence = float(result.get("confidence", 0.0))
                source_text = result.get("source_text", "")
                
                # Determine validation status
                validation_status = "valid"
                if value == "NOT_FOUND":
                    validation_status = "missing"
                elif value == "UNCLEAR":
                    validation_status = "unclear"
                elif not self._validate_field_value(value, field_config):
                    validation_status = "invalid"
                
                # Determine field type
                field_type = FieldType(field_config.get("type", "string"))
                
                extracted_field = ExtractedField(
                    name=field_name,
                    value=value if value not in ["NOT_FOUND", "UNCLEAR"] else None,
                    field_type=field_type,
                    confidence=confidence,
                    source_location=source_text,
                    validation_status=validation_status
                )
                
                extracted_fields.append(extracted_field)
        
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
            field_type = FieldType(field_config.get("type", "string"))
            
            # Try pattern matching
            pattern_key = field_type.value if field_type.value in patterns else None
            
            if pattern_key:
                matches = re.findall(patterns[pattern_key], document_text)
                if matches:
                    value = matches[0]  # Take first match
                    confidence = 0.7  # Medium confidence for pattern matching
                    
                    extracted_field = ExtractedField(
                        name=field_name,
                        value=value,
                        field_type=field_type,
                        confidence=confidence,
                        validation_status="valid"
                    )
                    extracted_fields.append(extracted_field)
                    continue
            
            # Try searching for field by alternative names
            alternative_names = field_config.get("alternative_names", [])
            for alt_name in alternative_names:
                # Look for the field name followed by a colon and value
                pattern = rf"{re.escape(alt_name)}\s*:?\s*([^\n\r]+)"
                match = re.search(pattern, document_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    confidence = 0.6  # Lower confidence for name-based matching
                    
                    extracted_field = ExtractedField(
                        name=field_name,
                        value=value,
                        field_type=field_type,
                        confidence=confidence,
                        validation_status="valid"
                    )
                    extracted_fields.append(extracted_field)
                    break
        
        return extracted_fields
    
    def _validate_field_value(self, value: str, field_config: Dict) -> bool:
        """Validate extracted field value against schema configuration"""
        if not value or value in ["NOT_FOUND", "UNCLEAR"]:
            return False
        
        validation_pattern = field_config.get("validation_pattern")
        if validation_pattern:
            return bool(re.match(validation_pattern, value))
        
        return True
    
    def _validate_extracted_fields(self, extracted_fields: List[ExtractedField], 
                                 schema: PatientSchema) -> List[ExtractedField]:
        """Validate and clean extracted fields"""
        validated_fields = []
        
        for field in extracted_fields:
            # Additional validation logic can be added here
            validated_fields.append(field)
        
        return validated_fields
    
    def _generate_output_document(self, fields: List[ExtractedField], schema: PatientSchema,
                                document_path: str, output_format: str) -> str:
        """Generate clean output document with extracted data"""
        
        if output_format.lower() == "json":
            return self._generate_json_output(fields, schema, document_path)
        elif output_format.lower() == "markdown":
            return self._generate_markdown_output(fields, schema, document_path)
        elif output_format.lower() == "yaml":
            return self._generate_yaml_output(fields, schema, document_path)
        else:
            return self._generate_json_output(fields, schema, document_path)
    
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
        
        # Group fields by type for better organization
        demographic_fields = []
        medical_fields = []
        contact_fields = []
        other_fields = []
        
        for field in fields:
            if field.name in ['patient_first_name', 'patient_last_name', 'date_of_birth', 'gender', 'address']:
                demographic_fields.append(field)
            elif field.name in ['allergies', 'medical_history', 'medications', 'diagnosis']:
                medical_fields.append(field)
            elif field.name in ['phone_number', 'email_address', 'emergency_contact_name', 'emergency_contact_phone']:
                contact_fields.append(field)
            else:
                other_fields.append(field)
        
        if demographic_fields:
            md_content += "### Demographics\n\n"
            for field in demographic_fields:
                status_icon = "✅" if field.validation_status == "valid" else "⚠️" if field.validation_status == "unclear" else "❌"
                value_display = field.value if field.value is not None else "[NOT FOUND]"
                md_content += f"* **{field.name.replace('_', ' ').title()}:** {value_display} {status_icon}\n"
            md_content += "\n"
        
        if contact_fields:
            md_content += "### Contact Information\n\n"
            for field in contact_fields:
                status_icon = "✅" if field.validation_status == "valid" else "⚠️" if field.validation_status == "unclear" else "❌"
                value_display = field.value if field.value is not None else "[NOT FOUND]"
                md_content += f"* **{field.name.replace('_', ' ').title()}:** {value_display} {status_icon}\n"
            md_content += "\n"
        
        if medical_fields:
            md_content += "### Medical Information\n\n"
            for field in medical_fields:
                status_icon = "✅" if field.validation_status == "valid" else "⚠️" if field.validation_status == "unclear" else "❌"
                value_display = field.value if field.value is not None else "[NOT FOUND]"
                md_content += f"* **{field.name.replace('_', ' ').title()}:** {value_display} {status_icon}\n"
            md_content += "\n"
        
        if other_fields:
            md_content += "### Other Information\n\n"
            for field in other_fields:
                status_icon = "✅" if field.validation_status == "valid" else "⚠️" if field.validation_status == "unclear" else "❌"
                value_display = field.value if field.value is not None else "[NOT FOUND]"
                md_content += f"* **{field.name.replace('_', ' ').title()}:** {value_display} {status_icon}\n"
            md_content += "\n"
        
        # Add extraction summary
        total_fields = len(fields)
        successful_extractions = len([f for f in fields if f.value is not None])
        success_rate = (successful_extractions / total_fields) * 100 if total_fields > 0 else 0
        
        md_content += f"""---

### Extraction Summary

* **Total Fields:** {total_fields}
* **Successfully Extracted:** {successful_extractions}
* **Success Rate:** {success_rate:.1f}%

*Report generated automatically by PatientDataExtractor*
"""
        
        return md_content
    
    def _generate_yaml_output(self, fields: List[ExtractedField], schema: PatientSchema,
                            document_path: str) -> str:
        """Generate YAML output document"""
        output_data = {
            "extraction_metadata": {
                "source_document": str(document_path),
                "schema_used": schema.schema_name,
                "extraction_date": datetime.now().isoformat()
            },
            "patient_data": {}
        }
        
        for field in fields:
            output_data["patient_data"][field.name] = field.value
        
        return yaml.dump(output_data, default_flow_style=False, sort_keys=False)
    
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


def main():
    """CLI interface for patient data extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Patient Data Extractor")
    parser.add_argument("command", choices=["analyze-form", "extract-data", "list-schemas"], 
                       help="Command to execute")
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--schema-name", help="Schema name")
    parser.add_argument("--output-format", choices=["json", "markdown", "yaml"], 
                       default="markdown", help="Output format for extraction")
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = PatientDataExtractor()
    
    if args.command == "analyze-form":
        # Analyze blank form to generate schema
        schema = extractor.analyze_blank_form(args.input, args.schema_name)
        print(f"Schema generated: {schema.schema_name}")
        print(f"Fields identified: {len(schema.fields)}")
        
    elif args.command == "extract-data":
        # Extract data from filled document
        results = extractor.extract_patient_data(
            args.input, 
            args.schema_name, 
            args.output_format
        )
        print(f"Extraction completed with {results['success_rate']:.1f}% success rate")
        print(f"Output: \n{results['output_document']}")
        
    elif args.command == "list-schemas":
        # List available schemas
        schemas = extractor.list_schemas()
        print("Available schemas:")
        for schema in schemas:
            print(f"  - {schema}")


if __name__ == "__main__":
    main() 