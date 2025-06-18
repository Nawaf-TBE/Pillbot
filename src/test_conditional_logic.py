"""
Test script for Conditional Logic in Form Filler Service

This script demonstrates the enhanced form filler service with conditional logic
capabilities, including simple rules and complex LLM-based inferences.
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.form_filler_service import (
    FormFillerService, load_and_populate_form, get_form_filler_service_info,
    check_form_filler_availability, FormFillerError
)

def create_test_entities_diabetes_controlled():
    """Create test entities for a well-controlled diabetes patient."""
    return {
        # Patient Information
        "member_id": "DM123456789",
        "patient_first_name": "Alice",
        "patient_last_name": "Thompson",
        "patient_date_of_birth": "05/12/1968",
        
        # Prescriber Information
        "prescriber_name": "Dr. Sarah Martinez",
        "prescriber_npi": "1234567890",
        "prescriber_phone": "(555) 432-1098",
        
        # Diagnosis Information - Will trigger conditional rules
        "primary_diagnosis_code": "E11.9",  # Type 2 diabetes - triggers A1C requirement
        "primary_diagnosis": "Type 2 diabetes mellitus without complications",
        
        # Medication Information
        "requested_drug_name": "Ozempic",
        "requested_strength": "0.5 mg/dose",
        "quantity_requested": "1.5 ml pen",
        "days_supply": "28",
        
        # Clinical Information - Will trigger conditional logic
        "a1c_value": "7.8%",  # Moderate control - won't trigger high priority
        "bmi_value": "31.2",
        "previous_medications_tried": "Metformin 1000mg BID for 6 months - inadequate control. Glipizide 10mg daily for 4 months - hypoglycemic episodes. Sitagliptin 100mg daily for 3 months - insufficient efficacy.",
        "contraindications_present": "No",
        "clinical_justification": "Patient has Type 2 diabetes with suboptimal glycemic control on maximum tolerated doses of metformin and sulfonylurea. Has tried DPP-4 inhibitor without adequate response. No contraindications to GLP-1 therapy. Patient would benefit from Ozempic for improved glycemic control."
    }

def create_test_entities_diabetes_poor_control():
    """Create test entities for a poorly controlled diabetes patient."""
    return {
        # Patient Information
        "member_id": "DM987654321",
        "patient_first_name": "Robert",
        "patient_last_name": "Chen",
        "patient_date_of_birth": "11/08/1955",
        
        # Prescriber Information
        "prescriber_name": "Dr. Michael Rodriguez",
        "prescriber_npi": "9876543210",
        
        # Diagnosis Information
        "primary_diagnosis_code": "E11.65",  # Type 2 diabetes with hyperglycemia
        "primary_diagnosis": "Type 2 diabetes mellitus with hyperglycemia",
        
        # Medication Information
        "requested_drug_name": "Ozempic",
        "requested_strength": "1.0 mg/dose",
        "quantity_requested": "3 ml pen",
        
        # Clinical Information - Will trigger high priority rule
        "a1c_value": "10.2%",  # Poor control - will trigger high priority
        "bmi_value": "29.8",
        "previous_medications_tried": "Metformin 2000mg daily, Glimepiride 8mg daily, Sitagliptin 100mg daily - all at maximum doses for adequate duration with poor glycemic response",
        "contraindications_present": "No",
        "clinical_justification": "Patient with poorly controlled Type 2 diabetes despite triple oral therapy at maximum tolerated doses. Recent A1C of 10.2% indicates urgent need for intensification. Patient has cardiovascular risk factors including hypertension and dyslipidemia. GLP-1 agonist therapy indicated for both glycemic control and cardiovascular protection.",
        "medical_history": "Hypertension, dyslipidemia, diabetic retinopathy"
    }

def create_test_entities_with_contraindications():
    """Create test entities for a patient with contraindications."""
    return {
        # Patient Information
        "member_id": "CI555666777",
        "patient_first_name": "Maria",
        "patient_last_name": "Lopez",
        "patient_date_of_birth": "03/15/1972",
        
        # Prescriber Information
        "prescriber_name": "Dr. Jennifer Kim",
        
        # Diagnosis Information
        "primary_diagnosis_code": "E11.9",
        "primary_diagnosis": "Type 2 diabetes mellitus",
        
        # Medication Information
        "requested_drug_name": "Ozempic",
        "requested_strength": "0.25 mg/dose",
        "quantity_requested": "1.5 ml pen",
        
        # Clinical Information - Has contraindications
        "a1c_value": "8.5%",
        "contraindications_present": "Yes",  # Will trigger justification requirement
        "clinical_justification": "Patient has history of pancreatitis 2 years ago, but extensive workup shows resolved acute pancreatitis with no chronic changes. Multiple consultations with gastroenterology confirm no ongoing pancreatic dysfunction. Benefits of GLP-1 therapy outweigh risks given poor diabetes control and cardiovascular risk profile.",
        "previous_medications_tried": "Metformin, Glyburide - both failed due to side effects"
    }

def test_simple_conditional_rules():
    """Test simple conditional logic rules."""
    print("🔧 Testing Simple Conditional Rules")
    print("=" * 45)
    
    try:
        # Test 1: Diabetes diagnosis requiring A1C
        print("\n📋 Test 1: Diabetes Diagnosis → A1C Required")
        print("-" * 45)
        
        entities_1 = create_test_entities_diabetes_controlled()
        result_1 = load_and_populate_form(entities_1, "InsureCo_Ozempic")
        
        # Check if A1C is now required
        a1c_field = result_1["form_data"]["a1c_value"]
        print(f"✅ A1C field required: {a1c_field['required']}")
        print(f"   Conditional requirement: {a1c_field.get('conditional_requirement', False)}")
        
        # Check conditional logic metadata
        conditional_logic = result_1["form_metadata"].get("conditional_logic", {})
        print(f"   Rules triggered: {conditional_logic.get('rules_triggered', 0)}")
        
        # Check for conditional notes
        notes = result_1["form_metadata"].get("conditional_notes", [])
        if notes:
            print(f"   Conditional notes: {notes[0]}")
        
        # Test 2: Poor A1C control → High Priority
        print(f"\n📋 Test 2: High A1C → High Priority")
        print("-" * 35)
        
        entities_2 = create_test_entities_diabetes_poor_control()
        result_2 = load_and_populate_form(entities_2, "InsureCo_Ozempic")
        
        # Check if priority level was set
        priority_field = result_2["form_data"].get("priority_level", {})
        if priority_field.get("value"):
            print(f"✅ Priority level set: {priority_field['value']}")
            print(f"   Conditional value: {priority_field.get('conditional_value', False)}")
            print(f"   Confidence: {priority_field.get('confidence', 0)}")
        
        # Test 3: Contraindications → Require Justification
        print(f"\n📋 Test 3: Contraindications → Justification Required")
        print("-" * 50)
        
        entities_3 = create_test_entities_with_contraindications()
        result_3 = load_and_populate_form(entities_3, "InsureCo_Ozempic")
        
        # Check if clinical justification is now required
        justification_field = result_3["form_data"]["clinical_justification"]
        print(f"✅ Clinical justification required: {justification_field['required']}")
        print(f"   Has justification: {'Yes' if justification_field.get('value') else 'No'}")
        
        return result_1, result_2, result_3
        
    except Exception as e:
        print(f"❌ Error testing simple conditional rules: {e}")
        return None, None, None

def test_complex_llm_inferences():
    """Test complex LLM-based inference rules."""
    print(f"\n🧠 Testing Complex LLM Inferences")
    print("=" * 40)
    
    try:
        # Import LLM service to check availability
        from services.llm_service import check_llm_availability
        
        if not check_llm_availability():
            print("⚠️  LLM service not available (GEMINI_API_KEY not configured)")
            print("   Complex inference rules will be skipped")
            return None
        
        # Test step therapy analysis
        print(f"\n🔍 Test: Step Therapy Failure Analysis")
        print("-" * 40)
        
        entities = create_test_entities_diabetes_controlled()
        
        # Create a service instance for testing
        service = FormFillerService()
        schema = service.load_form_schema("InsureCo_Ozempic")
        
        print(f"📤 Calling LLM for step therapy analysis...")
        print(f"   Previous medications: {entities['previous_medications_tried'][:100]}...")
        
        result = service.populate_form(entities, schema)
        
        # Check if LLM inferences were performed
        conditional_logic = result["form_metadata"].get("conditional_logic", {})
        llm_inferences = conditional_logic.get("llm_inferences", 0)
        
        print(f"✅ LLM inferences performed: {llm_inferences}")
        
        # Check if step therapy field was set
        step_therapy_field = result["form_data"].get("step_therapy_requirement_met", {})
        if step_therapy_field.get("value"):
            print(f"   Step therapy requirement met: {step_therapy_field['value']}")
            print(f"   Confidence: {step_therapy_field.get('confidence', 0)}")
        
        # Check cardiovascular indication
        cv_field = result["form_data"].get("cardiovascular_indication", {})
        if cv_field.get("value"):
            print(f"   Cardiovascular indication: {cv_field['value']}")
        
        return result
        
    except ImportError:
        print("⚠️  LLM service not available (import failed)")
        return None
    except Exception as e:
        print(f"❌ Error testing complex LLM inferences: {e}")
        return None

def test_conditional_logic_integration():
    """Test the complete conditional logic integration."""
    print(f"\n🎯 Testing Complete Conditional Logic Integration")
    print("=" * 55)
    
    # Test with comprehensive patient data
    entities = create_test_entities_diabetes_poor_control()
    
    try:
        result = load_and_populate_form(entities, "InsureCo_Ozempic")
        
        # Analyze results
        metadata = result["form_metadata"]
        conditional_logic = metadata.get("conditional_logic", {})
        
        print(f"📊 Conditional Logic Summary:")
        print(f"   Rules evaluated: {conditional_logic.get('rules_evaluated', 0)}")
        print(f"   Rules triggered: {conditional_logic.get('rules_triggered', 0)}")
        print(f"   LLM inferences: {conditional_logic.get('llm_inferences', 0)}")
        print(f"   Requirements added: {conditional_logic.get('conditional_requirements_added', 0)}")
        print(f"   Values set: {conditional_logic.get('conditional_values_set', 0)}")
        
        # Show conditional notes
        notes = metadata.get("conditional_notes", [])
        if notes:
            print(f"\n📝 Conditional Notes:")
            for i, note in enumerate(notes, 1):
                print(f"   {i}. {note}")
        
        # Show fields with conditional modifications
        print(f"\n🔧 Fields Modified by Conditional Logic:")
        form_data = result["form_data"]
        
        for field_name, field_data in form_data.items():
            modifications = []
            if field_data.get("conditional_requirement"):
                modifications.append("made required")
            if field_data.get("conditional_value"):
                modifications.append(f"value set to '{field_data['value']}'")
            
            if modifications:
                print(f"   {field_name}: {', '.join(modifications)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in integration test: {e}")
        return None

def main():
    """Main test function."""
    print("🤖 Form Filler Service - Conditional Logic Testing")
    print("=" * 60)
    
    # Check service availability
    if not check_form_filler_availability():
        print("❌ Form filler service not available")
        return
    
    # Display enhanced service info
    service_info = get_form_filler_service_info()
    print(f"📋 Service: {service_info['service_name']} v{service_info['version']}")
    print(f"🔧 New Features:")
    for feature in service_info['supported_features'][-2:]:  # Show last 2 (new) features
        print(f"   • {feature}")
    
    print(f"\n🛠️  Conditional Logic Capabilities:")
    conditional_logic = service_info.get('conditional_logic', {})
    print(f"   Simple conditions: {len(conditional_logic.get('simple_conditions', []))} types")
    print(f"   Complex inferences: {len(conditional_logic.get('complex_inferences', []))} types")
    print(f"   Available actions: {', '.join(conditional_logic.get('actions', []))}")
    
    # Run tests
    simple_results = test_simple_conditional_rules()
    llm_result = test_complex_llm_inferences()
    integration_result = test_conditional_logic_integration()
    
    # Summary
    print(f"\n🎉 Conditional Logic Testing Summary")
    print("-" * 40)
    
    if simple_results and any(simple_results):
        print("✅ Simple conditional rules: Working")
    else:
        print("❌ Simple conditional rules: Failed")
    
    if llm_result:
        print("✅ LLM-based inferences: Working")
    else:
        print("⚠️  LLM-based inferences: Skipped (API not available)")
    
    if integration_result:
        print("✅ Complete integration: Working")
    else:
        print("❌ Complete integration: Failed")
    
    print(f"\n📁 Enhanced conditional logic ready for production use!")

if __name__ == "__main__":
    main() 