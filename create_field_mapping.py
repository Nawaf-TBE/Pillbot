#!/usr/bin/env python3
"""
Script to create field mappings between schema fields and PDF field names.
This helps when user-provided PDF templates have different field names than expected.
"""

import json
import sys
from pathlib import Path

def create_field_mapping_template(pdf_field_analysis_file, schema_file="data/InsureCo_Ozempic.json"):
    """Create a field mapping template based on PDF analysis and schema."""
    
    # Load PDF field analysis
    try:
        with open(pdf_field_analysis_file, 'r') as f:
            pdf_analysis = json.load(f)
    except Exception as e:
        print(f"Error loading PDF analysis file: {e}")
        return None
    
    # Load schema
    try:
        with open(schema_file, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema file: {e}")
        return None
    
    schema_fields = list(schema.get("field_mappings", {}).keys())
    pdf_fields = []
    
    # Extract unique PDF field names
    for field_info in pdf_analysis:
        if field_info.get("field_name"):
            pdf_fields.append(field_info["field_name"])
    
    pdf_fields = sorted(set(pdf_fields))
    
    # Create mapping template
    mapping = {
        "mapping_name": "Custom PDF Field Mapping",
        "created_for": pdf_field_analysis_file,
        "schema_file": schema_file,
        "description": "Maps schema field names to PDF form field names",
        "field_mappings": {}
    }
    
    print(f"Creating field mapping for {len(schema_fields)} schema fields")
    print(f"PDF contains {len(pdf_fields)} form fields")
    print("\nCreating mapping template...")
    
    # Create template mapping entries
    for schema_field in schema_fields:
        mapping["field_mappings"][schema_field] = {
            "pdf_field_name": None,  # To be filled in manually
            "confidence": 0.0,
            "notes": f"Map '{schema_field}' to appropriate PDF field",
            "suggestions": []
        }
        
        # Try to find similar field names (basic fuzzy matching)
        suggestions = []
        schema_lower = schema_field.lower()
        
        for pdf_field in pdf_fields:
            pdf_lower = pdf_field.lower()
            
            # Look for partial matches
            if any(word in pdf_lower for word in schema_lower.split('_')):
                suggestions.append(pdf_field)
            elif schema_lower in pdf_lower or pdf_lower in schema_lower:
                suggestions.append(pdf_field)
        
        mapping["field_mappings"][schema_field]["suggestions"] = suggestions[:5]  # Top 5 suggestions
    
    # Save mapping template
    output_file = Path(pdf_field_analysis_file).stem.replace("_field_analysis", "") + "_field_mapping_template.json"
    
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\nField mapping template saved to: {output_file}")
    print("\nNext steps:")
    print("1. Edit the mapping file to set 'pdf_field_name' for each schema field")
    print("2. Use suggestions as guidance for matching fields")
    print("3. Save the completed mapping file")
    print("4. Use it with the enhanced form filler service")
    
    return mapping

def show_guided_mapping(pdf_field_analysis_file, schema_file="data/InsureCo_Ozempic.json"):
    """Show a guided interactive mapping process."""
    
    # Load files
    try:
        with open(pdf_field_analysis_file, 'r') as f:
            pdf_analysis = json.load(f)
        with open(schema_file, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading files: {e}")
        return None
    
    schema_fields = list(schema.get("field_mappings", {}).keys())
    pdf_fields = sorted(set([f["field_name"] for f in pdf_analysis if f.get("field_name")]))
    
    print("PDF Form Field Interactive Mapping")
    print("=" * 50)
    print(f"Schema fields to map: {len(schema_fields)}")
    print(f"PDF fields available: {len(pdf_fields)}")
    print("\nInstructions:")
    print("- For each schema field, choose a matching PDF field")
    print("- Enter the number of the PDF field, or 'skip' to skip")
    print("- Enter 'quit' to exit")
    print("=" * 50)
    
    mapping = {"field_mappings": {}}
    
    for i, schema_field in enumerate(schema_fields):
        print(f"\n[{i+1}/{len(schema_fields)}] Schema field: '{schema_field}'")
        description = schema["field_mappings"][schema_field].get("description", "")
        if description:
            print(f"    Description: {description}")
        
        # Show PDF field options
        print("\nAvailable PDF fields:")
        for j, pdf_field in enumerate(pdf_fields):
            print(f"  {j+1:3d}. {pdf_field}")
        
        while True:
            try:
                choice = input(f"\nSelect PDF field for '{schema_field}' (1-{len(pdf_fields)}, 'skip', 'quit'): ").strip()
                
                if choice.lower() == 'quit':
                    print("Mapping cancelled.")
                    return None
                elif choice.lower() == 'skip':
                    mapping["field_mappings"][schema_field] = None
                    break
                else:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(pdf_fields):
                        selected_field = pdf_fields[choice_num - 1]
                        mapping["field_mappings"][schema_field] = selected_field
                        print(f"  ✓ Mapped '{schema_field}' → '{selected_field}'")
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(pdf_fields)}")
            except ValueError:
                print("Please enter a valid number, 'skip', or 'quit'")
    
    # Save completed mapping
    output_file = Path(pdf_field_analysis_file).stem.replace("_field_analysis", "") + "_field_mapping.json"
    
    final_mapping = {
        "mapping_name": "Custom PDF Field Mapping",
        "created_for": pdf_field_analysis_file,
        "schema_file": schema_file,
        "description": "Maps schema field names to PDF form field names",
        "field_mappings": mapping["field_mappings"]
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_mapping, f, indent=2)
    
    print(f"\nCompleted field mapping saved to: {output_file}")
    
    # Show summary
    mapped_count = len([v for v in mapping["field_mappings"].values() if v is not None])
    print(f"\nSummary: {mapped_count}/{len(schema_fields)} fields mapped")
    
    return final_mapping

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_field_mapping.py <pdf_field_analysis_file> [mode]")
        print("\nModes:")
        print("  template  - Create a mapping template file (default)")
        print("  guided    - Interactive guided mapping")
        print("\nExample:")
        print("  python create_field_mapping.py b9de9f57-4a0d-48de-af55-e24d529588b8_form_template_field_analysis.json")
        print("  python create_field_mapping.py b9de9f57-4a0d-48de-af55-e24d529588b8_form_template_field_analysis.json guided")
        sys.exit(1)
    
    analysis_file = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "template"
    
    if not Path(analysis_file).exists():
        print(f"Error: Analysis file not found: {analysis_file}")
        sys.exit(1)
    
    if mode == "guided":
        show_guided_mapping(analysis_file)
    elif mode == "template":
        create_field_mapping_template(analysis_file)
    else:
        print(f"Unknown mode: {mode}. Use 'template' or 'guided'")
        sys.exit(1) 