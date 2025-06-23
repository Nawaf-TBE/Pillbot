#!/usr/bin/env python3
"""
Debug script to inspect PDF form fields and diagnose filling issues.
"""

import fitz  # PyMuPDF
import sys
import json
from pathlib import Path

def inspect_pdf_fields(pdf_path):
    """Inspect form fields in a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        fields_info = []
        
        print(f"Inspecting PDF: {pdf_path}")
        print(f"Total pages: {doc.page_count}")
        print("=" * 50)
        
        total_fields = 0
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            widgets = list(page.widgets())  # Convert generator to list
            
            if widgets:
                print(f"\nPage {page_num + 1} - Found {len(widgets)} form fields:")
                print("-" * 30)
                
                for i, widget in enumerate(widgets):
                    field_info = {
                        "page": page_num + 1,
                        "field_name": widget.field_name,
                        "field_type": widget.field_type,
                        "field_value": widget.field_value,
                        "field_label": getattr(widget, 'field_label', 'N/A'),
                        "rect": list(widget.rect)
                    }
                    
                    fields_info.append(field_info)
                    total_fields += 1
                    
                    # Map field type numbers to readable names
                    type_names = {
                        fitz.PDF_WIDGET_TYPE_TEXT: "Text",
                        fitz.PDF_WIDGET_TYPE_CHECKBOX: "Checkbox", 
                        fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "Radio Button",
                        fitz.PDF_WIDGET_TYPE_COMBOBOX: "Dropdown",
                        fitz.PDF_WIDGET_TYPE_LISTBOX: "List Box"
                    }
                    
                    type_name = type_names.get(widget.field_type, f"Unknown ({widget.field_type})")
                    
                    print(f"  {i+1:2d}. Field: '{widget.field_name}'")
                    print(f"      Type: {type_name}")
                    print(f"      Current Value: '{widget.field_value}'")
                    print(f"      Position: {widget.rect}")
                    print()
            else:
                print(f"\nPage {page_num + 1} - No form fields found")
        
        doc.close()
        
        print("=" * 50)
        print(f"SUMMARY: Found {total_fields} total form fields")
        
        # Show unique field names
        field_names = [f['field_name'] for f in fields_info if f['field_name']]
        unique_names = sorted(set(field_names))
        
        print(f"\nUnique field names ({len(unique_names)}):")
        for name in unique_names:
            print(f"  - {name}")
        
        # Save detailed info to JSON
        output_file = Path(pdf_path).stem + "_field_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(fields_info, f, indent=2)
        
        print(f"\nDetailed field analysis saved to: {output_file}")
        
        return fields_info
        
    except Exception as e:
        print(f"Error inspecting PDF: {e}")
        return []

def compare_with_schema(fields_info, schema_path="data/InsureCo_Ozempic.json"):
    """Compare PDF fields with the expected schema fields."""
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        schema_fields = list(schema.get("field_mappings", {}).keys())
        pdf_fields = [f['field_name'] for f in fields_info if f['field_name']]
        
        print("\n" + "=" * 50)
        print("FIELD MAPPING ANALYSIS")
        print("=" * 50)
        
        print(f"\nSchema expects {len(schema_fields)} fields:")
        for field in sorted(schema_fields):
            print(f"  - {field}")
        
        print(f"\nPDF contains {len(set(pdf_fields))} unique fields:")
        for field in sorted(set(pdf_fields)):
            print(f"  - {field}")
        
        # Find matches
        matches = set(schema_fields) & set(pdf_fields)
        print(f"\n✅ EXACT MATCHES ({len(matches)}):")
        for field in sorted(matches):
            print(f"  - {field}")
        
        # Find schema fields not in PDF
        missing_in_pdf = set(schema_fields) - set(pdf_fields)
        print(f"\n❌ SCHEMA FIELDS NOT IN PDF ({len(missing_in_pdf)}):")
        for field in sorted(missing_in_pdf):
            print(f"  - {field}")
        
        # Find PDF fields not in schema
        extra_in_pdf = set(pdf_fields) - set(schema_fields)
        print(f"\n⚠️  PDF FIELDS NOT IN SCHEMA ({len(extra_in_pdf)}):")
        for field in sorted(extra_in_pdf):
            print(f"  - {field}")
        
        # Calculate match percentage
        if schema_fields:
            match_percentage = (len(matches) / len(schema_fields)) * 100
            print(f"\n📊 FIELD MATCH RATE: {match_percentage:.1f}%")
            
            if match_percentage < 50:
                print("⚠️  WARNING: Low field match rate. PDF filling may not work well.")
                print("   Consider:")
                print("   1. Updating the schema to match PDF field names")
                print("   2. Creating a field mapping configuration")
                print("   3. Using a different PDF template")
        
    except Exception as e:
        print(f"Error comparing with schema: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf_fields.py <pdf_file_path>")
        print("\nExample:")
        print("  python debug_pdf_fields.py data/prior_auth_template.pdf")
        print("  python debug_pdf_fields.py data/b9de9f57-4a0d-48de-af55-e24d529588b8_form_template.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("PDF Form Field Inspector")
    print("=" * 50)
    
    fields_info = inspect_pdf_fields(pdf_path)
    
    if fields_info:
        compare_with_schema(fields_info)
    else:
        print("No form fields found or error occurred.") 