#!/usr/bin/env python3
"""
Demo script for Patient Data Extractor

This script demonstrates how to use the PatientDataExtractor to:
1. Analyze a blank form and generate a schema
2. Extract patient data from filled documents
3. Generate clean output reports

Usage:
    python demo_patient_extractor.py
"""

import os
import logging
from pathlib import Path
from patient_extractor import PatientDataExtractor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demo_schema_generation():
    """Demo: Generate schema from a blank form"""
    print("🏥 " + "="*80)
    print("   DEMO 1: SCHEMA GENERATION FROM BLANK FORM")
    print("="*88)
    
    # Initialize extractor
    extractor = PatientDataExtractor()
    
    # Check if we have any PDF files in the data directory
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if pdf_files:
        # Use the first PDF found as an example blank form
        blank_form_path = pdf_files[0]
        print(f"📋 Using sample form: {blank_form_path.name}")
        
        try:
            # Generate schema from the blank form
            schema = extractor.analyze_blank_form(str(blank_form_path), "demo_patient_intake")
            
            print(f"\n✅ Schema generated successfully!")
            print(f"   📝 Name: {schema.schema_name}")
            print(f"   📊 Fields: {len(schema.fields)}")
            print(f"   📄 Description: {schema.description}")
            print(f"   📅 Created: {schema.created_date}")
            
            # Show some sample fields
            print(f"\n📋 Sample fields identified:")
            field_count = 0
            for field_name, field_config in schema.fields.items():
                if field_count >= 10:  # Show only first 10 fields
                    break
                required_marker = "🔴" if field_config.get("required") else "🔵"
                print(f"   {required_marker} {field_name} ({field_config['type']}) - {field_config['description']}")
                field_count += 1
            
            if len(schema.fields) > 10:
                print(f"   ... and {len(schema.fields) - 10} more fields")
            
            return schema.schema_name
            
        except Exception as e:
            print(f"❌ Error generating schema: {e}")
            return None
    else:
        print("❌ No PDF files found in data directory for schema generation demo")
        return None

def demo_data_extraction(schema_name=None):
    """Demo: Extract data from a filled document"""
    print("\n🔍 " + "="*80)
    print("   DEMO 2: PATIENT DATA EXTRACTION")
    print("="*88)
    
    # Initialize extractor
    extractor = PatientDataExtractor()
    
    # Check available schemas
    schemas = extractor.list_schemas()
    if not schemas and not schema_name:
        print("❌ No schemas available. Run schema generation first.")
        return
    
    if schema_name and schema_name in schemas:
        use_schema = schema_name
    elif schemas:
        use_schema = schemas[0]  # Use first available schema
    else:
        use_schema = None
    
    # Look for a document to extract from (different from the blank form)
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    # Try to find a filled document (prefer processed documents)
    filled_document = None
    for pdf_file in pdf_files:
        # Skip form templates and use other PDFs as example filled documents
        if "template" not in pdf_file.name.lower() and "blank" not in pdf_file.name.lower():
            filled_document = pdf_file
            break
    
    if not filled_document and pdf_files:
        # If no other documents, use any PDF as a demo
        filled_document = pdf_files[0]
    
    if filled_document:
        print(f"📄 Extracting data from: {filled_document.name}")
        
        if use_schema:
            print(f"🎯 Using schema: {use_schema}")
        else:
            print("🎯 Using most recent schema")
        
        try:
            # Extract patient data
            results = extractor.extract_patient_data(
                str(filled_document),
                use_schema,
                "markdown"
            )
            
            print(f"\n✅ Extraction completed!")
            print(f"   📊 Success Rate: {results['success_rate']:.1f}%")
            print(f"   📝 Fields Extracted: {results['extracted_count']}/{results['total_fields']}")
            print(f"   🎯 Schema Used: {results['schema_used']}")
            print(f"   📅 Timestamp: {results['extraction_timestamp']}")
            
            # Show a preview of the generated report
            output_lines = results['output_document'].split('\n')
            preview_lines = output_lines[:25]  # First 25 lines
            
            print(f"\n📄 Generated Report Preview:")
            print("─" * 80)
            for line in preview_lines:
                print(line)
            
            if len(output_lines) > 25:
                print("...")
                print(f"[Report contains {len(output_lines)} total lines]")
            
            print("─" * 80)
            print(f"💾 Full results saved to: data/patient_extraction/")
            
            return results
            
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            return None
    else:
        print("❌ No suitable documents found for extraction demo")
        return None

