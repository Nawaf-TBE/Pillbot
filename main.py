"""
Main entry point for PriorAuthAutomation Pipeline

This script demonstrates the complete prior authorization processing pipeline
using the orchestrator to coordinate all services from document input to final PDF output.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.orchestrator import run_pipeline, get_pipeline_info, PipelineError


def create_sample_pdf():
    """
    Create a sample PDF for testing purposes using reportlab.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        sample_pdf_path = "sample_prior_auth.pdf"
        
        # Create a comprehensive sample prior authorization document
        c = canvas.Canvas(sample_pdf_path, pagesize=letter)
        
        # Page 1 - Patient and Provider Information
        c.drawString(100, 750, "PRIOR AUTHORIZATION REQUEST")
        c.drawString(100, 730, "Insurance Provider: BlueCross BlueShield")
        c.drawString(400, 730, "Date: 03/15/2024")
        
        c.drawString(100, 700, "PATIENT INFORMATION")
        c.drawString(100, 680, "Patient Name: Sarah Johnson")
        c.drawString(100, 660, "Member ID: BC987654321")
        c.drawString(100, 640, "Date of Birth: 08/22/1978")
        c.drawString(100, 620, "Phone: (555) 123-4567")
        
        c.drawString(100, 580, "PRESCRIBER INFORMATION")
        c.drawString(100, 560, "Prescriber: Dr. Maria Rodriguez, MD")
        c.drawString(100, 540, "NPI: 1234567890")
        c.drawString(100, 520, "Phone: (555) 987-6543")
        c.drawString(100, 500, "Practice: Endocrine Associates")
        
        c.drawString(100, 460, "REQUESTED MEDICATION")
        c.drawString(100, 440, "Drug Name: Ozempic (semaglutide)")
        c.drawString(100, 420, "Strength: 1.0 mg/dose")
        c.drawString(100, 400, "Quantity: 1.5 mL pen")
        c.drawString(100, 380, "Days Supply: 28 days")
        c.drawString(100, 360, "Pharmacy: Central Pharmacy")
        
        c.showPage()
        
        # Page 2 - Clinical Information
        c.drawString(100, 750, "CLINICAL INFORMATION")
        
        c.drawString(100, 720, "PRIMARY DIAGNOSIS")
        c.drawString(100, 700, "ICD-10 Code: E11.9")
        c.drawString(100, 680, "Description: Type 2 diabetes mellitus without complications")
        
        c.drawString(100, 640, "CLINICAL DATA")
        c.drawString(100, 620, "Most Recent A1C: 8.7% (Date: 02/20/2024)")
        c.drawString(100, 600, "BMI: 32.4")
        c.drawString(100, 580, "Weight: 185 lbs")
        c.drawString(100, 560, "Blood Pressure: 138/88 mmHg")
        
        c.drawString(100, 520, "PREVIOUS MEDICATIONS TRIED")
        c.drawString(100, 500, "1. Metformin 1000mg BID - 12 months")
        c.drawString(120, 480, "Outcome: Inadequate glycemic control")
        c.drawString(100, 460, "2. Glipizide 10mg daily - 8 months")
        c.drawString(120, 440, "Outcome: Discontinued due to hypoglycemic episodes")
        c.drawString(100, 420, "3. Sitagliptin 100mg daily - 6 months")
        c.drawString(120, 400, "Outcome: Minimal improvement in A1C")
        
        c.drawString(100, 360, "CONTRAINDICATIONS")
        c.drawString(100, 340, "No known contraindications to GLP-1 receptor agonists")
        c.drawString(100, 320, "No history of pancreatitis or thyroid cancer")
        
        c.showPage()
        
        # Page 3 - Clinical Justification
        c.drawString(100, 750, "CLINICAL JUSTIFICATION")
        
        c.drawString(100, 720, "Patient has Type 2 diabetes mellitus with suboptimal glycemic")
        c.drawString(100, 700, "control despite trials of three different antidiabetic medications.")
        c.drawString(100, 680, "Current A1C of 8.7% is significantly above the target of <7%.")
        
        c.drawString(100, 640, "Patient would benefit from GLP-1 receptor agonist therapy for:")
        c.drawString(120, 620, "• Improved glycemic control")
        c.drawString(120, 600, "• Weight management (current BMI 32.4)")
        c.drawString(120, 580, "• Cardiovascular risk reduction")
        
        c.drawString(100, 540, "Step therapy requirements have been met with adequate")
        c.drawString(100, 520, "trials of metformin, sulfonylurea, and DPP-4 inhibitor.")
        
        c.drawString(100, 480, "AUTHORIZATION REQUEST")
        c.drawString(100, 460, "Requesting approval for Ozempic 1.0mg weekly injection")
        c.drawString(100, 440, "for improved diabetes management and cardiovascular")
        c.drawString(100, 420, "risk reduction in this high-risk patient.")
        
        c.drawString(100, 380, "Prescriber Signature: Dr. Maria Rodriguez, MD")
        c.drawString(100, 360, "Date: 03/15/2024")
        
        c.save()
        
        print(f"✅ Created sample prior authorization PDF: {sample_pdf_path}")
        return sample_pdf_path
        
    except ImportError:
        print("⚠️  reportlab not installed. Cannot create sample PDF.")
        print("Install with: pip install reportlab")
        return None


