# Form Filler Service Documentation

## Overview

The Form Filler Service is an enhanced component of the PriorAuthAutomation system that populates insurance prior authorization forms based on extracted document entities using configurable JSON schemas. **Version 2.0** introduces advanced conditional logic capabilities and LLM-based complex inferences.

## New Features in Version 2.0

### 🔧 Conditional Logic Rules
- **Simple Rules**: Basic conditional logic based on form field values
- **Complex Inferences**: LLM-powered analysis for medical reasoning
- **Dynamic Requirements**: Fields can become required based on conditions
- **Smart Value Setting**: Automatic population of derived fields
- **Clinical Notes**: Contextual annotations based on rule triggers

### 🧠 LLM-Based Complex Inferences
- **Step Therapy Analysis**: Determine if treatment progression requirements are met
- **Cardiovascular Risk Assessment**: Evaluate cardiovascular benefit indications
- **Dosing Appropriateness**: Verify clinical appropriateness of requested medications
- **Medical History Analysis**: Extract complex clinical patterns from narrative text

## Core Features

### Entity Mapping
- Maps extracted document entities to specific form fields
- Supports nested entity structures and complex data transformations
- Configurable field mappings through JSON schemas

### Field Validation
- **Type Checking**: Ensures data types match field requirements
- **Length Constraints**: Validates minimum and maximum field lengths
- **Pattern Matching**: Uses regex patterns for format validation
- **Required Field Validation**: Checks for mandatory field completion

### Data Transformations
- **Text Processing**: uppercase, lowercase, trim operations
- **Date Formatting**: Standardizes date representations
- **Value Extraction**: Extracts specific components from complex values

### Confidence Scoring
- Calculates confidence scores for each populated field
- Factors in data quality, validation success, and source reliability
- Provides overall form completion confidence metrics

## Conditional Logic System

### Simple Conditional Rules

Simple rules evaluate basic conditions on form field values and trigger actions when conditions are met.

#### Supported Condition Types
- `equals`: Exact value match
- `not_equals`: Value mismatch
- `contains`: Substring presence
- `not_empty`: Non-empty value check
- `empty`: Empty value check
- `greater_than`: Numeric comparison (handles percentages)
- `less_than`: Numeric comparison (handles percentages)
- `regex`: Regular expression matching

#### Available Actions
- `make_required`: Dynamically mark fields as required
- `set_value`: Populate fields with computed values
- `add_note`: Include contextual annotations

#### Example Simple Rule
```json
{
  "name": "require_a1c_for_diabetes",
  "description": "If patient has diabetes diagnosis, A1C value is required",
  "condition": {
    "type": "contains",
    "field": "primary_diagnosis_code",
    "value": "E11"
  },
  "actions": [
    {
      "type": "make_required",
      "field": "a1c_value"
    },
    {
      "type": "add_note",
      "note": "A1C value is required for diabetes patients"
    }
  ]
}
```

### Complex LLM-Based Inference Rules

Complex rules leverage Large Language Models to perform sophisticated medical reasoning and clinical analysis.

#### LLM Inference Capabilities
- **Medical Context Analysis**: Interpret clinical narratives and medical history
- **Treatment Pattern Recognition**: Identify medication trial patterns and failures
- **Risk Factor Assessment**: Evaluate cardiovascular and other clinical risks
- **Dosing Validation**: Assess appropriateness of medication dosing

#### Example Complex Rule
```json
{
  "name": "step_therapy_failure_check",
  "description": "Determine if patient has failed adequate trial of two oral diabetes medications",
  "llm_inference": {
    "prompt": "Based on the following medical information, determine if the patient has failed an adequate trial of at least two different oral diabetes medications...",
    "context_fields": ["previous_medications_tried", "clinical_justification", "primary_diagnosis"],
    "result_field": "step_therapy_completed",
    "expected_result": "yes"
  },
  "actions": [
    {
      "type": "set_value",
      "field": "step_therapy_requirement_met",
      "value": "Yes",
      "confidence": 0.85
    }
  ]
}
```

## Schema Structure

### Enhanced Schema Format
```json
{
  "schema_name": "InsureCo_Ozempic",
  "schema_version": "2.0",
  "description": "Prior authorization form for Ozempic with conditional logic",
  
  "field_mappings": {
    // Standard field mappings (unchanged)
  },
  
  "conditional_rules": {
    "simple_rules": [
      // Array of simple conditional rules
    ],
    "complex_inference_rules": [
      // Array of LLM-based inference rules
    ]
  },
  
  "form_structure": {
    // Form organization (unchanged)
  }
}
```

## Usage Examples

### Basic Form Population
```python
from services.form_filler_service import load_and_populate_form

# Extract entities (from previous pipeline steps)
entities = {
    "member_id": "12345",
    "patient_first_name": "John",
    "primary_diagnosis_code": "E11.9",
    "a1c_value": "10.2%",
    // ... other entities
}

# Populate form with conditional logic
result = load_and_populate_form(entities, "InsureCo_Ozempic")

# Check conditional logic results
conditional_logic = result["form_metadata"]["conditional_logic"]
print(f"Rules triggered: {conditional_logic['rules_triggered']}")
print(f"LLM inferences: {conditional_logic['llm_inferences']}")
```

