"""
Test script for data_store.py functionality.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.data_store import (
    generate_document_id,
    save_document_metadata,
    get_document_metadata,
    save_processed_data,
    get_processed_data,
    get_all_processed_data,
    list_documents,
    delete_document_data,
    get_document_stages
)


def test_data_store():
    """
    Test all data store functionality.
    """
    print("🧪 Testing Data Store Functionality")
    print("=" * 50)
    
    # Generate a test document ID
    doc_id = generate_document_id()
    print(f"📄 Generated document ID: {doc_id}")
    
    try:
        # Test 1: Save and retrieve document metadata
        print("\n🔸 Test 1: Document Metadata")
        print("-" * 30)
        
        metadata = {
            "file_path": "/path/to/document.pdf",
            "is_native_pdf": True,
            "status": "processing",
            "file_size_mb": 2.5,
            "original_filename": "medical_record.pdf"
        }
        
        save_document_metadata(doc_id, metadata)
        print("✅ Saved document metadata")
        
        retrieved_metadata = get_document_metadata(doc_id)
        print("✅ Retrieved document metadata:")
        for key, value in retrieved_metadata.items():
            print(f"   {key}: {value}")
        
        # Test 2: Save and retrieve processed data for different stages
        print("\n🔸 Test 2: Processed Data - Multiple Stages")
        print("-" * 40)
        
        # Stage 1: OCR output
        ocr_data = {
            "text": "Patient Name: John Doe\nDOB: 01/15/1980\nDiagnosis: Hypertension",
            "confidence": 0.95,
            "pages_processed": 3
        }
        save_processed_data(doc_id, "ocr", ocr_data)
        print("✅ Saved OCR stage data")
        
        # Stage 2: Parsed entities
        entities_data = {
            "patient_name": "John Doe",
            "date_of_birth": "1980-01-15",
            "diagnosis": "Hypertension",
            "extracted_entities": ["PERSON", "DATE", "MEDICAL_CONDITION"]
        }
        save_processed_data(doc_id, "entities", entities_data)
        print("✅ Saved entities stage data")
        
        # Stage 3: Classification
        classification_data = {
            "document_type": "medical_record",
            "confidence": 0.88,
            "categories": ["patient_info", "diagnosis", "treatment"]
        }
        save_processed_data(doc_id, "classification", classification_data)
        print("✅ Saved classification stage data")
        
        # Test 3: Retrieve specific stage data
        print("\n🔸 Test 3: Retrieve Specific Stage Data")
        print("-" * 40)
        
        ocr_retrieved = get_processed_data(doc_id, "ocr")
        print("✅ Retrieved OCR data:")
        print(f"   Text preview: {ocr_retrieved['text'][:50]}...")
        print(f"   Confidence: {ocr_retrieved['confidence']}")
        
        entities_retrieved = get_processed_data(doc_id, "entities")
        print("✅ Retrieved entities data:")
        print(f"   Patient: {entities_retrieved['patient_name']}")
        print(f"   DOB: {entities_retrieved['date_of_birth']}")
        print(f"   Diagnosis: {entities_retrieved['diagnosis']}")
        
        # Test 4: Get all processed data
        print("\n🔸 Test 4: Get All Processed Data")
        print("-" * 35)
        
        all_data = get_all_processed_data(doc_id)
        print("✅ Retrieved all processed data:")
        print(f"   Document ID: {all_data['document_id']}")
        print(f"   Created: {all_data['created_at']}")
        print(f"   Last updated: {all_data['updated_at']}")
        print(f"   Available stages: {list(all_data.keys())}")
        
        # Test 5: Get document stages
        print("\n🔸 Test 5: Get Document Stages")
        print("-" * 30)
        
        stages = get_document_stages(doc_id)
        print(f"✅ Document stages: {stages}")
        
        # Test 6: List all documents
        print("\n🔸 Test 6: List All Documents")
        print("-" * 30)
        
        all_docs = list_documents()
        print(f"✅ Found {len(all_docs)} document(s):")
        for doc in all_docs[-3:]:  # Show last 3 documents
            print(f"   - {doc}")
        
        # Test 7: Error handling
        print("\n🔸 Test 7: Error Handling")
        print("-" * 25)
        
        # Try to get non-existent stage
        try:
            get_processed_data(doc_id, "non_existent_stage")
        except KeyError as e:
            print(f"✅ Correctly caught KeyError: {e}")
        
        # Try to get data for non-existent document
        try:
            get_document_metadata("non-existent-doc-id")
        except FileNotFoundError as e:
            print(f"✅ Correctly caught FileNotFoundError: File not found")
        
        # Test 8: Update existing metadata
        print("\n🔸 Test 8: Update Metadata")
        print("-" * 25)
        
        updated_metadata = {
            "status": "completed",
            "processing_time_seconds": 45.2,
            "pages_count": 3
        }
        save_document_metadata(doc_id, updated_metadata)
        
        final_metadata = get_document_metadata(doc_id)
        print("✅ Updated metadata:")
        print(f"   Status: {final_metadata['status']}")
        print(f"   Processing time: {final_metadata['processing_time_seconds']}s")
        print(f"   Created: {final_metadata['created_at']}")
        print(f"   Updated: {final_metadata['updated_at']}")
        
        print("\n🎉 All tests completed successfully!")
        
        # Optional: Clean up test data
        print(f"\n🗑️  Cleaning up test data for document: {doc_id}")
        delete_document_data(doc_id)
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        # Clean up on error
        try:
            delete_document_data(doc_id)
            print("🗑️  Cleaned up test data after error")
        except:
            pass


def demo_workflow():
    """
    Demonstrate a realistic workflow using the data store.
    """
    print("\n" + "=" * 60)
    print("🏥 Demo: Prior Authorization Document Processing Workflow")
    print("=" * 60)
    
    # Simulate processing a prior authorization document
    doc_id = generate_document_id()
    
    try:
        # Step 1: Document received
        print("📥 Step 1: Document received")
        metadata = {
            "file_path": "uploads/prior_auth_request_123.pdf",
            "original_filename": "prior_auth_request_123.pdf",
            "status": "received",
            "file_size_mb": 3.2,
            "uploaded_at": "2024-01-15T10:30:00"
        }
        save_document_metadata(doc_id, metadata)
        print(f"   Document {doc_id[:8]}... received and stored")
        
        # Step 2: PDF analysis
        print("\n🔍 Step 2: PDF analysis")
        pdf_analysis = {
            "is_native_pdf": True,
            "page_count": 5,
            "has_selectable_text": True,
            "analysis_confidence": 0.99
        }
        save_processed_data(doc_id, "pdf_analysis", pdf_analysis)
        save_document_metadata(doc_id, {"status": "analyzed"})
        print("   PDF analysis completed - native PDF with selectable text")
        
        # Step 3: Text extraction
        print("\n📝 Step 3: Text extraction")
        extracted_text = {
            "full_text": "PRIOR AUTHORIZATION REQUEST\nPatient: Jane Smith\nDOB: 03/22/1985\nRequested Medication: Adalimumab...",
            "page_texts": ["Page 1 content...", "Page 2 content...", "Page 3 content..."],
            "extraction_method": "direct_pdf",
            "word_count": 1250
        }
        save_processed_data(doc_id, "text_extraction", extracted_text)
        save_document_metadata(doc_id, {"status": "text_extracted"})
        print("   Text extraction completed - 1250 words extracted")
        
        # Step 4: Entity extraction
        print("\n🏷️  Step 4: Entity extraction")
        entities = {
            "patient_name": "Jane Smith",
            "date_of_birth": "1985-03-22",
            "medication": "Adalimumab",
            "diagnosis": "Rheumatoid Arthritis",
            "physician": "Dr. Robert Johnson",
            "insurance_id": "BC-12345-6789",
            "prior_auth_number": "PA-2024-001234"
        }
        save_processed_data(doc_id, "entities", entities)
        save_document_metadata(doc_id, {"status": "entities_extracted"})
        print("   Key entities extracted and structured")
        
        # Step 5: Validation and completion
        print("\n✅ Step 5: Validation and completion")
        validation = {
            "all_required_fields": True,
            "data_quality_score": 0.95,
            "validation_errors": [],
            "ready_for_processing": True
        }
        save_processed_data(doc_id, "validation", validation)
        save_document_metadata(doc_id, {
            "status": "completed",
            "processing_completed_at": "2024-01-15T10:35:22"
        })
        print("   Document processing completed successfully")
        
        # Show final summary
        print("\n📊 Final Processing Summary")
        print("-" * 30)
        final_metadata = get_document_metadata(doc_id)
        stages = get_document_stages(doc_id)
        
        print(f"Document ID: {doc_id[:8]}...")
        print(f"Status: {final_metadata['status']}")
        print(f"Processing stages: {', '.join(stages)}")
        print(f"Patient: {get_processed_data(doc_id, 'entities')['patient_name']}")
        print(f"Medication: {get_processed_data(doc_id, 'entities')['medication']}")
        
        print("\n🎯 Demo workflow completed successfully!")
        
        # Clean up demo data
        print(f"\n🗑️  Cleaning up demo data...")
        delete_document_data(doc_id)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        try:
            delete_document_data(doc_id)
        except:
            pass


def main():
    """
    Main function to run tests and demo.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--demo-only":
        demo_workflow()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        test_data_store()
    else:
        test_data_store()
        demo_workflow()


if __name__ == "__main__":
    main() 