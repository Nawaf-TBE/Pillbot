"""
Form Filler Service for PriorAuthAutomation

This module provides functionality to populate insurance prior authorization forms
based on extracted document entities and configurable form schemas.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

try:
    import fitz  # PyMuPDF for PDF form filling
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PyMuPDF not available. PDF generation will be disabled.")

# Configure logging
logger = logging.getLogger(__name__)

class FormFillerError(Exception):
    """Custom exception for form filling errors."""
    pass

class FormFillerService:
    """Service for filling out prior authorization forms based on extracted entities."""
    
    def __init__(self, schema_directory: Optional[str] = None):
        """
        Initialize the form filler service.
        
        Args:
            schema_directory: Path to directory containing form schemas (optional)
        """
        if schema_directory:
            self.schema_directory = Path(schema_directory)
        else:
            # Default to data directory relative to this file
            current_file = Path(__file__)
            self.schema_directory = current_file.parent.parent.parent / "data"
        
        self.loaded_schemas = {}
    
    def load_form_schema(self, schema_name: str) -> Dict[str, Any]:
        """
        Load a form schema from the schema directory.
        
        Args:
            schema_name: Name of the schema file (without .json extension)
            
        Returns:
            Dict containing the form schema
            
        Raises:
            FormFillerError: If schema file cannot be loaded
        """
        try:
            schema_path = self.schema_directory / f"{schema_name}.json"
            
            if not schema_path.exists():
                raise FormFillerError(f"Schema file not found: {schema_path}")
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            # Cache the loaded schema
            self.loaded_schemas[schema_name] = schema
            
            logger.info(f"Loaded form schema: {schema_name}")
            return schema
            
        except json.JSONDecodeError as e:
            raise FormFillerError(f"Invalid JSON in schema file {schema_name}: {e}")
        except Exception as e:
            raise FormFillerError(f"Error loading schema {schema_name}: {e}")
    
    def populate_form(self, extracted_entities: Dict[str, Any], form_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Populate a form structure based on extracted entities and form schema.
        
        Args:
            extracted_entities: Dictionary of entities extracted from the document
            form_schema: Schema defining the form structure and field mappings
            
        Returns:
            Dictionary representing the populated form
            
        Raises:
            FormFillerError: If form population fails
        """
        try:
            logger.info("Starting form population")
            
            # Validate schema structure
            self._validate_schema(form_schema)
            
            # Initialize populated form structure
            populated_form = {
                "form_metadata": {
                    "schema_name": form_schema.get("schema_name", "unknown"),
                    "schema_version": form_schema.get("schema_version", "1.0"),
                    "population_timestamp": datetime.now().isoformat(),
                    "populated_fields_count": 0,
                    "total_fields_count": 0,
                    "missing_fields": [],
                    "confidence_scores": {}
                },
                "form_data": {}
            }
            
            # Get field mappings from schema
            field_mappings = form_schema.get("field_mappings", {})
            form_structure = form_schema.get("form_structure", {})
            
            # Count total fields
            populated_form["form_metadata"]["total_fields_count"] = len(field_mappings)
            
            # Populate each field according to the schema
            for form_field, mapping_config in field_mappings.items():
                field_value, confidence = self._populate_field(
                    form_field, mapping_config, extracted_entities
                )
                
                # Store the populated value
                populated_form["form_data"][form_field] = {
                    "value": field_value,
                    "source": mapping_config.get("source_field", "unknown"),
                    "confidence": confidence,
                    "required": mapping_config.get("required", False),
                    "data_type": mapping_config.get("data_type", "string")
                }
                
                # Track metadata
                if field_value is not None and field_value != "":
                    populated_form["form_metadata"]["populated_fields_count"] += 1
                    populated_form["form_metadata"]["confidence_scores"][form_field] = confidence
                else:
                    if mapping_config.get("required", False):
                        populated_form["form_metadata"]["missing_fields"].append(form_field)
            
            # Apply conditional rules if specified in schema
            conditional_rules = form_schema.get("conditional_rules", {})
            if conditional_rules:
                logger.info("Applying conditional rules")
                populated_form = self._apply_conditional_rules(
                    populated_form, conditional_rules, extracted_entities, form_schema
                )
            
            # Apply form structure and formatting
            if form_structure:
                populated_form["form_sections"] = self._apply_form_structure(
                    populated_form["form_data"], form_structure
                )
            
            # Calculate overall form completion
            completion_rate = (
                populated_form["form_metadata"]["populated_fields_count"] / 
                populated_form["form_metadata"]["total_fields_count"]
            ) if populated_form["form_metadata"]["total_fields_count"] > 0 else 0
            
            populated_form["form_metadata"]["completion_rate"] = round(completion_rate, 2)
            
            logger.info(
                f"Form population completed: {populated_form['form_metadata']['populated_fields_count']}/"
                f"{populated_form['form_metadata']['total_fields_count']} fields "
                f"({completion_rate:.1%} completion)"
            )
            
            return populated_form
            
        except Exception as e:
            logger.error(f"Error populating form: {e}")
            raise FormFillerError(f"Form population failed: {e}")
    
    def _populate_field(self, form_field: str, mapping_config: Dict[str, Any], 
                       extracted_entities: Dict[str, Any]) -> tuple[Any, float]:
        """
        Populate a single form field based on its mapping configuration.
        
        Args:
            form_field: Name of the form field
            mapping_config: Configuration for how to map this field
            extracted_entities: Extracted entities from the document
            
        Returns:
            Tuple of (field_value, confidence_score)
        """
        try:
            # Get source field name
            source_field = mapping_config.get("source_field")
            if not source_field:
                return None, 0.0
            
            # Extract value from entities
            value = extracted_entities.get(source_field)
            
            # Apply transformations if specified
            if value is not None and "transformations" in mapping_config:
                value = self._apply_transformations(value, mapping_config["transformations"])
            
            # Apply validation if specified
            if value is not None and "validation" in mapping_config:
                is_valid = self._validate_field_value(value, mapping_config["validation"])
                if not is_valid:
                    logger.warning(f"Field {form_field} failed validation: {value}")
                    return None, 0.0
            
            # Apply default value if no value found
            if value is None or value == "":
                default_value = mapping_config.get("default_value")
                if default_value is not None:
                    value = default_value
            
            # Calculate confidence score
            confidence = self._calculate_field_confidence(value, mapping_config)
            
            return value, confidence
            
        except Exception as e:
            logger.warning(f"Error populating field {form_field}: {e}")
            return None, 0.0
    
    def _apply_conditional_rules(self, populated_form: Dict[str, Any], 
                               conditional_rules: Dict[str, Any], 
                               extracted_entities: Dict[str, Any],
                               form_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply conditional rules to the populated form.
        
        Args:
            populated_form: Current form data
            conditional_rules: Rules to apply
            extracted_entities: Original extracted entities
            form_schema: Full form schema
            
        Returns:
            Updated populated form
        """
        try:
            # Track conditional evaluations
            conditional_metadata = {
                "rules_evaluated": 0,
                "rules_triggered": 0,
                "llm_inferences": 0,
                "conditional_requirements_added": 0,
                "conditional_values_set": 0
            }
            
            # Process simple conditional rules
            simple_rules = conditional_rules.get("simple_rules", [])
            for rule in simple_rules:
                conditional_metadata["rules_evaluated"] += 1
                
                if self._evaluate_simple_rule(rule, populated_form["form_data"]):
                    conditional_metadata["rules_triggered"] += 1
                    self._apply_rule_actions(rule, populated_form, conditional_metadata)
            
            # Process complex inference rules (requiring LLM)
            complex_rules = conditional_rules.get("complex_inference_rules", [])
            for rule in complex_rules:
                conditional_metadata["rules_evaluated"] += 1
                
                if self._evaluate_complex_rule(rule, extracted_entities, populated_form):
                    conditional_metadata["rules_triggered"] += 1
                    conditional_metadata["llm_inferences"] += 1
                    self._apply_rule_actions(rule, populated_form, conditional_metadata)
            
            # Add conditional metadata to form
            populated_form["form_metadata"]["conditional_logic"] = conditional_metadata
            
            logger.info(f"Conditional rules: {conditional_metadata['rules_triggered']}/{conditional_metadata['rules_evaluated']} triggered")
            
            return populated_form
            
        except Exception as e:
            logger.error(f"Error applying conditional rules: {e}")
            # Don't fail the entire form population due to conditional rule errors
            populated_form["form_metadata"]["conditional_logic_error"] = str(e)
            return populated_form
    
    def _evaluate_simple_rule(self, rule: Dict[str, Any], form_data: Dict[str, Any]) -> bool:
        """
        Evaluate a simple conditional rule based on form field values.
        
        Args:
            rule: Rule configuration
            form_data: Current form data
            
        Returns:
            True if rule condition is met, False otherwise
        """
        try:
            condition = rule.get("condition", {})
            condition_type = condition.get("type", "equals")
            field_name = condition.get("field")
            expected_value = condition.get("value")
            
            if not field_name or field_name not in form_data:
                return False
            
            actual_value = form_data[field_name].get("value")
            
            if condition_type == "equals":
                return str(actual_value).lower() == str(expected_value).lower()
            elif condition_type == "not_equals":
                return str(actual_value).lower() != str(expected_value).lower()
            elif condition_type == "contains":
                return str(expected_value).lower() in str(actual_value).lower()
            elif condition_type == "not_empty":
                return actual_value is not None and str(actual_value).strip() != ""
            elif condition_type == "empty":
                return actual_value is None or str(actual_value).strip() == ""
            elif condition_type == "greater_than":
                try:
                    # Handle percentage values by removing % symbol
                    actual_num = str(actual_value).replace('%', '').strip()
                    expected_num = str(expected_value).replace('%', '').strip()
                    return float(actual_num) > float(expected_num)
                except (ValueError, TypeError):
                    return False
            elif condition_type == "less_than":
                try:
                    # Handle percentage values by removing % symbol
                    actual_num = str(actual_value).replace('%', '').strip()
                    expected_num = str(expected_value).replace('%', '').strip()
                    return float(actual_num) < float(expected_num)
                except (ValueError, TypeError):
                    return False
            elif condition_type == "regex":
                try:
                    return bool(re.search(str(expected_value), str(actual_value)))
                except re.error:
                    return False
            
            return False
            
        except Exception as e:
            logger.warning(f"Error evaluating simple rule: {e}")
            return False
    
    def _evaluate_complex_rule(self, rule: Dict[str, Any], 
                             extracted_entities: Dict[str, Any],
                             populated_form: Dict[str, Any]) -> bool:
        """
        Evaluate a complex rule that requires LLM inference.
        
        Args:
            rule: Rule configuration with LLM inference
            extracted_entities: Original extracted entities
            populated_form: Current form data
            
        Returns:
            True if rule condition is met based on LLM inference
        """
        try:
            # Import LLM service here to avoid circular imports
            try:
                from .llm_service import extract_entities_with_gemini, check_llm_availability
            except ImportError:
                logger.warning("LLM service not available for complex rule evaluation")
                return False
            
            if not check_llm_availability():
                logger.warning("LLM service not configured for complex rule evaluation")
                return False
            
            inference_config = rule.get("llm_inference", {})
            prompt_template = inference_config.get("prompt")
            context_fields = inference_config.get("context_fields", [])
            
            if not prompt_template:
                logger.warning("No prompt template specified for complex rule")
                return False
            
            # Build context from extracted entities and populated form
            context_data = {}
            
            # Add specified context fields from extracted entities
            for field in context_fields:
                if field in extracted_entities:
                    context_data[field] = extracted_entities[field]
            
            # Add relevant medical history context
            medical_context_fields = ["previous_medications_tried", "clinical_justification", 
                                    "primary_diagnosis", "medical_history"]
            for field in medical_context_fields:
                if field in extracted_entities:
                    context_data[field] = extracted_entities[field]
            
            # Format the prompt with context
            formatted_prompt = self._format_llm_prompt(prompt_template, context_data)
            
            logger.info(f"Evaluating complex rule with LLM: {rule.get('description', 'unnamed rule')}")
            
            # Call LLM for inference
            llm_result = extract_entities_with_gemini(formatted_prompt)
            
            # Extract the inference result
            entities = llm_result.get("extracted_entities", {})
            inference_field = inference_config.get("result_field", "inference_result")
            
            result = entities.get(inference_field, "").lower()
            
            # Determine if condition is met
            expected_result = inference_config.get("expected_result", "yes").lower()
            
            return result == expected_result
            
        except Exception as e:
            logger.error(f"Error evaluating complex rule: {e}")
            return False
    
    def _format_llm_prompt(self, prompt_template: str, context_data: Dict[str, Any]) -> str:
        """
        Format an LLM prompt template with context data.
        
        Args:
            prompt_template: Template string with placeholders
            context_data: Data to substitute into template
            
        Returns:
            Formatted prompt string
        """
        try:
            # Create context string
            context_lines = []
            for key, value in context_data.items():
                if value:
                    context_lines.append(f"{key}: {value}")
            
            context_string = "\n".join(context_lines)
            
            # Replace placeholders in template
            formatted_prompt = prompt_template.format(
                context=context_string,
                **context_data
            )
            
            return formatted_prompt
            
        except Exception as e:
            logger.warning(f"Error formatting LLM prompt: {e}")
            return prompt_template
    
    def _apply_rule_actions(self, rule: Dict[str, Any], 
                          populated_form: Dict[str, Any],
                          conditional_metadata: Dict[str, Any]) -> None:
        """
        Apply the actions specified in a triggered rule.
        
        Args:
            rule: Rule configuration with actions
            populated_form: Form to modify
            conditional_metadata: Metadata tracking
        """
        try:
            actions = rule.get("actions", [])
            
            for action in actions:
                action_type = action.get("type")
                
                if action_type == "make_required":
                    field_name = action.get("field")
                    if field_name and field_name in populated_form["form_data"]:
                        populated_form["form_data"][field_name]["required"] = True
                        populated_form["form_data"][field_name]["conditional_requirement"] = True
                        conditional_metadata["conditional_requirements_added"] += 1
                        
                        # Check if this creates a new missing required field
                        field_value = populated_form["form_data"][field_name].get("value")
                        if not field_value or str(field_value).strip() == "":
                            if field_name not in populated_form["form_metadata"]["missing_fields"]:
                                populated_form["form_metadata"]["missing_fields"].append(field_name)
                
                elif action_type == "set_value":
                    field_name = action.get("field")
                    value = action.get("value")
                    confidence = action.get("confidence", 0.7)
                    
                    if field_name and field_name in populated_form["form_data"]:
                        populated_form["form_data"][field_name]["value"] = value
                        populated_form["form_data"][field_name]["confidence"] = confidence
                        populated_form["form_data"][field_name]["conditional_value"] = True
                        conditional_metadata["conditional_values_set"] += 1
                        
                        # Update metadata counters
                        if value and str(value).strip():
                            if field_name not in populated_form["form_metadata"]["confidence_scores"]:
                                populated_form["form_metadata"]["populated_fields_count"] += 1
                            populated_form["form_metadata"]["confidence_scores"][field_name] = confidence
                            
                            # Remove from missing fields if present
                            if field_name in populated_form["form_metadata"]["missing_fields"]:
                                populated_form["form_metadata"]["missing_fields"].remove(field_name)
                
                elif action_type == "add_note":
                    note = action.get("note", "")
                    if "conditional_notes" not in populated_form["form_metadata"]:
                        populated_form["form_metadata"]["conditional_notes"] = []
                    populated_form["form_metadata"]["conditional_notes"].append(note)
                
        except Exception as e:
            logger.warning(f"Error applying rule actions: {e}")
    
    def _apply_transformations(self, value: Any, transformations: List[Dict[str, Any]]) -> Any:
        """Apply transformations to a field value."""
        for transformation in transformations:
            transform_type = transformation.get("type")
            
            if transform_type == "uppercase":
                if isinstance(value, str):
                    value = value.upper()
            elif transform_type == "lowercase":
                if isinstance(value, str):
                    value = value.lower()
            elif transform_type == "trim":
                if isinstance(value, str):
                    value = value.strip()
            elif transform_type == "format_date":
                # Add date formatting logic here
                pass
            elif transform_type == "extract_first":
                if isinstance(value, list) and value:
                    value = value[0]
        
        return value
    
    def _validate_field_value(self, value: Any, validation_config: Dict[str, Any]) -> bool:
        """Validate a field value against validation rules."""
        try:
            # Check data type
            expected_type = validation_config.get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return False
            
            # Check length constraints
            if isinstance(value, str):
                min_length = validation_config.get("min_length")
                max_length = validation_config.get("max_length")
                if min_length and len(value) < min_length:
                    return False
                if max_length and len(value) > max_length:
                    return False
            
            # Check pattern matching
            pattern = validation_config.get("pattern")
            if pattern and isinstance(value, str):
                import re
                if not re.match(pattern, value):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_field_confidence(self, value: Any, mapping_config: Dict[str, Any]) -> float:
        """Calculate confidence score for a field value."""
        base_confidence = 0.8
        
        # Reduce confidence for empty or very short values
        if isinstance(value, str):
            if len(value.strip()) == 0:
                return 0.0
            elif len(value.strip()) < 3:
                base_confidence *= 0.7
        
        # Increase confidence if value matches expected patterns
        if "validation" in mapping_config:
            if self._validate_field_value(value, mapping_config["validation"]):
                base_confidence = min(1.0, base_confidence * 1.1)
        
        return round(base_confidence, 2)
    
    def _apply_form_structure(self, form_data: Dict[str, Any], 
                            form_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Apply form structure and organize fields into sections."""
        structured_form = {}
        
        sections = form_structure.get("sections", {})
        for section_name, section_config in sections.items():
            structured_form[section_name] = {
                "title": section_config.get("title", section_name),
                "fields": {},
                "section_metadata": {
                    "populated_fields": 0,
                    "total_fields": len(section_config.get("fields", []))
                }
            }
            
            # Add fields to this section
            for field_name in section_config.get("fields", []):
                if field_name in form_data:
                    structured_form[section_name]["fields"][field_name] = form_data[field_name]
                    if form_data[field_name]["value"] is not None:
                        structured_form[section_name]["section_metadata"]["populated_fields"] += 1
        
        return structured_form
    
    def _validate_schema(self, schema: Dict[str, Any]) -> None:
        """Validate that the form schema has the required structure."""
        required_keys = ["schema_name", "field_mappings"]
        for key in required_keys:
            if key not in schema:
                raise FormFillerError(f"Schema missing required key: {key}")
        
        # Validate field mappings structure
        field_mappings = schema["field_mappings"]
        if not isinstance(field_mappings, dict):
            raise FormFillerError("field_mappings must be a dictionary")
        
        for field_name, mapping in field_mappings.items():
            if not isinstance(mapping, dict):
                raise FormFillerError(f"Mapping for field {field_name} must be a dictionary")
            if "source_field" not in mapping:
                raise FormFillerError(f"Mapping for field {field_name} missing source_field")
        
        # Validate conditional rules if present
        if "conditional_rules" in schema:
            self._validate_conditional_rules(schema["conditional_rules"], field_mappings)
    
    def _validate_conditional_rules(self, conditional_rules: Dict[str, Any], 
                                  field_mappings: Dict[str, Any]) -> None:
        """Validate conditional rules structure."""
        try:
            # Validate simple rules
            simple_rules = conditional_rules.get("simple_rules", [])
            for i, rule in enumerate(simple_rules):
                if "condition" not in rule:
                    raise FormFillerError(f"Simple rule {i} missing condition")
                if "actions" not in rule:
                    raise FormFillerError(f"Simple rule {i} missing actions")
                
                # Validate that referenced fields exist
                condition = rule["condition"]
                if "field" in condition:
                    field_name = condition["field"]
                    if field_name not in field_mappings:
                        raise FormFillerError(f"Simple rule {i} references unknown field: {field_name}")
            
            # Validate complex inference rules
            complex_rules = conditional_rules.get("complex_inference_rules", [])
            for i, rule in enumerate(complex_rules):
                if "llm_inference" not in rule:
                    raise FormFillerError(f"Complex rule {i} missing llm_inference")
                if "actions" not in rule:
                    raise FormFillerError(f"Complex rule {i} missing actions")
                
                llm_config = rule["llm_inference"]
                if "prompt" not in llm_config:
                    raise FormFillerError(f"Complex rule {i} missing prompt in llm_inference")
                
        except Exception as e:
            raise FormFillerError(f"Invalid conditional rules: {e}")
    
    def generate_filled_pdf(self, template_path: str, populated_data: Dict[str, Any], 
                           output_path: str) -> None:
        """
        Generate a filled PDF from a template using populated form data.
        
        Args:
            template_path: Path to the fillable PDF template
            populated_data: Populated form data from populate_form()
            output_path: Path where the filled PDF should be saved
            
        Raises:
            FormFillerError: If PDF generation fails
        """
        if not PYMUPDF_AVAILABLE:
            raise FormFillerError("PyMuPDF not available. Cannot generate PDF.")
        
        try:
            template_path = Path(template_path)
            output_path = Path(output_path)
            
            if not template_path.exists():
                raise FormFillerError(f"Template PDF not found: {template_path}")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Generating filled PDF from template: {template_path}")
            
            # Open the template PDF
            doc = fitz.open(str(template_path))
            
            # Extract form data values
            form_data = populated_data.get("form_data", {})
            
            # Track filling statistics
            fill_stats = {
                "fields_found": 0,
                "fields_filled": 0,
                "fields_skipped": 0,
                "fields_missing": []
            }
            
            # Iterate through all pages
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get form fields on this page
                widgets = page.widgets()
                
                for widget in widgets:
                    fill_stats["fields_found"] += 1
                    field_name = widget.field_name
                    
                    if field_name in form_data:
                        field_info = form_data[field_name]
                        field_value = field_info.get("value", "")
                        
                        if field_value is not None and str(field_value).strip():
                            # Fill the field based on its type
                            success = self._fill_pdf_field(widget, field_value, field_info)
                            
                            if success:
                                fill_stats["fields_filled"] += 1
                                logger.debug(f"Filled field '{field_name}' with value: {field_value}")
                            else:
                                fill_stats["fields_skipped"] += 1
                                logger.warning(f"Failed to fill field '{field_name}'")
                        else:
                            fill_stats["fields_skipped"] += 1
                            fill_stats["fields_missing"].append(field_name)
                    else:
                        fill_stats["fields_skipped"] += 1
                        fill_stats["fields_missing"].append(field_name)
                        logger.debug(f"No data available for PDF field: {field_name}")
            
            # Save the filled PDF
            doc.save(str(output_path))
            doc.close()
            
            # Log results
            completion_rate = (fill_stats["fields_filled"] / fill_stats["fields_found"]) if fill_stats["fields_found"] > 0 else 0
            
            logger.info(
                f"PDF generation completed: {output_path}\n"
                f"  Fields found: {fill_stats['fields_found']}\n"
                f"  Fields filled: {fill_stats['fields_filled']}\n"
                f"  Completion rate: {completion_rate:.1%}"
            )
            
            # Add PDF generation metadata to populated_data if it's mutable
            if isinstance(populated_data, dict) and "form_metadata" in populated_data:
                populated_data["form_metadata"]["pdf_generation"] = {
                    "template_path": str(template_path),
                    "output_path": str(output_path),
                    "generation_timestamp": datetime.now().isoformat(),
                    "fill_statistics": fill_stats,
                    "completion_rate": completion_rate
                }
            
        except Exception as e:
            logger.error(f"Error generating filled PDF: {e}")
            raise FormFillerError(f"PDF generation failed: {e}")
    
    def _fill_pdf_field(self, widget, value: Any, field_info: Dict[str, Any]) -> bool:
        """
        Fill a single PDF form field based on its type.
        
        Args:
            widget: PyMuPDF widget object
            value: Value to fill
            field_info: Additional field information
            
        Returns:
            True if field was successfully filled, False otherwise
        """
        try:
            field_type = widget.field_type
            str_value = str(value).strip()
            
            if field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                # Text field
                widget.field_value = str_value
                widget.update()
                return True
                
            elif field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                # Checkbox field
                if str_value.lower() in ["yes", "true", "1", "checked", "on"]:
                    widget.field_value = True
                else:
                    widget.field_value = False
                widget.update()
                return True
                
            elif field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                # Radio button field
                widget.field_value = str_value
                widget.update()
                return True
                
            elif field_type == fitz.PDF_WIDGET_TYPE_COMBOBOX:
                # Dropdown/combobox field
                widget.field_value = str_value
                widget.update()
                return True
                
            elif field_type == fitz.PDF_WIDGET_TYPE_LISTBOX:
                # List box field
                widget.field_value = str_value
                widget.update()
                return True
                
            else:
                logger.warning(f"Unsupported field type: {field_type}")
                return False
                
        except Exception as e:
            logger.warning(f"Error filling field: {e}")
            return False


# Convenience functions
def populate_form(extracted_entities: Dict[str, Any], form_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to populate a form without instantiating the service class.
    
    Args:
        extracted_entities: Dictionary of entities extracted from the document
        form_schema: Schema defining the form structure and field mappings
        
    Returns:
        Dictionary representing the populated form
    """
    service = FormFillerService()
    return service.populate_form(extracted_entities, form_schema)


def load_and_populate_form(extracted_entities: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
    """
    Convenience function to load a schema and populate a form in one call.
    
    Args:
        extracted_entities: Dictionary of entities extracted from the document
        schema_name: Name of the schema file (without .json extension)
        
    Returns:
        Dictionary representing the populated form
    """
    service = FormFillerService()
    schema = service.load_form_schema(schema_name)
    return service.populate_form(extracted_entities, schema)


# Service status functions
def get_form_filler_service_info() -> Dict[str, Any]:
    """
    Get information about the form filler service.
    
    Returns:
        Dictionary with service information
    """
    return {
        "service_name": "Form Filler Service",
        "version": "2.0.0",
        "supported_features": [
            "Entity to form field mapping",
            "Field validation and transformation",
            "Confidence scoring",
            "Form structure organization",
            "Schema-based configuration",
            "Conditional logic rules",
            "LLM-based complex inferences"
        ],
        "schema_directory": str(Path(__file__).parent.parent.parent / "data"),
        "supported_transformations": [
            "uppercase", "lowercase", "trim", "format_date", "extract_first"
        ],
        "supported_validations": [
            "type checking", "length constraints", "pattern matching"
        ],
        "conditional_logic": {
            "simple_conditions": [
                "equals", "not_equals", "contains", "not_empty", 
                "empty", "greater_than", "less_than", "regex"
            ],
            "complex_inferences": [
                "LLM-based medical reasoning",
                "Treatment history analysis",
                "Clinical criteria evaluation"
            ],
            "actions": [
                "make_required", "set_value", "add_note"
            ]
        }
    }


def check_form_filler_availability() -> bool:
    """
    Check if the form filler service is available.
    
    Returns:
        True if service is available, False otherwise
    """
    try:
        service = FormFillerService()
        return True
    except Exception:
        return False


def generate_filled_pdf(template_path: str, populated_data: Dict[str, Any], output_path: str) -> None:
    """
    Convenience function to generate a filled PDF without instantiating the service class.
    
    Args:
        template_path: Path to the fillable PDF template
        populated_data: Populated form data from populate_form()
        output_path: Path where the filled PDF should be saved
        
    Raises:
        FormFillerError: If PDF generation fails
    """
    service = FormFillerService()
    return service.generate_filled_pdf(template_path, populated_data, output_path) 