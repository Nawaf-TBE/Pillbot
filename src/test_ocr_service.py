"""
Test script for OCR service functionality.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ocr_service import (
    perform_mistral_ocr, check_ocr_availability, get_ocr_service_info, OCRError
)
from services.data_store import (
    generate_document_id, save_document_metadata, save_processed_data
)


def create_sample_scanned_pdf():
    """
    Create a sample PDF that simulates a scanned document for OCR testing.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        sample_pdf_path = "sample_scanned_test.pdf"
        
        # Create a simple PDF with embedded images (simulating scanned pages)
        c = canvas.Canvas(sample_pdf_path, pagesize=letter)
        
        # Create a simple image with text (simulating a scanned page)
        img_width, img_height = 600, 400
        img = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw some text that looks like a medical document
        try:
            # Try to use default font
            font = ImageFont.load_default()
        except:
            font = None
        
        text_lines = [
            "PRIOR AUTHORIZATION REQUEST",
            "",
            "Patient Name: Jane Smith",
            "Date of Birth: March 22, 1985",
            "Member ID: BC-12345-6789",
            "",
            "Requested Medication: Adalimumab",
            "Diagnosis: Rheumatoid Arthritis",
            "Prescribing Physician: Dr. Robert Johnson",
            "",
            "Clinical Information:",
            "Patient has been diagnosed with moderate to severe",
            "rheumatoid arthritis and has failed conventional DMARDs.",
            "Requesting approval for Adalimumab therapy.",
        ]
        
        y_position = 20
        for line in text_lines:
            if line:  # Skip empty lines
                draw.text((20, y_position), line, fill='black', font=font)
            y_position += 25
        
        # Save image to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Add image to PDF
        c.drawImage(img_bytes, 50, 200, width=500, height=300)
        c.showPage()
        
        # Add a second page
        img2 = Image.new('RGB', (img_width, img_height), color='white')
        draw2 = ImageDraw.Draw(img2)
        
        text_lines_2 = [
            "SUPPORTING DOCUMENTATION",
            "",
            "Lab Results:",
            "ESR: 45 mm/hr (elevated)",
            "CRP: 12 mg/L (elevated)",
            "RF: Positive",
            "",
            "Previous Treatments:",
            "- Methotrexate (inadequate response)",
            "- Sulfasalazine (side effects)",
            "- Hydroxychloroquine (inadequate response)",
            "",
            "Physician Signature: Dr. Robert Johnson",
            "Date: January 15, 2024",
        ]
        
        y_position = 20
        for line in text_lines_2:
            if line:
                draw2.text((20, y_position), line, fill='black', font=font)
            y_position += 25
        
        img_bytes_2 = io.BytesIO()
        img2.save(img_bytes_2, format='PNG')
        img_bytes_2.seek(0)
        
        c.drawImage(img_bytes_2, 50, 200, width=500, height=300)
        c.save()
        
        print(f"✅ Created sample scanned PDF: {sample_pdf_path}")
        return sample_pdf_path
        
    except ImportError as e:
        print(f"⚠️  Cannot create sample PDF: {e}")
        print("Install with: pip install reportlab Pillow")
        return None
    except Exception as e:
        print(f"❌ Error creating sample PDF: {e}")
        return None


