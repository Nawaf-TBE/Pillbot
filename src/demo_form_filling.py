"""
Demo script showing the complete form filling pipeline.

This script demonstrates how extracted entities would flow through
the form filler service to populate insurance prior authorization forms.
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.form_filler_service import (
    load_and_populate_form, get_form_filler_service_info, 
    check_form_filler_availability
)
from services.data_store import (
    generate_document_id, save_processed_data, save_document_metadata,
    get_processed_data
)

def create_realistic_extracted_entities():
    """
    Create realistic extracted entities that would come from LLM processing
    of a prior authorization document.
    """
    return {
        # Patient Information
        "member_id": "BC123456789",
        "patient_first_name": "Sarah",
        "patient_last_name": "Johnson",
        "patient_date_of_birth": "03/22/1975",
        
        # Prescriber Information
        "prescriber_name": "Dr. Emily Chen",
        "prescriber_npi": "9876543210",
        "prescriber_phone": "(555) 987-6543",
        
        # Diagnosis Information
        "primary_diagnosis_code": "E11.65",
        "primary_diagnosis": "Type 2 diabetes mellitus with hyperglycemia",
        
        # Medication Information
        "requested_drug_name": "Ozempic",
        "requested_strength": "0.5 mg/dose",
        "quantity_requested": "1.5 ml pen",
        "days_supply": "30",
        
        # Pharmacy Information
        "pharmacy_name": "Central Health Pharmacy",
        
        # Clinical Information
        "a1c_value": "9.2%",
        "bmi_value": "29.8",
        "previous_medications_tried": "Metformin 1000mg BID, Glipizide 10mg daily - inadequate glycemic control",
        "contraindications_present": "No",
        "clinical_justification": "Patient with poorly controlled Type 2 diabetes mellitus with recent HbA1c of 9.2% despite optimal doses of metformin and sulfonylurea. Patient requires GLP-1 receptor agonist therapy to achieve glycemic target. No contraindications to semaglutide therapy."
    }

def create_partial_extracted_entities():
    """
    Create extracted entities with some missing fields to demonstrate
    handling of incomplete data.
    """
    return {
        # Limited information available
        "member_id": "XY987654321",
        "patient_first_name": "Michael",
        "patient_last_name": "Rodriguez",
        "prescriber_name": "Dr. James Wilson",
        "primary_diagnosis": "Diabetes mellitus, type 2",
        "requested_drug_name": "Ozempic",
        "a1c_value": "8.7"
        # Missing: DOB, NPI, diagnosis code, strength, etc.
    }

def demo_form_filling_pipeline():
    """Demonstrate the complete form filling pipeline."""
    print("🚀 Form Filling Pipeline Demo")
    print("=" * 50)
    
    # Check service availability
    if not check_form_filler_availability():
        print("❌ Form filler service not available")
        return
    
    # Generate a demo document ID
    doc_id = generate_document_id()
    print(f"📄 Processing demo document: {doc_id[:8]}...")
    
    # Save mock document metadata
    save_document_metadata(doc_id, {
        "filename": "demo_prior_auth.pdf",
        "processing_type": "demo",
        "status": "processing"
    })
    
    print(f"\n🎯 Scenario 1: Complete Entity Data")
    print("-" * 40)
    
    # Test with complete extracted entities
    complete_entities = create_realistic_extracted_entities()
    
    # Save mock entity extraction results
    entity_extraction_result = {
        "extracted_entities": complete_entities,
        "validation": {
            "validation_report": {
                "populated_fields": 19,
                "total_fields": 20,
                "confidence_score": 0.89
            }
        },
        "metadata": {
            "processing_time_seconds": 2.3,
            "model_used": "gemini-1.5-flash"
        }
    }
    save_processed_data(doc_id, "llm_entity_extraction", entity_extraction_result)
    
    # Perform form filling
    try:
        populated_form = load_and_populate_form(complete_entities, "InsureCo_Ozempic")
        
        # Save form filling results
        save_processed_data(doc_id, "form_filling_InsureCo_Ozempic", populated_form)
        
        form_metadata = populated_form["form_metadata"]
        print(f"✅ Form populated successfully!")
        print(f"   📋 Schema: {form_metadata['schema_name']} v{form_metadata['schema_version']}")
        print(f"   📊 Completion: {form_metadata['populated_fields_count']}/{form_metadata['total_fields_count']} fields ({form_metadata['completion_rate']:.1%})")
        
        if form_metadata["missing_fields"]:
            print(f"   ⚠️  Missing required fields: {len(form_metadata['missing_fields'])}")
        
        # Show key populated fields
        form_data = populated_form["form_data"]
        key_fields = ["member_id", "patient_first_name", "patient_last_name", "primary_diagnosis_description", "requested_drug_name"]
        
        print(f"\n   📝 Key populated fields:")
        for field in key_fields:
            if field in form_data and form_data[field]["value"]:
                value = form_data[field]["value"]
                confidence = form_data[field]["confidence"]
                print(f"      {field}: {value} (confidence: {confidence})")
        
        # Show form sections summary
        if "form_sections" in populated_form:
            print(f"\n   📋 Form sections completion:")
            for section_name, section_data in populated_form["form_sections"].items():
                populated = section_data["section_metadata"]["populated_fields"]
                total = section_data["section_metadata"]["total_fields"]
                completion = populated / total if total > 0 else 0
                status = "✅" if completion == 1.0 else "⚠️" if completion > 0.5 else "❌"
                print(f"      {status} {section_data['title']}: {populated}/{total} ({completion:.1%})")
        
        save_document_metadata(doc_id, {"status": "form_filling_completed"})
        
    except Exception as e:
        print(f"❌ Form filling failed: {e}")
        save_processed_data(doc_id, "form_filling_error", {"error": str(e)})
    
    print(f"\n🎯 Scenario 2: Partial Entity Data")
    print("-" * 38)
    
    # Test with partial extracted entities
    partial_entities = create_partial_extracted_entities()
    doc_id_2 = generate_document_id()
    
    save_document_metadata(doc_id_2, {
        "filename": "demo_partial_prior_auth.pdf",
        "processing_type": "demo_partial",
        "status": "processing"
    })
    
    try:
        populated_form_2 = load_and_populate_form(partial_entities, "InsureCo_Ozempic")
        
        # Save form filling results
        save_processed_data(doc_id_2, "form_filling_InsureCo_Ozempic", populated_form_2)
        
        form_metadata_2 = populated_form_2["form_metadata"]
        print(f"✅ Partial form populated!")
        print(f"   📊 Completion: {form_metadata_2['populated_fields_count']}/{form_metadata_2['total_fields_count']} fields ({form_metadata_2['completion_rate']:.1%})")
        
        if form_metadata_2["missing_fields"]:
            missing_count = len(form_metadata_2["missing_fields"])
            print(f"   ❌ Missing required fields: {missing_count}")
            # Show first few missing fields
            missing_sample = form_metadata_2["missing_fields"][:5]
            print(f"      Sample missing: {', '.join(missing_sample)}")
        
        save_document_metadata(doc_id_2, {"status": "form_filling_completed_partial"})
        
    except Exception as e:
        print(f"❌ Partial form filling failed: {e}")
    
    print(f"\n📊 Pipeline Summary")
    print("-" * 20)
    print(f"✅ Form filler service: Available")
    print(f"✅ Schema loaded: InsureCo_Ozempic")
    print(f"✅ Complete scenario: {form_metadata['completion_rate']:.1%} completion")
    print(f"✅ Partial scenario: {form_metadata_2['completion_rate']:.1%} completion")
    print(f"📁 Results saved to data store")
    
    # Show service info
    service_info = get_form_filler_service_info()
    print(f"\n🔧 Service Features:")
    for feature in service_info['supported_features'][:3]:
        print(f"   • {feature}")
    
    return doc_id, doc_id_2

def show_saved_form_data(doc_id: str):
    """Display the saved form data for inspection."""
    try:
        form_data = get_processed_data(doc_id, "form_filling_InsureCo_Ozempic")
        
        print(f"\n📄 Saved Form Data for {doc_id[:8]}...")
        print("-" * 40)
        
        # Show form metadata
        metadata = form_data["form_metadata"]
        print(f"Form: {metadata['schema_name']}")
        print(f"Populated: {metadata['population_timestamp']}")
        print(f"Completion: {metadata['completion_rate']:.1%}")
        
        # Show a few populated fields
        fields = form_data["form_data"]
        print(f"\nSample populated fields:")
        count = 0
        for field_name, field_info in fields.items():
            if field_info["value"] and count < 3:
                print(f"  {field_name}: {field_info['value']}")
                count += 1
        
    except Exception as e:
        print(f"Could not retrieve form data: {e}")

def main():
    """Main demo function."""
    print("🤖 PriorAuthAutomation - Form Filling Demo")
    print("=" * 55)
    
    doc_id_1, doc_id_2 = demo_form_filling_pipeline()
    
    # Show some saved data
    show_saved_form_data(doc_id_1)
    
    print(f"\n🎉 Form filling demo completed!")
    print(f"📁 Check the data/ directory for saved results")

if __name__ == "__main__":
    main() 