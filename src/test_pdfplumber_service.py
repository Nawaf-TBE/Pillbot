"""
Test script for pdfplumber extraction functionality.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.parsing_service import extract_with_pdfplumber, perform_combined_parsing, ParsingError


def create_test_extraction_rules():
    """
    Create comprehensive extraction rules for testing pdfplumber functionality.
    
    Returns:
        Dict: Extraction rules for testing
    """
    return {
        "bounding_boxes": {
            # Top-right area for document ID/date
            "header_info": {
                "x0": 400,
                "y0": 720,
                "x1": 550,
                "y1": 780,
                "page": 0
            },
            # Patient information area
            "patient_section": {
                "x0": 80,
                "y0": 640,
                "x1": 300,
                "y1": 720,
                "page": 0
            }
        },
        "table_extraction": {
            "page": 1,  # Check second page for tables
            "table_settings": {},  # Use default pdfplumber table extraction settings
            "columns_of_interest": ["Medication", "Dosage", "Quantity", "Date"]
        },
        "regex_patterns": {
            # Member/Patient ID patterns
            "member_ids": {
                "pattern": r"[A-Z]{2,3}\d{6,9}",
                "flags": 0,
                "page": "all"
            },
            # Date patterns (various formats)
            "dates": {
                "pattern": r"\d{1,2}/\d{1,2}/\d{4}",
                "flags": 0,
                "page": "all"
            },
            # Medication patterns with dosage
            "medications_with_dosage": {
                "pattern": r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\d+(?:\.\d+)?\s*(?:mg|ml|g|mcg)",
                "flags": 0,
                "page": "all"
            },
            # ICD codes
            "icd_codes": {
                "pattern": r"ICD-?10?:?\s*[A-Z]\d{2}(?:\.\d{1,2})?",
                "flags": 0,
                "page": "all"
            },
            # Phone numbers
            "phone_numbers": {
                "pattern": r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
                "flags": 0,
                "page": "all"
            }
        },
        "text_search": {
            # Patient demographic information
            "patient_demographics": {
                "search_terms": ["Patient Name", "DOB", "Date of Birth", "Member ID", "SSN"],
                "context_lines": 2,
                "page": "all"
            },
            # Medical information
            "medical_info": {
                "search_terms": ["Diagnosis", "Condition", "Medical History", "Allergies"],
                "context_lines": 3,
                "page": "all"
            },
            # Prescription information
            "prescription_info": {
                "search_terms": ["Medication", "Prescribing", "Physician", "Doctor", "Provider"],
                "context_lines": 2,
                "page": "all"
            },
            # Insurance and authorization
            "insurance_auth": {
                "search_terms": ["Authorization", "Insurance", "Coverage", "Plan", "Policy"],
                "context_lines": 2,
                "page": "all"
            },
            # Pharmacy information
            "pharmacy_details": {
                "search_terms": ["Pharmacy", "Pharmacist", "Dispensing", "Fill"],
                "context_lines": 2,
                "page": "all"
            }
        }
    }


def test_pdfplumber_extraction():
    """
    Test pdfplumber extraction functionality with sample PDF.
    """
    print("🧪 Testing pdfplumber Extraction Service")
    print("=" * 45)
    
    # First, create a sample PDF for testing
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        test_pdf_path = "test_medical_document.pdf"
        
        # Create a more comprehensive medical document
        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        
        # Page 1 - Prior Authorization Request
        c.drawString(100, 760, "PRIOR AUTHORIZATION REQUEST")
        c.drawString(450, 760, "PA-2023-001")
        c.drawString(450, 740, "12/15/2023")
        
        c.drawString(100, 720, "PATIENT INFORMATION")
        c.drawString(100, 700, "Patient Name: Sarah Johnson")
        c.drawString(100, 680, "DOB: 03/22/1985")
        c.drawString(100, 660, "Member ID: BC987654321")
        c.drawString(100, 640, "SSN: XXX-XX-1234")
        c.drawString(100, 620, "Phone: (555) 123-4567")
        
        c.drawString(100, 580, "DIAGNOSIS")
        c.drawString(100, 560, "Primary: Type 2 Diabetes Mellitus (ICD-10: E11.9)")
        c.drawString(100, 540, "Secondary: Hypertension (ICD-10: I10)")
        
        c.drawString(100, 500, "REQUESTED MEDICATION")
        c.drawString(100, 480, "Medication: Jardiance 25mg")
        c.drawString(100, 460, "Quantity: 90 tablets")
        c.drawString(100, 440, "Days Supply: 90 days")
        c.drawString(100, 420, "Prescribing Physician: Dr. Michael Chen, MD")
        c.drawString(100, 400, "NPI: 1234567890")
        
        c.drawString(100, 360, "PHARMACY INFORMATION")
        c.drawString(100, 340, "Pharmacy: CVS Pharmacy #12345")
        c.drawString(100, 320, "Address: 123 Main St, Anytown, ST 12345")
        c.drawString(100, 300, "Phone: (555) 987-6543")
        c.drawString(100, 280, "Pharmacist: Dr. Lisa Wong, PharmD")
        
        c.showPage()
        
        # Page 2 - Medical History and Lab Results
        c.drawString(100, 760, "MEDICAL HISTORY AND CLINICAL JUSTIFICATION")
        
        c.drawString(100, 720, "PREVIOUS MEDICATIONS TRIED:")
        c.drawString(120, 700, "• Metformin 1000mg BID - Inadequate response")
        c.drawString(120, 680, "• Glipizide 10mg BID - Side effects (hypoglycemia)")
        c.drawString(120, 660, "• Insulin Glargine 20 units - Patient preference for oral")
        
        c.drawString(100, 620, "RECENT LAB RESULTS (Date: 11/30/2023):")
        c.drawString(120, 600, "• HbA1c: 8.2% (Target: <7%)")
        c.drawString(120, 580, "• Fasting Glucose: 165 mg/dL")
        c.drawString(120, 560, "• eGFR: 85 mL/min/1.73m²")
        c.drawString(120, 540, "• Blood Pressure: 140/88 mmHg")
        
        c.drawString(100, 500, "CLINICAL NOTES:")
        c.drawString(100, 480, "Patient has been struggling with glucose control despite")
        c.drawString(100, 460, "lifestyle modifications and current medications.")
        c.drawString(100, 440, "SGLT2 inhibitor therapy is clinically appropriate.")
        
        c.drawString(100, 400, "ALLERGIES:")
        c.drawString(120, 380, "• Sulfa drugs - Rash")
        c.drawString(120, 360, "• Penicillin - Hives")
        
        c.showPage()
        
        # Page 3 - Insurance and Authorization Details
        c.drawString(100, 760, "INSURANCE AND AUTHORIZATION DETAILS")
        
        c.drawString(100, 720, "INSURANCE INFORMATION:")
        c.drawString(120, 700, "Primary Insurance: Blue Cross Blue Shield")
        c.drawString(120, 680, "Plan Type: PPO Gold")
        c.drawString(120, 660, "Group Number: 54321")
        c.drawString(120, 640, "Policy Number: BC987654321-001")
        c.drawString(120, 620, "Effective Date: 01/01/2023")
        
        c.drawString(100, 580, "PRIOR AUTHORIZATION STATUS:")
        c.drawString(120, 560, "Request Date: 12/15/2023")
        c.drawString(120, 540, "Status: Pending Review")
        c.drawString(120, 520, "Expected Decision: 12/18/2023")
        c.drawString(120, 500, "Urgency: Standard")
        
        c.drawString(100, 460, "PRESCRIBER ATTESTATION:")
        c.drawString(100, 440, "I certify that this medication is medically necessary")
        c.drawString(100, 420, "and that alternative therapies have been considered.")
        
        c.drawString(100, 380, "Physician Signature: Dr. Michael Chen, MD")
        c.drawString(100, 360, "Date: 12/15/2023")
        c.drawString(100, 340, "DEA#: BC1234567")
        
        c.drawString(100, 300, "--- END OF PRIOR AUTHORIZATION REQUEST ---")
        
        c.save()
        
        print(f"✅ Created comprehensive test PDF: {test_pdf_path}")
        
    except ImportError:
        print("❌ reportlab not installed. Cannot create test PDF.")
        print("Install with: pip install reportlab")
        return False
    
    # Test pdfplumber extraction
    try:
        print(f"\n🔸 Test 1: pdfplumber Service Availability")
        print("-" * 35)
        
        # Check if pdfplumber is available
        try:
            import pdfplumber
            print("✅ pdfplumber library available")
        except ImportError:
            print("❌ pdfplumber library not available")
            print("Install with: pip install pdfplumber")
            return False
        
        print(f"\n🔸 Test 2: Basic Extraction Rules")
        print("-" * 35)
        
        # Create extraction rules
        extraction_rules = create_test_extraction_rules()
        
        print(f"📋 Extraction rules created:")
        print(f"   Bounding boxes: {len(extraction_rules['bounding_boxes'])}")
        print(f"   Regex patterns: {len(extraction_rules['regex_patterns'])}")
        print(f"   Text searches: {len(extraction_rules['text_search'])}")
        print(f"   Table extraction: {'Yes' if 'table_extraction' in extraction_rules else 'No'}")
        
        print(f"\n🔸 Test 3: pdfplumber Extraction")
        print("-" * 35)
        
        # Perform extraction
        result = extract_with_pdfplumber(test_pdf_path, extraction_rules)
        
        print(f"✅ Extraction completed successfully!")
        print(f"   Processing time: {result['metadata']['processing_time_seconds']} seconds")
        print(f"   Total pages processed: {result['metadata']['total_pages']}")
        
        # Display bounding box results
        bbox_data = result.get("bounding_box_data", {})
        if bbox_data:
            print(f"\n📍 Bounding Box Extractions:")
            for field_name, data in bbox_data.items():
                text = data.get("text", "").strip()
                confidence = data.get("confidence", 0)
                if text:
                    print(f"   {field_name}: '{text}' (confidence: {confidence})")
                else:
                    print(f"   {field_name}: No text found")
        
        # Display regex results
        regex_data = result.get("regex_data", {})
        if regex_data:
            print(f"\n🔍 Regex Pattern Results:")
            for field_name, data in regex_data.items():
                matches = data.get("matches", [])
                print(f"   {field_name}: {len(matches)} matches")
                for i, match in enumerate(matches[:3]):  # Show first 3 matches
                    print(f"      Match {i+1}: '{match['match']}' (page {match['page']})")
                if len(matches) > 3:
                    print(f"      ... and {len(matches) - 3} more")
        
        # Display text search results
        text_search_data = result.get("text_search_data", {})
        if text_search_data:
            print(f"\n🔎 Text Search Results:")
            for field_name, data in text_search_data.items():
                contexts = data.get("contexts", [])
                print(f"   {field_name}: {len(contexts)} contexts found")
                for i, context in enumerate(contexts[:2]):  # Show first 2 contexts
                    print(f"      Context {i+1}: '{context['matched_line'][:60]}...'")
        
        # Display table extraction results
        table_data = result.get("table_data", {})
        if table_data and table_data.get("tables"):
            print(f"\n📊 Table Extraction Results:")
            tables = table_data["tables"]
            print(f"   Found {len(tables)} table(s)")
            for i, table in enumerate(tables):
                headers = table.get("headers", [])
                row_count = table.get("row_count", 0)
                print(f"   Table {i+1}: {len(headers)} columns, {row_count} rows")
                if headers:
                    print(f"      Headers: {', '.join(headers)}")
        
        print(f"\n🔸 Test 4: Combined Parsing")
        print("-" * 35)
        
        # Test combined parsing
        combined_result = perform_combined_parsing(test_pdf_path, extraction_rules)
        
        methods_used = combined_result.get("metadata", {}).get("methods_used", [])
        processing_time = combined_result.get("metadata", {}).get("processing_time_seconds", 0)
        
        print(f"✅ Combined parsing completed!")
        print(f"   Methods used: {', '.join(methods_used)}")
        print(f"   Total processing time: {processing_time} seconds")
        
        # Show cross-validation if available
        cross_validation = combined_result.get("combined_analysis", {}).get("cross_validation", {})
        if cross_validation:
            print(f"\n🔗 Cross-Validation Results:")
            for field, validation in cross_validation.items():
                found = "✅" if validation.get("found_in_markdown", False) else "❌"
                confidence = validation.get("confidence", 0)
                print(f"   {field}: {found} (confidence: {confidence:.1f})")
        
        print(f"\n🎉 All pdfplumber tests completed successfully!")
        
        # Clean up test file
        try:
            os.remove(test_pdf_path)
            print(f"🗑️  Cleaned up test file: {test_pdf_path}")
        except OSError:
            print(f"⚠️  Could not remove test file: {test_pdf_path}")
        
        return True
        
    except ParsingError as e:
        print(f"❌ pdfplumber extraction failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """
    Main function to run pdfplumber tests.
    """
    success = test_pdfplumber_extraction()
    
    if success:
        print(f"\n✅ pdfplumber testing completed successfully!")
    else:
        print(f"\n❌ pdfplumber testing failed. Check dependencies and try again.")
        print(f"\nRequired dependencies:")
        print(f"   pip install pdfplumber reportlab")


if __name__ == "__main__":
    main() 