def test_ocr_service():
    """
    Test the OCR service functionality.
    """
    print("🧪 Testing OCR Service")
    print("=" * 30)
    
    # Test 1: Check service availability
    print("\n🔸 Test 1: Service Availability")
    print("-" * 30)
    
    is_available = check_ocr_availability()
    print(f"OCR Service Available: {'✅ Yes' if is_available else '❌ No'}")
    
    # Display service information
    service_info = get_ocr_service_info()
    print(f"Service: {service_info['service_name']}")
    print(f"Model: {service_info['model']}")
    print(f"API Key Configured: {'✅' if service_info['api_key_configured'] else '❌'}")
    print(f"Timeout: {service_info['timeout']} seconds")
    print(f"Max Retries: {service_info['max_retries']}")
    print(f"Supported Formats: {', '.join(service_info['supported_formats'])}")
    
    if not is_available:
        print("\n⚠️  OCR service is not available.")
        print("To test OCR functionality:")
        print("1. Set MISTRAL_API_KEY environment variable")
        print("2. Ensure you have Mistral API access")
        print("3. Re-run this test")
        return
    
    # Test 2: Create and process sample document
    print("\n🔸 Test 2: OCR Processing")
    print("-" * 25)
    
    sample_pdf = create_sample_scanned_pdf()
    if not sample_pdf:
        print("❌ Cannot test OCR without sample PDF")
        return
    
    try:
        print(f"📄 Processing: {sample_pdf}")
        
        # Generate document ID for tracking
        doc_id = generate_document_id()
        print(f"📋 Document ID: {doc_id[:8]}...")
        
        # Save initial metadata
        save_document_metadata(doc_id, {
            "file_path": sample_pdf,
            "original_filename": sample_pdf,
            "status": "ocr_processing",
            "document_type": "scanned_pdf"
        })
        
        # Perform OCR
        print("🔍 Starting OCR processing...")
        ocr_result = perform_mistral_ocr(sample_pdf)
        
        # Save OCR results
        save_processed_data(doc_id, "ocr", ocr_result)
        
        # Display results
        print("✅ OCR processing completed!")
        print(f"   Extracted text length: {len(ocr_result.get('extracted_text', ''))} characters")
        print(f"   Confidence score: {ocr_result.get('confidence', 'N/A')}")
        print(f"   Total pages processed: {ocr_result.get('metadata', {}).get('total_pages', 'N/A')}")
        print(f"   Processing time: {ocr_result.get('metadata', {}).get('processing_time_seconds', 'N/A')} seconds")
        print(f"   OCR method: {ocr_result.get('metadata', {}).get('ocr_method', 'N/A')}")
        
        # Show sample of extracted text
        extracted_text = ocr_result.get('extracted_text', '')
        if extracted_text:
            print(f"\n📝 Sample extracted text (first 200 characters):")
            print(f"   {extracted_text[:200]}...")
        
        # Update final status
        save_document_metadata(doc_id, {"status": "ocr_completed"})
        
        print(f"\n🎉 OCR test completed successfully!")
        
    except OCRError as e:
        print(f"❌ OCR Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Clean up sample file
        try:
            if sample_pdf and os.path.exists(sample_pdf):
                os.remove(sample_pdf)
                print(f"🗑️  Cleaned up sample file: {sample_pdf}")
        except OSError:
            print(f"⚠️  Could not remove sample file: {sample_pdf}")


def demo_ocr_workflow():
    """
    Demonstrate a complete OCR workflow for prior authorization documents.
    """
    print("\n" + "=" * 60)
    print("🏥 Demo: OCR Workflow for Prior Authorization Documents")
    print("=" * 60)
    
    if not check_ocr_availability():
        print("❌ OCR service not available. Please configure MISTRAL_API_KEY.")
        return
    
    print("📋 This demo simulates processing a scanned prior authorization form")
    print("    that would typically require OCR for text extraction.")
    
    sample_pdf = create_sample_scanned_pdf()
    if not sample_pdf:
        print("❌ Cannot run demo without sample PDF")
        return
    
    try:
        doc_id = generate_document_id()
        
        # Step 1: Document received
        print("\n📥 Step 1: Scanned document received")
        save_document_metadata(doc_id, {
            "file_path": sample_pdf,
            "document_type": "prior_authorization_request",
            "status": "received",
            "requires_ocr": True
        })
        print(f"   Document {doc_id[:8]}... stored")
        
        # Step 2: OCR Processing
        print("\n🔍 Step 2: OCR text extraction")
        ocr_result = perform_mistral_ocr(sample_pdf)
        save_processed_data(doc_id, "ocr", ocr_result)
        save_document_metadata(doc_id, {"status": "ocr_completed"})
        print(f"   Extracted {len(ocr_result.get('extracted_text', ''))} characters")
        
        # Step 3: Text analysis (simulated)
        print("\n📊 Step 3: Text analysis and entity extraction")
        extracted_text = ocr_result.get('extracted_text', '')
        
        # Simple keyword extraction (in real implementation, this would use NLP)
        entities = {}
        if 'Jane Smith' in extracted_text:
            entities['patient_name'] = 'Jane Smith'
        if 'Adalimumab' in extracted_text:
            entities['medication'] = 'Adalimumab'
        if 'Rheumatoid Arthritis' in extracted_text:
            entities['diagnosis'] = 'Rheumatoid Arthritis'
        if 'Dr. Robert Johnson' in extracted_text:
            entities['physician'] = 'Dr. Robert Johnson'
        
        save_processed_data(doc_id, "entities", entities)
        save_document_metadata(doc_id, {"status": "entities_extracted"})
        print(f"   Extracted {len(entities)} key entities")
        
        # Step 4: Completion
        print("\n✅ Step 4: Processing complete")
        save_document_metadata(doc_id, {
            "status": "completed",
            "processing_completed_at": "2024-01-15T14:30:00"
        })
        
        # Summary
        print("\n📊 Processing Summary")
        print("-" * 25)
        print(f"Document ID: {doc_id[:8]}...")
        print(f"Total processing time: {ocr_result.get('metadata', {}).get('processing_time_seconds', 'N/A')} seconds")
        print(f"Extracted entities: {list(entities.keys())}")
        print(f"Text confidence: {ocr_result.get('confidence', 'N/A')}")
        
        print("\n🎯 OCR workflow demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        # Clean up
        try:
            if sample_pdf and os.path.exists(sample_pdf):
                os.remove(sample_pdf)
                print(f"🗑️  Cleaned up demo file")
        except OSError:
            pass


def main():
    """
    Main function to run OCR tests and demo.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--demo-only":
        demo_ocr_workflow()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        test_ocr_service()
    else:
        test_ocr_service()
        demo_ocr_workflow()


if __name__ == "__main__":
    main() 