### Advanced Service Usage
```python
from services.form_filler_service import FormFillerService

# Create service instance
service = FormFillerService()

# Load schema
schema = service.load_form_schema("InsureCo_Ozempic")

# Populate with full control
result = service.populate_form(entities, schema)

# Analyze conditional modifications
for field_name, field_data in result["form_data"].items():
    if field_data.get("conditional_requirement"):
        print(f"{field_name} made required by conditional logic")
    if field_data.get("conditional_value"):
        print(f"{field_name} value set by conditional logic: {field_data['value']}")
```

## Output Structure

### Enhanced Form Output
```json
{
  "form_metadata": {
    "schema_name": "InsureCo_Ozempic",
    "completion_rate": 0.95,
    "conditional_logic": {
      "rules_evaluated": 7,
      "rules_triggered": 2,
      "llm_inferences": 1,
      "conditional_requirements_added": 1,
      "conditional_values_set": 1
    },
    "conditional_notes": [
      "A1C value is required for diabetes patients",
      "High priority due to poor glycemic control"
    ],
    "missing_fields": ["prescriber_phone"],
    "confidence_scores": {
      "member_id": 1.0,
      "priority_level": 0.9
    }
  },
  "form_data": {
    "member_id": {
      "value": "12345",
      "confidence": 1.0,
      "required": true
    },
    "a1c_value": {
      "value": "10.2%",
      "confidence": 0.9,
      "required": true,
      "conditional_requirement": true
    },
    "priority_level": {
      "value": "High",
      "confidence": 0.9,
      "conditional_value": true
    }
  }
}
```

## Configuration

### Environment Setup
For LLM-based complex inferences, configure:
```bash
export GEMINI_API_KEY="your_gemini_api_key"
```

### Schema Configuration
1. Define field mappings for all form fields
2. Add simple conditional rules for basic logic
3. Configure complex inference rules for medical reasoning
4. Validate schema structure using the service's validation methods

## Testing

### Comprehensive Test Suite
```bash
# Test all conditional logic features
python src/test_conditional_logic.py

# Test simple rules only
python src/test_form_filler.py

# Demo complete integration
python src/demo_form_filling.py
```

### Test Scenarios
- **Diabetes with A1C requirement**: Tests field requirement logic
- **Poor glycemic control**: Tests priority setting logic
- **Contraindications present**: Tests justification requirements
- **Step therapy analysis**: Tests LLM-based medical reasoning
- **Cardiovascular risk assessment**: Tests complex clinical inference

## Performance Considerations

### LLM Usage Optimization
- Complex inference rules only execute when conditions are met
- LLM calls are batched when possible
- Fallback handling for LLM service unavailability
- Caching of repeated inference results (future enhancement)

### Error Handling
- Graceful degradation when LLM service is unavailable
- Detailed error logging for troubleshooting
- Conditional logic errors don't fail entire form population
- Comprehensive validation of rule configurations

## Schema Validation

The service validates:
- Required schema structure and field mappings
- Conditional rule syntax and field references
- LLM inference configuration completeness
- Action target field existence

## Integration with Pipeline

### Seamless Integration
The enhanced form filler service integrates seamlessly with the existing PriorAuthAutomation pipeline:

1. **Document Processing**: OCR and parsing extract entities
2. **Entity Extraction**: LLM service identifies key information
3. **Form Population**: Enhanced form filler applies conditional logic
4. **Result Storage**: Populated forms saved with conditional metadata
5. **Workflow Routing**: Priority and requirements influence processing

### Service Status Integration
```python
from services.form_filler_service import get_form_filler_service_info, check_form_filler_availability

# Check enhanced capabilities
info = get_form_filler_service_info()
print(f"Service version: {info['version']}")
print(f"Conditional logic available: {info['conditional_logic']}")

# Verify service availability
if check_form_filler_availability():
    print("Enhanced form filler ready for production")
```

## Future Enhancements

### Roadmap
- **Multi-form Support**: Handle multiple form types simultaneously
- **Dynamic Schema Loading**: Runtime schema updates without restart
- **Advanced Caching**: Cache LLM inference results for similar cases
- **Machine Learning Integration**: Learn from form completion patterns
- **Real-time Validation**: Live validation during form entry
- **Custom Rule Engine**: Visual rule builder interface

### Extensibility
The conditional logic system is designed for easy extension:
- Add new condition types by extending `_evaluate_simple_rule`
- Implement new actions in `_apply_rule_actions`
- Integrate additional LLM providers in `_evaluate_complex_rule`
- Create domain-specific inference rules for different medical specialties

## Troubleshooting

### Common Issues
1. **LLM Service Unavailable**: Ensure GEMINI_API_KEY is configured
2. **Rule Not Triggering**: Check field names and condition syntax
3. **Performance Issues**: Optimize LLM prompts and reduce context size
4. **Validation Failures**: Verify schema structure and field references

### Debug Mode
Enable detailed logging for troubleshooting:
```python
import logging
logging.getLogger('services.form_filler_service').setLevel(logging.DEBUG)
```

This enhanced Form Filler Service provides production-ready conditional logic capabilities that significantly improve the accuracy and intelligence of prior authorization form population while maintaining backward compatibility with existing implementations. 