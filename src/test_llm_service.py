"""
Test script for LLM entity extraction functionality using Google Gemini API.
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm_service import (
    extract_entities_with_gemini, extract_specific_entities, check_llm_availability,
    get_llm_service_info, validate_extracted_entities, LLMServiceError
)


def create_sample_medical_document_content():
    """
    Create sample medical document content for testing entity extraction.
    
    Returns:
        str: Sample medical document content
    """
    return """
# PRIOR AUTHORIZATION REQUEST

**Document Number:** PA-2024-001234
**Date:** January 15, 2024
**Submission Date:** January 15, 2024

## PATIENT INFORMATION

**Patient Name:** Sarah Michelle Johnson
**Date of Birth:** March 22, 1985
**Member ID:** BC987654321
**Patient ID:** PMI-54321
**SSN:** XXX-XX-1234
**Phone:** (555) 123-4567
**Address:** 123 Oak Street, Springfield, IL 62701

## MEDICAL INFORMATION

**Primary Diagnosis:** Type 2 Diabetes Mellitus
**Primary Diagnosis Code:** ICD-10: E11.9
**Secondary Diagnoses:** 
- Hypertension
- Dyslipidemia

**Secondary Diagnosis Codes:**
- ICD-10: I10 (Hypertension)
- ICD-10: E78.5 (Dyslipidemia)

**Medical History:** Patient has a 5-year history of Type 2 diabetes, initially managed with lifestyle modifications. Progressive deterioration in glycemic control despite adherence to metformin and lifestyle interventions.

**Allergies:** 
- Sulfa drugs (causes rash)
- Penicillin (causes hives)

**Current Medications:**
- Metformin 1000mg twice daily
- Lisinopril 10mg once daily
- Atorvastatin 20mg once daily

## REQUESTED MEDICATION

**Requested Drug Name:** Jardiance (empagliflozin)
**Drug Strength:** 25mg
**Drug Form:** Tablet
**Quantity Requested:** 90 tablets
**Days Supply:** 90 days
**Refills:** 5 refills
**Indication:** Type 2 Diabetes Mellitus - inadequate glycemic control with current therapy

## PRESCRIBER INFORMATION

**Prescriber Name:** Dr. Michael Chen, MD
**Prescriber NPI:** 1234567890
**Prescriber Phone:** (555) 987-6543
**Prescriber Address:** 456 Medical Center Drive, Springfield, IL 62702
**Prescriber DEA:** BC1234567
**Specialty:** Endocrinology

## PHARMACY INFORMATION

**Pharmacy Name:** CVS Pharmacy #12345
**Pharmacy Address:** 789 Main Street, Springfield, IL 62701
**Pharmacy Phone:** (555) 456-7890
**Pharmacist Name:** Dr. Lisa Wong, PharmD

## INSURANCE AND AUTHORIZATION

**Insurance Plan:** Blue Cross Blue Shield PPO Gold
**Group Number:** 54321
**Policy Number:** BC987654321-001
**Request Date:** January 15, 2024
**Urgency:** Standard

## CLINICAL INFORMATION

**Lab Results:** 
- HbA1c: 8.2% (Target: <7%) - Date: December 20, 2023
- Fasting Glucose: 165 mg/dL - Date: December 20, 2023
- eGFR: 85 mL/min/1.73m² - Date: December 20, 2023

**Previous Treatments:**
- Metformin 1000mg BID - Inadequate response after 6 months
- Glipizide 10mg BID - Side effects (hypoglycemia)
- Insulin consideration - Patient preference for oral medication

**Treatment Failure Reason:** Current therapy (metformin) insufficient to achieve target HbA1c <7%. Patient experienced hypoglycemic episodes with sulfonylurea addition.

**Clinical Notes:** Patient demonstrates good medication adherence and lifestyle compliance. SGLT2 inhibitor therapy clinically appropriate given current renal function and cardiovascular risk profile.

## ADMINISTRATIVE

**Document Type:** Prior Authorization Request
**Document Date:** January 15, 2024
**Submission Date:** January 15, 2024

---

**Prescriber Attestation:** I certify that this medication is medically necessary for this patient and that alternative therapies have been considered or tried without success.

