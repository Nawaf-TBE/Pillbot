"""
Test script for PDF Generation in Form Filler Service

This script demonstrates the PDF generation functionality by creating sample form data
and generating a filled PDF from the template.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.form_filler_service import (
    FormFillerService, load_and_populate_form, generate_filled_pdf,
    get_form_filler_service_info, FormFillerError
)

def create_sample_form_data():
    """Create sample form data for testing PDF generation."""
    return {
        # Patient Information
        "member_id": "INS123456789",
        "patient_first_name": "Jennifer",
        "patient_last_name": "Martinez",
        "patient_date_of_birth": "03/22/1985",
        
        # Prescriber Information
        "prescriber_name": "Dr. Michael Chen",
        "prescriber_npi": "1234567890",
        "prescriber_phone": "(555) 123-4567",
        
        # Diagnosis Information
        "primary_diagnosis_code": "E11.9",
        "primary_diagnosis": "Type 2 diabetes mellitus without complications",
        
        # Medication Information
        "requested_drug_name": "Ozempic",
        "requested_strength": "1.0 mg/dose",
        "quantity_requested": "1.5 ml pen",
        "days_supply": "28",
        "pharmacy_name": "HealthPlus Pharmacy",
        
        # Clinical Information
        "a1c_value": "8.7%",
        "bmi_value": "32.1",
        "contraindications_present": "No",
        "previous_medications_tried": "Metformin 1000mg BID for 8 months - inadequate control. Glipizide 10mg daily for 6 months - hypoglycemic episodes. Patient discontinued due to adverse effects.",
        "clinical_justification": "Patient has Type 2 diabetes with suboptimal glycemic control despite adequate trials of metformin and sulfonylurea. A1C remains elevated at 8.7% above target of <7%. Patient has obesity with BMI 32.1 and would benefit from GLP-1 therapy for both glycemic control and weight management. No contraindications to semaglutide therapy.",
        
        # Additional fields (some set by conditional logic)
        "priority_level": "Standard"
    }

def test_form_population_and_pdf_generation():
    """Test the complete form population and PDF generation workflow."""
    print("🧪 Testing PDF Generation Workflow")
    print("=" * 50)
    
    try:
        # Step 1: Check if template exists
        template_path = Path("../data/prior_auth_template.pdf")
        if not template_path.exists():
            print("⚠️  PDF template not found. Please run 'python create_pdf_template.py' first")
            return False
        
        # Step 2: Create sample entities
        print("\n📋 Creating sample form data...")
        entities = create_sample_form_data()
        print(f"   Created {len(entities)} sample entities")
        
        # Step 3: Populate form using schema
        print("\n🔧 Populating form with schema...")
        try:
            populated_form = load_and_populate_form(entities, "InsureCo_Ozempic")
            
            form_metadata = populated_form["form_metadata"]
            print(f"✅ Form population completed!")
            print(f"   📋 Schema: {form_metadata['schema_name']} v{form_metadata['schema_version']}")
            print(f"   📊 Completion: {form_metadata['populated_fields_count']}/{form_metadata['total_fields_count']} fields ({form_metadata['completion_rate']:.1%})")
            
            # Show conditional logic results if present
            if "conditional_logic" in form_metadata:
                conditional_logic = form_metadata["conditional_logic"]
                print(f"   🔧 Conditional rules: {conditional_logic.get('rules_triggered', 0)} triggered")
                
            # Show some populated fields
            form_data = populated_form["form_data"]
            sample_fields = ["member_id", "patient_first_name", "requested_drug_name", "a1c_value"]
            for field in sample_fields:
                if field in form_data and form_data[field]["value"]:
                    print(f"   📝 {field}: {form_data[field]['value']}")
                    
        except Exception as e:
            print(f"❌ Form population failed: {e}")
            return False
        
        # Step 4: Generate filled PDF
        print(f"\n📄 Generating filled PDF...")
        try:
            output_path = Path("../data/test_filled_form.pdf")
            
            # Use the convenience function
            generate_filled_pdf(
                str(template_path),
                populated_form,
                str(output_path)
            )
            
            # Get PDF generation stats from metadata
            pdf_stats = populated_form["form_metadata"].get("pdf_generation", {})
            fill_stats = pdf_stats.get("fill_statistics", {})
            
            print(f"✅ PDF generation completed!")
            print(f"   📄 Output: {output_path}")
            print(f"   📊 Fields found: {fill_stats.get('fields_found', 0)}")
            print(f"   📈 Fields filled: {fill_stats.get('fields_filled', 0)}")
            print(f"   📋 Completion rate: {pdf_stats.get('completion_rate', 0):.1%}")
            
            if fill_stats.get("fields_missing"):
                missing_count = len(fill_stats["fields_missing"])
                print(f"   ⚠️  Fields not found in template: {missing_count}")
                if missing_count <= 5:
                    print(f"      {', '.join(fill_stats['fields_missing'][:5])}")
            
            # Verify the output file exists
            if output_path.exists():
                file_size = output_path.stat().st_size / 1024  # KB
                print(f"   💾 Generated PDF size: {file_size:.1f} KB")
                return True
            else:
                print(f"❌ Output PDF was not created")
                return False
                
        except FormFillerError as e:
            print(f"❌ PDF generation failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected PDF generation error: {e}")
            return False
    
    except Exception as e:
        print(f"❌ Test workflow failed: {e}")
        return False

def test_pdf_field_analysis():
    """Analyze the PDF template to show available fields."""
    print(f"\n🔍 Analyzing PDF Template Fields")
    print("-" * 40)
    
    try:
        import fitz  # PyMuPDF
        
        template_path = Path("../data/prior_auth_template.pdf")
        if not template_path.exists():
            print(f"⚠️  Template not found: {template_path}")
            return
        
        # Open template and analyze fields
        doc = fitz.open(str(template_path))
        all_fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            widgets = page.widgets()
            
            for widget in widgets:
                field_info = {
                    "name": widget.field_name,
                    "type": widget.field_type,
                    "page": page_num + 1
                }
                all_fields.append(field_info)
        
        doc.close()
        
        if all_fields:
            print(f"📋 Found {len(all_fields)} form fields in template:")
            
            # Group by type
            field_types = {}
            for field in all_fields:
                field_type = field["type"]
                if field_type not in field_types:
                    field_types[field_type] = []
                field_types[field_type].append(field)
            
            # Display by type
            type_names = {
                fitz.PDF_WIDGET_TYPE_TEXT: "Text",
                fitz.PDF_WIDGET_TYPE_CHECKBOX: "Checkbox",
                fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "Radio Button",
                fitz.PDF_WIDGET_TYPE_COMBOBOX: "Dropdown",
                fitz.PDF_WIDGET_TYPE_LISTBOX: "List Box"
            }
            
            for field_type, fields in field_types.items():
                type_name = type_names.get(field_type, f"Type {field_type}")
                print(f"\n   {type_name} fields ({len(fields)}):")
                for field in fields[:10]:  # Show first 10 of each type
                    print(f"      • {field['name']} (page {field['page']})")
                if len(fields) > 10:
                    print(f"      ... and {len(fields) - 10} more")
        else:
            print(f"⚠️  No form fields found in template")
    
    except ImportError:
        print(f"⚠️  PyMuPDF not available for field analysis")
    except Exception as e:
        print(f"❌ Error analyzing template: {e}")

def main():
    """Main test function."""
    print("🤖 Form Filler Service - PDF Generation Testing")
    print("=" * 60)
    
    # Display service info
    service_info = get_form_filler_service_info()
    print(f"📋 Service: {service_info['service_name']} v{service_info['version']}")
    
    # Check PyMuPDF availability
    try:
        import fitz
        print(f"✅ PyMuPDF available for PDF generation")
    except ImportError:
        print(f"❌ PyMuPDF not available - PDF generation disabled")
        return
    
    # Run tests
    success = test_form_population_and_pdf_generation()
    
    if success:
        print(f"\n🎉 PDF Generation Test Summary")
        print("-" * 35)
        print("✅ Form population: Success")
        print("✅ PDF generation: Success")
        print("✅ Output file created: Success")
        
        # Analyze template fields
        test_pdf_field_analysis()
        
        print(f"\n📁 Generated files:")
        output_files = [
            "../data/prior_auth_template.pdf",
            "../data/test_filled_form.pdf"
        ]
        
        for file_path in output_files:
            path = Path(file_path)
            if path.exists():
                size_kb = path.stat().st_size / 1024
                print(f"   • {path.name} ({size_kb:.1f} KB)")
        
        print(f"\n🔧 To integrate into your workflow:")
        print(f"   1. Use load_and_populate_form() to populate form data")
        print(f"   2. Use generate_filled_pdf() to create filled PDFs")
        print(f"   3. PDFs are automatically saved with generation metadata")
        
    else:
        print(f"\n❌ PDF Generation Test Failed")
        print("Check the error messages above for troubleshooting")

if __name__ == "__main__":
    main() 