def demo_create_sample_data():
    """Create sample patient data for demonstration"""
    print("\n📝 " + "="*80)
    print("   DEMO 3: CREATING SAMPLE PATIENT DOCUMENT")
    print("="*88)
    
    # Create a sample patient document for testing
    sample_content = """
PATIENT INTAKE FORM

Patient Information:
First Name: John
Last Name: Doe
Date of Birth: 01/15/1985
Phone: (555) 123-4567
Email: john.doe@email.com
Address: 123 Main Street, Anytown, ST 12345

Medical History:
Allergies: Penicillin, Peanuts
Current Medications: Metformin, Lisinopril
Medical History: Type 2 Diabetes, Hypertension
Primary Care Physician: Dr. Smith

Emergency Contact:
Name: Jane Doe (spouse)
Phone: (555) 987-6543

Insurance Information:
Insurance Company: BlueCross BlueShield
Member ID: BC123456789
Group Number: GRP001

Additional Notes:
Patient reports occasional headaches and requests refill of diabetes medication.
Last A1C: 7.2% (3 months ago)
Blood pressure well controlled on current medications.
"""
    
    # Save sample document
    sample_file = Path("data/sample_patient_document.txt")
    sample_file.parent.mkdir(exist_ok=True)
    
    with open(sample_file, 'w') as f:
        f.write(sample_content)
    
    print(f"✅ Created sample patient document: {sample_file}")
    print(f"📄 Content preview:")
    print("─" * 40)
    print(sample_content[:300] + "...")
    print("─" * 40)
    
    return str(sample_file)

def demo_extract_from_sample():
    """Demo extraction from the sample document"""
    print("\n🎯 " + "="*80)
    print("   DEMO 4: EXTRACTION FROM SAMPLE DOCUMENT")
    print("="*88)
    
    # Create sample data first
    sample_file = demo_create_sample_data()
    
    # Initialize extractor
    extractor = PatientDataExtractor()
    
    try:
        # Extract from sample document
        results = extractor.extract_patient_data(
            sample_file,
            None,  # Use most recent schema
            "markdown"
        )
        
        print(f"\n✅ Sample extraction completed!")
        print(f"   📊 Success Rate: {results['success_rate']:.1f}%")
        print(f"   📝 Fields Extracted: {results['extracted_count']}/{results['total_fields']}")
        
        # Show the full report for the sample
        print(f"\n📄 Complete Sample Report:")
        print("="*80)
        print(results['output_document'])
        print("="*80)
        
        return results
        
    except Exception as e:
        print(f"❌ Error extracting from sample: {e}")
        return None

def main():
    """Run all demos"""
    print("🚀 " + "="*80)
    print("   PATIENT DATA EXTRACTOR - COMPREHENSIVE DEMO")
    print("="*88)
    print("\nThis demo showcases the complete patient data extraction workflow:")
    print("1. 📋 Schema generation from blank forms")
    print("2. 🔍 Data extraction from filled documents") 
    print("3. 📄 Clean report generation")
    print("4. 🎯 Sample document processing")
    
    # Demo 1: Schema Generation
    schema_name = demo_schema_generation()
    
    # Demo 2: Data Extraction
    demo_data_extraction(schema_name)
    
    # Demo 3 & 4: Sample Document Processing
    demo_extract_from_sample()
    
    # Summary
    print("\n🎉 " + "="*80)
    print("   DEMO COMPLETE - SUMMARY")
    print("="*88)
    
    extractor = PatientDataExtractor()
    schemas = extractor.list_schemas()
    
    print(f"📚 Available schemas: {len(schemas)}")
    for schema in schemas:
        print(f"   • {schema}")
    
    # Check output directory
    output_dir = Path("data/patient_extraction")
    if output_dir.exists():
        extraction_files = list(output_dir.glob("extraction_*.json"))
        report_files = list(output_dir.glob("report_*.md"))
        schema_files = list(output_dir.glob("schemas/*.json"))
        
        print(f"\n💾 Generated files:")
        print(f"   📊 Extraction results: {len(extraction_files)}")
        print(f"   📄 Markdown reports: {len(report_files)}")
        print(f"   🏗️ Schema files: {len(schema_files)}")
        
        if report_files:
            latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
            print(f"\n📋 Latest report: {latest_report.name}")
    
    print(f"\n🛠️ Next steps:")
    print(f"   1. Run 'python patient_extractor.py analyze-form --input your_blank_form.pdf'")
    print(f"   2. Run 'python patient_extractor.py extract-data --input your_filled_form.pdf'")
    print(f"   3. Check the 'data/patient_extraction/' directory for results")
    print(f"   4. Integrate into your existing workflow!")
    
    print("\n✨ Demo completed successfully! ✨")

if __name__ == "__main__":
    main() 