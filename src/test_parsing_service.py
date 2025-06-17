"""
Test script for LlamaParse parsing service functionality.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.parsing_service import (
    perform_llamaparse, perform_llamaparse_with_metadata, 
    check_parsing_availability, get_parsing_service_info,
    analyze_prior_auth_document, extract_document_sections, ParsingError
)
from services.data_store import (
    generate_document_id, save_document_metadata, save_processed_data
)


def create_sample_medical_pdf():
    """
    Create a sample medical PDF document for parsing tests.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        sample_pdf_path = "sample_medical_document.pdf"
        
        # Create a simple PDF with medical content
        c = canvas.Canvas(sample_pdf_path, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "PRIOR AUTHORIZATION REQUEST")
        
        # Patient Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 100, "Patient Information")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 120, "Patient Name: Jane Smith")
        c.drawString(50, height - 135, "Date of Birth: March 22, 1985")
        c.drawString(50, height - 150, "Member ID: BC-12345-6789")
        c.drawString(50, height - 165, "Phone: (555) 123-4567")
        
        # Medication Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 200, "Requested Medication")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 220, "Medication Name: Adalimumab (Humira)")
        c.drawString(50, height - 235, "Strength: 40 mg/0.8 mL")
        c.drawString(50, height - 250, "Quantity: 2 pens (30-day supply)")
        c.drawString(50, height - 265, "Directions: Inject 40 mg subcutaneously every other week")
        
        # Clinical Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 300, "Clinical Information")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 320, "Primary Diagnosis: Rheumatoid Arthritis (ICD-10: M06.9)")
        c.drawString(50, height - 340, "Clinical Justification:")
        c.drawString(50, height - 355, "Patient has been diagnosed with moderate to severe rheumatoid arthritis.")
        c.drawString(50, height - 370, "She has failed conventional DMARDs including:")
        c.drawString(70, height - 385, "• Methotrexate - inadequate response after 3 months")
        c.drawString(70, height - 400, "• Sulfasalazine - discontinued due to GI side effects")
        c.drawString(70, height - 415, "• Hydroxychloroquine - inadequate response after 6 months")
        
        # Provider Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 450, "Prescribing Physician")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 470, "Physician Name: Dr. Robert Johnson, MD")
        c.drawString(50, height - 485, "Specialty: Rheumatology")
        c.drawString(50, height - 500, "NPI Number: 1234567890")
        c.drawString(50, height - 515, "Phone: (555) 987-6543")
        c.drawString(50, height - 530, "Date of Request: January 15, 2024")
        
        c.save()
        
        print(f"✅ Created sample medical PDF: {sample_pdf_path}")
        return sample_pdf_path
        
    except ImportError as e:
        print(f"⚠️  Cannot create sample PDF: {e}")
        print("Install with: pip install reportlab")
        return None
    except Exception as e:
        print(f"❌ Error creating sample PDF: {e}")
        return None


def test_parsing_service():
    """
    Test the LlamaParse parsing service functionality.
    """
    print("🧪 Testing LlamaParse Service")
    print("=" * 35)
    
    # Test 1: Check service availability
    print("\n🔸 Test 1: Service Availability")
    print("-" * 30)
    
    is_available = check_parsing_availability()
    print(f"Parsing Service Available: {'✅ Yes' if is_available else '❌ No'}")
    
    # Display service information
    service_info = get_parsing_service_info()
    print(f"Service: {service_info['service_name']}")
    print(f"Output Format: {service_info['output_format']}")
    print(f"API Key Configured: {'✅' if service_info['api_key_configured'] else '❌'}")
    print(f"Timeout: {service_info['timeout_seconds']} seconds")
    print(f"Supported Formats: {', '.join(service_info['supported_formats'])}")
    
    if not is_available:
        print("\n⚠️  Parsing service is not available.")
        print("To test parsing functionality:")
        print("1. Set LLAMAPARSE_API_KEY environment variable")
        print("2. Ensure you have LlamaParse API access")
        print("3. Re-run this test")
        return
    
    # Test 2: Create and process sample document
    print("\n🔸 Test 2: Document Parsing")
    print("-" * 27)
    
    sample_pdf = create_sample_medical_pdf()
    if not sample_pdf:
        print("❌ Cannot test parsing without sample PDF")
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
            "status": "parsing_processing",
            "document_type": "medical_document"
        })
        
        # Perform parsing with metadata
        print("🔍 Starting document parsing...")
        parsing_result = perform_llamaparse_with_metadata(sample_pdf)
        
        # Save parsing results
        save_processed_data(doc_id, "parsing", parsing_result)
        
        # Display results
        print("✅ Document parsing completed!")
        metadata = parsing_result['metadata']
        content_stats = metadata['content_stats']
        
        print(f"   Content length: {content_stats['total_characters']} characters")
        print(f"   Word count: {content_stats['word_count']}")
        print(f"   Processing time: {metadata['processing_time_seconds']} seconds")
        
        # Show sample content
        markdown_content = parsing_result['markdown_content']
        if markdown_content:
            print(f"\n📝 Sample content (first 300 characters):")
            print(f"   {markdown_content[:300]}...")
        
        # Test 3: Prior Authorization Analysis
        print("\n🔸 Test 3: Prior Auth Analysis")
        print("-" * 30)
        
        pa_analysis = analyze_prior_auth_document(markdown_content)
        save_processed_data(doc_id, "prior_auth_analysis", pa_analysis)
        
        print(f"Document Type: {pa_analysis['document_type']}")
        print(f"Confidence: {pa_analysis['confidence']:.2f}")
        print(f"Key fields found: {len(pa_analysis['key_fields_found'])}")
        
        if pa_analysis['entities']:
            print(f"Extracted entities:")
            for entity, value in pa_analysis['entities'].items():
                print(f"   {entity}: {value}")
        
        # Update final status
        save_document_metadata(doc_id, {"status": "parsing_completed"})
        
        print(f"\n🎉 Parsing test completed successfully!")
        
    except ParsingError as e:
        print(f"❌ Parsing Error: {e}")
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


def main():
    """
    Main function to run parsing tests.
    """
    test_parsing_service()


if __name__ == "__main__":
    main() 