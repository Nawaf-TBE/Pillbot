#!/usr/bin/env python3
"""
Create a simple PDF template for testing the orchestrator.
This creates a basic fillable PDF with the InsureCo_Ozempic schema fields.
"""

import os
from pathlib import Path

def create_simple_template():
    """Create a basic PDF template using reportlab."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.colors import black
        
        # Create output directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        template_path = data_dir / "prior_auth_template.pdf"
        
        # Create PDF with form fields
        c = canvas.Canvas(str(template_path), pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Prior Authorization Form - InsureCo Ozempic")
        
        # Patient Information Section
        y_pos = height - 100
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Patient Information:")
        
        y_pos -= 30
        c.setFont("Helvetica", 10)
        
        # Create form fields for key InsureCo_Ozempic schema fields
        form_fields = [
            ("member_id", "Member ID:"),
            ("patient_first_name", "First Name:"),
            ("patient_last_name", "Last Name:"),
            ("patient_date_of_birth", "Date of Birth:"),
            ("prescriber_name", "Prescriber Name:"),
            ("prescriber_npi", "NPI:"),
            ("prescriber_phone", "Phone:"),
            ("primary_diagnosis_code", "Diagnosis Code:"),
            ("primary_diagnosis_description", "Diagnosis Description:"),
            ("requested_drug_name", "Drug Name:"),
            ("requested_strength", "Strength:"),
            ("quantity_requested", "Quantity:"),
            ("days_supply", "Days Supply:"),
            ("pharmacy_name", "Pharmacy:"),
            ("a1c_value", "A1C Value:"),
            ("bmi_value", "BMI:"),
            ("contraindications_present", "Contraindications:"),
            ("priority_level", "Priority:"),
            ("previous_medications_tried", "Previous Medications:"),
            ("clinical_justification", "Clinical Justification:"),
            ("step_therapy_requirement_met", "Step Therapy Met:")
        ]
        
        for i, (field_name, label) in enumerate(form_fields):
            if i > 0 and i % 8 == 0:  # New page every 8 fields
                c.showPage()
                y_pos = height - 50
            
            # Draw label
            c.drawString(50, y_pos, label)
            
            # Create text field
            try:
                c.acroForm.textfield(
                    name=field_name,
                    tooltip=f"Enter {label.rstrip(':')}",
                    x=200,
                    y=y_pos - 5,
                    borderStyle='inset',
                    width=200,
                    height=15,
                    textColor=black,
                    forceBorder=True
                )
            except:
                # Fallback if acroForm fails - just draw a box
                c.rect(200, y_pos - 5, 200, 15)
            
            y_pos -= 25
        
        c.save()
        
        print(f"✅ Created PDF template: {template_path}")
        print(f"📄 Template size: {template_path.stat().st_size / 1024:.1f} KB")
        
        return str(template_path)
        
    except ImportError:
        print("⚠️  reportlab not available")
        print("Install with: pip install reportlab")
        
        # Create a very basic PDF structure as fallback
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        template_path = data_dir / "prior_auth_template.pdf"
        
        # Create minimal PDF structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Prior Auth Template) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
298
%%EOF"""
        
        with open(template_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ Created basic PDF template: {template_path}")
        return str(template_path)
        
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return None

if __name__ == "__main__":
    create_simple_template() 