**Physician Signature:** Dr. Michael Chen, MD  
**Date:** January 15, 2024
"""


def test_llm_entity_extraction():
    """
    Test LLM entity extraction functionality with sample medical document.
    """
    print("🧪 Testing LLM Entity Extraction Service")
    print("=" * 50)
    
    # Test 1: Service Availability
    print(f"\n🔸 Test 1: LLM Service Availability")
    print("-" * 35)
    
    if check_llm_availability():
        print("✅ Gemini LLM service available")
        
        # Show service information
        service_info = get_llm_service_info()
        print(f"   Service: {service_info['service_name']}")
        print(f"   Model: {service_info['model']}")
        print(f"   Temperature: {service_info['temperature']}")
        print(f"   Max tokens: {service_info['max_output_tokens']}")
        
    else:
        print("❌ Gemini LLM service not available")
        print("   Please check GEMINI_API_KEY environment variable")
        print("   Install: pip install google-generativeai")
        return False
    
    # Test 2: Basic Entity Extraction
    print(f"\n🔸 Test 2: Basic Entity Extraction")
    print("-" * 35)
    
    try:
        # Create sample document content
        document_content = create_sample_medical_document_content()
        print(f"📄 Sample document created ({len(document_content)} characters)")
        
        # Perform entity extraction
        print(f"🧠 Starting entity extraction...")
        extraction_result = extract_entities_with_gemini(document_content)
        
        entities = extraction_result["extracted_entities"]
        metadata = extraction_result["metadata"]
        
        print(f"✅ Entity extraction completed!")
        print(f"   Processing time: {metadata['processing_time_seconds']} seconds")
        print(f"   Model used: {metadata['model_used']}")
        print(f"   Total entities extracted: {len(entities)}")
        
        # Show key extracted entities
        print(f"\n📋 Key Extracted Entities:")
        key_fields = [
            ("patient_name", "Patient Name"),
            ("date_of_birth", "Date of Birth"),
            ("member_id", "Member ID"),
            ("primary_diagnosis", "Primary Diagnosis"),
            ("primary_diagnosis_code", "Primary Diagnosis Code"),
            ("requested_drug_name", "Requested Drug"),
            ("drug_strength", "Drug Strength"),
            ("prescriber_name", "Prescriber"),
            ("prescriber_npi", "Prescriber NPI"),
            ("insurance_plan", "Insurance Plan"),
            ("pharmacy_name", "Pharmacy")
        ]
        
        for field_key, display_name in key_fields:
            value = entities.get(field_key)
            if value:
                print(f"   {display_name}: {value}")
            else:
                print(f"   {display_name}: [Not found]")
        
        # Test 3: Entity Validation
        print(f"\n🔸 Test 3: Entity Validation")
        print("-" * 35)
        
        validation_result = validate_extracted_entities(entities)
        validation_report = validation_result["validation_report"]
        
        print(f"📊 Validation Report:")
        print(f"   Total fields: {validation_report['total_fields']}")
        print(f"   Populated fields: {validation_report['populated_fields']}")
        print(f"   Empty fields: {validation_report['empty_fields']}")
        print(f"   Confidence score: {validation_report['confidence_score']:.2f}")
        
        if validation_report["validation_issues"]:
            print(f"   ⚠️  Validation issues ({len(validation_report['validation_issues'])}):")
            for issue in validation_report["validation_issues"]:
                print(f"      - {issue}")
        else:
            print(f"   ✅ No validation issues found")
        
        # Test 4: Specific Entity Extraction
        print(f"\n🔸 Test 4: Specific Entity Extraction")
        print("-" * 35)
        
        specific_entities = [
            "patient_name",
            "requested_drug_name", 
            "prescriber_name",
            "primary_diagnosis",
            "insurance_plan"
        ]
        
        print(f"🎯 Extracting specific entities: {', '.join(specific_entities)}")
        
        specific_result = extract_specific_entities(document_content, specific_entities)
        specific_entities_data = specific_result["extracted_entities"]
        
        print(f"✅ Specific extraction completed!")
        print(f"   Processing time: {specific_result['metadata']['processing_time_seconds']} seconds")
        
        for entity in specific_entities:
            value = specific_entities_data.get(entity)
            print(f"   {entity}: {value if value else '[Not found]'}")
        
        # Test 5: Complex Medical Information
        print(f"\n🔸 Test 5: Complex Medical Information Analysis")
        print("-" * 35)
        
        complex_fields = ["allergies", "current_medications", "lab_results", "previous_treatments"]
        found_complex = {}
        
        for field in complex_fields:
            value = entities.get(field)
            if value:
                found_complex[field] = value
        
        if found_complex:
            print(f"📋 Complex medical information extracted:")
            for field, value in found_complex.items():
                if isinstance(value, list):
                    print(f"   {field}: {len(value)} items")
                    for item in value[:2]:  # Show first 2 items
                        print(f"      - {item}")
                    if len(value) > 2:
                        print(f"      ... and {len(value) - 2} more")
                else:
                    print(f"   {field}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
        else:
            print(f"   ⚠️  No complex medical information found")
        
        # Test 6: JSON Output Validation
        print(f"\n🔸 Test 6: JSON Output Validation")
        print("-" * 35)
        
        try:
            json_output = json.dumps(entities, indent=2)
            print(f"✅ Valid JSON output generated ({len(json_output)} characters)")
            
            # Parse back to ensure validity
            parsed_back = json.loads(json_output)
            print(f"✅ JSON parsing validation successful")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON validation failed: {e}")
            return False
        
        print(f"\n🎉 All LLM entity extraction tests completed successfully!")
        return True
        
    except LLMServiceError as e:
        print(f"❌ LLM service error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_error_handling():
    """
    Test error handling scenarios for the LLM service.
    """
    print(f"\n🔸 Bonus Test: Error Handling")
    print("-" * 35)
    
    try:
        # Test with empty content
        try:
            extract_entities_with_gemini("")
            print(f"❌ Should have failed with empty content")
        except ValueError:
            print(f"✅ Correctly handled empty content")
        
        # Test with very short content
        try:
            result = extract_entities_with_gemini("Hello world")
            print(f"✅ Handled short content gracefully")
        except Exception as e:
            print(f"⚠️  Short content handling: {e}")
        
        print(f"✅ Error handling tests completed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")


def main():
    """
    Main function to run LLM service tests.
    """
    success = test_llm_entity_extraction()
    
    if success:
        test_error_handling()
        print(f"\n✅ LLM entity extraction testing completed successfully!")
        print(f"\n💡 Tips for production use:")
        print(f"   - Set GEMINI_API_KEY environment variable")
        print(f"   - Adjust GEMINI_TEMPERATURE for consistency vs creativity")
        print(f"   - Use validation results to assess extraction quality")
        print(f"   - Consider custom prompts for specific document types")
    else:
        print(f"\n❌ LLM testing failed. Check configuration and try again.")
        print(f"\nRequired setup:")
        print(f"   1. Get Gemini API key from https://makersuite.google.com/app/apikey")
        print(f"   2. Set GEMINI_API_KEY environment variable")
        print(f"   3. Install: pip install google-generativeai")


if __name__ == "__main__":
    main() 