def display_pipeline_info():
    """Display information about the pipeline and service availability."""
    print("🔧 Pipeline Information")
    print("=" * 50)
    
    try:
        pipeline_info = get_pipeline_info()
        
        print(f"Pipeline: {pipeline_info['pipeline_name']} v{pipeline_info['version']}")
        print(f"Stages: {len(pipeline_info['stages'])} total")
        
        print(f"\n📊 Service Availability:")
        availability = pipeline_info['service_availability']
        for service, available in availability.items():
            status = "✅" if available else "❌"
            print(f"  {service}: {status}")
        
        print(f"\n🔧 Service Details:")
        services = pipeline_info['services']
        
        # OCR Service
        ocr = services['ocr']
        print(f"  OCR: {ocr['service_name']} ({ocr['model']})")
        print(f"    API Key: {'✅' if ocr['api_key_configured'] else '❌'}")
        
        # Parsing Service
        parsing = services['parsing']
        print(f"  Parsing: {parsing['service_name']}")
        print(f"    API Key: {'✅' if parsing['api_key_configured'] else '❌'}")
        print(f"    Formats: {', '.join(parsing['supported_formats'])}")
        
        # LLM Service
        llm = services['llm']
        print(f"  LLM: {llm['service_name']} ({llm['model']})")
        print(f"    API Key: {'✅' if llm['api_key_configured'] else '❌'}")
        
        # Form Filler Service
        form_filler = services['form_filler']
        print(f"  Form Filler: {form_filler['service_name']} v{form_filler['version']}")
        print(f"    Features: {len(form_filler['supported_features'])} available")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting pipeline info: {e}")
        return False


