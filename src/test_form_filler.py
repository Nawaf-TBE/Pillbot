"""
Test script for the Form Filler Service

This script demonstrates how to use the form filler service to populate
insurance prior authorization forms based on extracted document entities.
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.form_filler_service import (
    FormFillerService, populate_form, load_and_populate_form,
    get_form_filler_service_info, check_form_filler_availability,
    FormFillerError
)

def create_sample_extracted_entities():
    """
    Create sample extracted entities that would come from document processing.
    These represent what might be extracted from a prior authorization request.
    """
    return {
        # Patient Information
        "member_id": "AB123456789",
        "patient_first_name": "John", 
        "patient_last_name": "Smith",
        "patient_date_of_birth": "01/15/1980",
        
        # Prescriber Information  
        "prescriber_name": "Dr. Jane Wilson",
        "prescriber_npi": "1234567890",
        "prescriber_phone": "(555) 123-4567",
        
        # Diagnosis Information
        "primary_diagnosis_code": "E11.9",
        "primary_diagnosis": "Type 2 diabetes mellitus without complications",
        
        # Medication Information
        "requested_drug_name": "Ozempic",
        "requested_strength": "1 mg/0.5 ml",
        "quantity_requested": "3 ml pen injector",
        "days_supply": "84",
        
        # Pharmacy Information
        "pharmacy_name": "Main Street Pharmacy",
        
        # Clinical Information
        "a1c_value": "8.2%",
        "bmi_value": "32.1",
        "previous_medications_tried": "Metformin, Glipizide",
        "contraindications_present": "No",
        "clinical_justification": "Patient with poorly controlled type 2 diabetes despite maximum tolerated doses of metformin and sulfonylurea. HbA1c remains elevated at 8.2%. Patient is appropriate candidate for GLP-1 receptor agonist therapy."
    }

def create_incomplete_extracted_entities():
    """
    Create sample extracted entities with some missing fields to test form completion rates.
    """
    return {
        # Only partial information available
        "member_id": "BC987654321",
        "patient_first_name": "Sarah",
        "patient_last_name": "Johnson", 
        "prescriber_name": "Dr. Michael Brown",
        "primary_diagnosis": "Diabetes Type 2",
        "requested_drug_name": "Ozempic",
        "a1c_value": "7.8"
        # Missing: DOB, NPI, diagnosis code, strength, quantity, etc.
    }

def test_form_filler_service():
    """Test the form filler service with complete sample data."""
    print("🧪 Testing Form Filler Service")
    print("=" * 50)
    
    # Check service availability
    if not check_form_filler_availability():
        print("❌ Form filler service not available")
        return
    
    # Display service information
    service_info = get_form_filler_service_info()
    print(f"📋 Service: {service_info['service_name']} v{service_info['version']}")
    print(f"📂 Schema directory: {service_info['schema_directory']}")
    print(f"🔧 Features: {', '.join(service_info['supported_features'][:3])}...")
    
    try:
        # Test 1: Complete form population
        print(f"\n🎯 Test 1: Complete Form Population")
        print("-" * 35)
        
        sample_entities = create_sample_extracted_entities()
        populated_form = load_and_populate_form(sample_entities, "InsureCo_Ozempic")
        
        metadata = populated_form["form_metadata"]
        print(f"✅ Form populated successfully!")
        print(f"   📊 Completion: {metadata['populated_fields_count']}/{metadata['total_fields_count']} fields ({metadata['completion_rate']:.1%})")
        print(f"   🕒 Timestamp: {metadata['population_timestamp']}")
        
        if metadata["missing_fields"]:
            print(f"   ⚠️  Missing required fields: {len(metadata['missing_fields'])}")
        
        # Show some populated fields
        print(f"\n📝 Sample Populated Fields:")
        form_data = populated_form["form_data"]
        sample_fields = ["member_id", "patient_first_name", "primary_diagnosis_description", "requested_drug_name"]
        
        for field in sample_fields:
            if field in form_data and form_data[field]["value"]:
                value = form_data[field]["value"]
                confidence = form_data[field]["confidence"]
                print(f"   {field}: {value} (confidence: {confidence})")
        
        # Show form sections if available
        if "form_sections" in populated_form:
            print(f"\n📋 Form Sections:")
            for section_name, section_data in populated_form["form_sections"].items():
                populated = section_data["section_metadata"]["populated_fields"]
                total = section_data["section_metadata"]["total_fields"]
                print(f"   {section_data['title']}: {populated}/{total} fields")
        
        # Test 2: Incomplete form population
        print(f"\n🎯 Test 2: Incomplete Form Population")
        print("-" * 38)
        
        incomplete_entities = create_incomplete_extracted_entities()
        populated_form_2 = load_and_populate_form(incomplete_entities, "InsureCo_Ozempic")
        
        metadata_2 = populated_form_2["form_metadata"]
        print(f"✅ Form populated with partial data!")
        print(f"   📊 Completion: {metadata_2['populated_fields_count']}/{metadata_2['total_fields_count']} fields ({metadata_2['completion_rate']:.1%})")
        
        if metadata_2["missing_fields"]:
            print(f"   ❌ Missing required fields: {', '.join(metadata_2['missing_fields'][:5])}...")
        
        # Test 3: Direct service usage
        print(f"\n🎯 Test 3: Direct Service Usage")
        print("-" * 32)
        
        service = FormFillerService()
        schema = service.load_form_schema("InsureCo_Ozempic")
        direct_result = service.populate_form(sample_entities, schema)
        
        print(f"✅ Direct service call successful!")
        print(f"   Schema: {schema['schema_name']} v{schema['schema_version']}")
        print(f"   Drug: {schema['drug_name']}")
        print(f"   Insurer: {schema['insurer_name']}")
        
        # Test 4: Error handling
        print(f"\n🎯 Test 4: Error Handling")
        print("-" * 26)
        
        try:
            # Try to load non-existent schema
            bad_result = load_and_populate_form(sample_entities, "NonExistent_Schema")
        except FormFillerError as e:
            print(f"✅ Error handling works: {e}")
        
        print(f"\n✅ All form filler tests completed successfully!")
        
        return populated_form
        
    except Exception as e:
        print(f"❌ Error testing form filler service: {e}")
        return None

def save_sample_output(populated_form, filename="sample_populated_form.json"):
    """Save a sample populated form to file for inspection."""
    if populated_form:
        try:
            output_path = Path(__file__).parent.parent / "data" / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(populated_form, f, indent=2, ensure_ascii=False)
            print(f"💾 Sample output saved to: {output_path}")
        except Exception as e:
            print(f"⚠️  Could not save sample output: {e}")

def main():
    """Main function to run form filler tests."""
    print("🤖 PriorAuthAutomation - Form Filler Test")
    print("=" * 50)
    
    # Run the main test
    result = test_form_filler_service()
    
    # Save sample output
    if result:
        save_sample_output(result)
    
    print(f"\n🎉 Form filler testing completed!")

if __name__ == "__main__":
    main() 