def display_pipeline_results(results: dict):
    """Display the results of pipeline execution."""
    print(f"\n🎉 Pipeline Execution Results")
    print("=" * 50)
    
    metadata = results["pipeline_metadata"]
    summary = results["summary"]
    
    # Basic info
    print(f"Document ID: {metadata['document_id'][:8]}...")
    print(f"Document: {Path(metadata['document_path']).name}")
    print(f"Schema: {metadata['schema_name']}")
    print(f"Duration: {metadata['total_duration_seconds']:.2f} seconds")
    print(f"Status: {metadata['status']}")
    
    # Stage summary
    print(f"\n📊 Stage Summary:")
    print(f"  Completed: {summary['completed_stages']}/{summary['total_stages']} ({summary['success_rate']:.1%})")
    print(f"  Skipped: {summary['skipped_stages']}")
    print(f"  Failed: {summary['failed_stages']}")
    
    # Stage details
    print(f"\n🔄 Stage Details:")
    stage_results = results["stage_results"]
    
    for stage_name, stage_data in stage_results.items():
        status = stage_data["status"]
        duration = stage_data["duration_seconds"]
        
        if status == "completed":
            print(f"  ✅ {stage_name}: {duration:.2f}s")
            
            # Show specific metrics for key stages
            result = stage_data.get("result", {})
            
            if stage_name == "pdf_analysis":
                pages = result.get("page_count", 0)
                native = result.get("has_native_text", False)
                print(f"      📄 {pages} pages, native text: {native}")
                
            elif stage_name == "entity_extraction":
                confidence = result.get("confidence_score", 0)
                print(f"      🎯 Confidence: {confidence:.2f}")
                
            elif stage_name == "form_filling":
                completion = result.get("completion_rate", 0)
                fields = result.get("populated_fields", 0)
                total = result.get("total_fields", 0)
                print(f"      📋 {fields}/{total} fields ({completion:.1%})")
                
            elif stage_name == "pdf_generation":
                size_kb = result.get("file_size_kb", 0)
                output_path = result.get("output_path", "")
                print(f"      📄 {Path(output_path).name} ({size_kb:.1f} KB)")
                
        elif status == "skipped":
            reason = stage_data.get("reason", "Unknown")
            print(f"  ⚠️  {stage_name}: skipped ({reason})")
            
        elif status == "failed":
            reason = stage_data.get("reason", "Unknown")
            print(f"  ❌ {stage_name}: failed ({reason})")
    
    # Output files
    if summary["output_files"]:
        print(f"\n📁 Generated Files:")
        for output_file in summary["output_files"]:
            file_path = Path(output_file["path"])
            file_type = output_file["type"]
            size_kb = output_file["size_kb"]
            print(f"  📄 {file_path.name} ({file_type}, {size_kb:.1f} KB)")


def main():
    """
    Main function to demonstrate the complete pipeline orchestration.
    """
    print("🤖 PriorAuthAutomation - Pipeline Orchestrator")
    print("=" * 60)
    
    # Display pipeline information
    if not display_pipeline_info():
        print("❌ Failed to get pipeline information")
        return
    
    # Check if a PDF was provided as command line argument
    pdf_path = None
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}")
            return
    else:
        # Create a sample PDF for testing
        print(f"\n📝 Creating sample prior authorization document...")
        pdf_path = create_sample_pdf()
        
        if not pdf_path or not os.path.exists(pdf_path):
            print("❌ Could not create sample PDF")
            print("\n📝 Usage:")
            print("python main.py [path_to_pdf_file]")
            print("\nOr install reportlab to create a sample PDF:")
            print("pip install reportlab")
            return
    
    print(f"\n🚀 Starting pipeline execution...")
    print(f"📄 Processing document: {Path(pdf_path).name}")
    
    try:
        # Run the complete pipeline
        results = run_pipeline(
            document_path=pdf_path,
            schema_name="InsureCo_Ozempic",
            output_directory="data"
        )
        
        # Display results
        display_pipeline_results(results)
        
        print(f"\n✅ Pipeline completed successfully!")
        
        # Clean up sample file if we created it
        if pdf_path == "sample_prior_auth.pdf":
            try:
                os.remove(pdf_path)
                print(f"🗑️  Cleaned up sample file: {pdf_path}")
            except OSError:
                print(f"⚠️  Could not remove sample file: {pdf_path}")
    
    except PipelineError as e:
        print(f"\n❌ Pipeline failed at stage '{e.stage.value}': {e.message}")
        if e.original_error:
            print(f"   Original error: {e.original_error}")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    print(f"\n🔧 For more detailed logs, check the console output above.")


if __name__ == "__main__":
    main() 