"""
Main module for testing PDF utility functions.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pdf_utils import check_pdf_is_native, get_pdf_page_count, get_pdf_info
from services.data_store import (
    generate_document_id, save_document_metadata, save_processed_data,
    get_document_metadata, list_documents
)
from services.ocr_service import perform_mistral_ocr, check_ocr_availability, get_ocr_service_info, OCRError
from services.parsing_service import (
    perform_llamaparse, perform_llamaparse_with_metadata, check_parsing_availability, 
    get_parsing_service_info, analyze_prior_auth_document, ParsingError,
    extract_with_pdfplumber, perform_combined_parsing
)
from services.llm_service import (
    extract_entities_with_gemini, check_llm_availability, get_llm_service_info,
    LLMServiceError, validate_extracted_entities
)
from services.form_filler_service import (
    load_and_populate_form, get_form_filler_service_info, check_form_filler_availability,
    FormFillerError, FormFillerService
)


def create_sample_extraction_rules():
    """
    Create dummy extraction rules for demonstrating pdfplumber functionality.
    These rules would typically be customized based on the specific document format.
    
    Returns:
        Dict: Extraction rules for pdfplumber
    """
    return {
        "bounding_boxes": {
            # Example: Extract patient ID from top-right corner of first page
            "patient_id": {
                "x0": 400,  # Left boundary (in points, 1 point = 1/72 inch)
                "y0": 700,  # Bottom boundary
                "x1": 550,  # Right boundary
                "y1": 750,  # Top boundary
                "page": 0   # First page (0-indexed)
            },
            # Example: Extract date from header area
            "document_date": {
                "x0": 50,
                "y0": 750,
                "x1": 200,
                "y1": 780,
                "page": 0
            }
        },
        "table_extraction": {
            "page": 0,  # Extract tables from first page
            "table_settings": {},  # Use default pdfplumber settings
            "columns_of_interest": ["Medication", "Dosage", "Quantity"]
        },
        "regex_patterns": {
            # Extract patterns that look like member IDs (letters followed by numbers)
            "member_id": {
                "pattern": r"[A-Z]{2,3}\d{6,9}",
                "flags": 0,
                "page": "all"
            },
            # Extract dates in MM/DD/YYYY format
            "dates": {
                "pattern": r"\d{1,2}/\d{1,2}/\d{4}",
                "flags": 0,
                "page": "all"
            },
            # Extract drug names (capitalized words followed by dosage info)
            "medications": {
                "pattern": r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\d+(?:\.\d+)?\s*(?:mg|ml|g)",
                "flags": 0,
                "page": "all"
            }
        },
        "text_search": {
            # Find patient information sections
            "patient_info": {
                "search_terms": ["Patient Name", "Member Name", "DOB", "Date of Birth"],
                "context_lines": 3,
                "page": "all"
            },
            # Find diagnosis information
            "diagnosis_info": {
                "search_terms": ["Diagnosis", "Condition", "ICD-10", "Medical History"],
                "context_lines": 2,
                "page": "all"
            },
            # Find pharmacy information
            "pharmacy_info": {
                "search_terms": ["Pharmacy", "Dispensing", "Pharmacist"],
                "context_lines": 2,
                "page": "all"
            }
        }
    }


def create_sample_pdf():
    """
    Create a simple PDF file for testing purposes using reportlab.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        sample_pdf_path = "sample_test.pdf"
        
        # Create a simple PDF with text content
        c = canvas.Canvas(sample_pdf_path, pagesize=letter)
        
        # Page 1 - Medical Document Header
        c.drawString(100, 750, "PRIOR AUTHORIZATION REQUEST")
        c.drawString(400, 740, "Date: 12/15/2023")  # Will be extracted by bounding box
        c.drawString(400, 720, "ID: AB123456")      # Will be extracted by bounding box
        
        c.drawString(100, 700, "Patient Name: John Smith")
        c.drawString(100, 680, "DOB: 01/15/1980")
        c.drawString(100, 660, "Member ID: AB123456789")
        c.drawString(100, 640, "Diagnosis: Hypertension (ICD-10: I10)")
        
        c.drawString(100, 600, "Requested Medication: Lisinopril 10mg")
        c.drawString(100, 580, "Quantity: 90 tablets")
        c.drawString(100, 560, "Prescribing Physician: Dr. Jane Wilson")
        
        c.drawString(100, 520, "Pharmacy: Main Street Pharmacy")
        c.drawString(100, 500, "Pharmacist: PharmD Robert Johnson")
        c.showPage()
        
        # Page 2 - Additional Medical Information
        c.drawString(100, 750, "MEDICAL HISTORY AND CLINICAL NOTES")
        c.drawString(100, 700, "Patient has history of elevated blood pressure.")
        c.drawString(100, 680, "Previous medications tried: Amlodipine 5mg")
        c.drawString(100, 660, "Current condition requires step therapy completion.")
        
        c.drawString(100, 620, "Lab Results (Date: 11/20/2023):")
        c.drawString(120, 600, "- Blood Pressure: 145/95 mmHg")
        c.drawString(120, 580, "- Creatinine: 1.2 mg/dL")
        c.drawString(120, 560, "- eGFR: 75 mL/min/1.73m²")
        c.showPage()
        
        # Page 3 - Authorization Details
        c.drawString(100, 750, "AUTHORIZATION DETAILS")
        c.drawString(100, 700, "Request Status: Pending Review")
        c.drawString(100, 680, "Submission Date: 12/15/2023")
        c.drawString(100, 660, "Expected Review Time: 3-5 business days")
        
        c.drawString(100, 620, "Insurance Information:")
        c.drawString(120, 600, "Plan: BlueCross BlueShield PPO")
        c.drawString(120, 580, "Group Number: 12345")
        c.drawString(120, 560, "Policy Number: BC987654321")
        
        c.drawString(100, 500, "End of Prior Authorization Request Document")
        c.save()
        
        print(f"✅ Created sample PDF: {sample_pdf_path}")
        return sample_pdf_path
        
    except ImportError:
        print("⚠️  reportlab not installed. Cannot create sample PDF.")
        print("Install with: pip install reportlab")
        return None


def test_pdf_functions(pdf_path: str):
    """
    Test the PDF utility functions with a given PDF file and store results.
    
    Args:
        pdf_path (str): Path to the PDF file to test
    """
    print(f"\n🔍 Testing PDF: {pdf_path}")
    print("-" * 50)
    
    # Generate document ID for this test
    doc_id = generate_document_id()
    
    try:
        # Test page count function
        page_count = get_pdf_page_count(pdf_path)
        print(f"📄 Page count: {page_count}")
        
        # Test native PDF check
        is_native = check_pdf_is_native(pdf_path)
        print(f"📝 Has selectable text: {'Yes' if is_native else 'No'}")
        
        # Test comprehensive info function
        pdf_info = get_pdf_info(pdf_path)
        print(f"💾 File size: {pdf_info['file_size_mb']} MB")
        print(f"📋 Metadata: {pdf_info['metadata']}")
        
        # Save results to data store
        print("\n💾 Saving results to data store...")
        
        # Save document metadata
        metadata = {
            "file_path": pdf_path,
            "original_filename": os.path.basename(pdf_path),
            "is_native_pdf": is_native,
            "status": "analyzed",
            "file_size_mb": pdf_info['file_size_mb']
        }
        save_document_metadata(doc_id, metadata)
        print(f"✅ Saved metadata for document {doc_id[:8]}...")
        
        # Save PDF analysis results
        analysis_data = {
            "page_count": page_count,
            "is_native": is_native,
            "file_size_mb": pdf_info['file_size_mb'],
            "pdf_metadata": pdf_info['metadata'],
            "analysis_timestamp": datetime.now().isoformat()
        }
        save_processed_data(doc_id, "pdf_analysis", analysis_data)
        print(f"✅ Saved PDF analysis data")
        
        # Conditionally perform OCR based on PDF type
        ocr_performed = False
        if not is_native:
            print(f"\n🔍 PDF appears to be scanned (no native text), attempting OCR...")
            
            # Check if OCR service is available
            if check_ocr_availability():
                try:
                    print(f"📸 Starting OCR processing with Mistral Vision API...")
                    ocr_result = perform_mistral_ocr(pdf_path)
                    
                    # Save OCR results
                    save_processed_data(doc_id, "ocr", ocr_result)
                    print(f"✅ OCR completed successfully!")
                    print(f"   Extracted text length: {len(ocr_result.get('extracted_text', ''))} characters")
                    print(f"   Confidence score: {ocr_result.get('confidence', 'N/A')}")
                    print(f"   Processing time: {ocr_result.get('metadata', {}).get('processing_time_seconds', 'N/A')} seconds")
                    
                    # Update document status
                    save_document_metadata(doc_id, {"status": "ocr_completed"})
                    ocr_performed = True
                    
                except OCRError as e:
                    print(f"❌ OCR failed: {e}")
                    save_document_metadata(doc_id, {"status": "ocr_failed", "ocr_error": str(e)})
                except Exception as e:
                    print(f"❌ Unexpected OCR error: {e}")
                    save_document_metadata(doc_id, {"status": "ocr_error", "error": str(e)})
            else:
                print(f"⚠️  OCR service not available (check MISTRAL_API_KEY)")
                save_document_metadata(doc_id, {"status": "ocr_unavailable"})
        else:
            print(f"\n✅ PDF has native text, skipping OCR")
            save_document_metadata(doc_id, {"status": "native_pdf_processed"})
        
        # Perform document parsing using LlamaParse
        parsing_performed = False
        print(f"\n📝 Starting document parsing with LlamaParse...")
        
        if check_parsing_availability():
            try:
                print(f"🔍 Parsing document structure and content...")
                parsing_result = perform_llamaparse_with_metadata(pdf_path)
                
                # Save parsing results
                save_processed_data(doc_id, "parsing", parsing_result)
                print(f"✅ Document parsing completed!")
                print(f"   Extracted content length: {len(parsing_result['markdown_content'])} characters")
                print(f"   Word count: {parsing_result['metadata']['content_stats']['word_count']}")
                print(f"   Headers found: {parsing_result['metadata']['content_stats']['header_count']}")
                print(f"   Processing time: {parsing_result['metadata']['processing_time_seconds']} seconds")
                
                # Analyze for prior authorization content
                print(f"\n🏥 Analyzing for prior authorization content...")
                pa_analysis = analyze_prior_auth_document(parsing_result['markdown_content'])
                save_processed_data(doc_id, "prior_auth_analysis", pa_analysis)
                
                print(f"   Document type: {pa_analysis['document_type']} (confidence: {pa_analysis['confidence']:.2f})")
                print(f"   Key fields found: {len(pa_analysis['key_fields_found'])}")
                if pa_analysis['entities']:
                    print(f"   Extracted entities: {list(pa_analysis['entities'].keys())}")
                
                # Update document status
                save_document_metadata(doc_id, {"status": "parsing_completed"})
                parsing_performed = True
                
            except ParsingError as e:
                print(f"❌ Parsing failed: {e}")
                save_document_metadata(doc_id, {"status": "parsing_failed", "parsing_error": str(e)})
            except Exception as e:
                print(f"❌ Unexpected parsing error: {e}")
                save_document_metadata(doc_id, {"status": "parsing_error", "error": str(e)})
        else:
            print(f"⚠️  Parsing service not available (check LLAMAPARSE_API_KEY)")
            save_document_metadata(doc_id, {"status": "parsing_unavailable"})
        
        # Demonstrate pdfplumber extraction with sample rules
        print(f"\n🔧 Testing pdfplumber extraction with sample rules...")
        
        try:
            # Create sample extraction rules
            extraction_rules = create_sample_extraction_rules()
            
            print(f"📋 Extraction rules configured:")
            print(f"   - Bounding boxes: {len(extraction_rules['bounding_boxes'])} fields")
            print(f"   - Regex patterns: {len(extraction_rules['regex_patterns'])} patterns")
            print(f"   - Text searches: {len(extraction_rules['text_search'])} searches")
            print(f"   - Table extraction: {'enabled' if 'table_extraction' in extraction_rules else 'disabled'}")
            
            # Perform pdfplumber extraction
            pdfplumber_result = extract_with_pdfplumber(pdf_path, extraction_rules)
            
            # Save pdfplumber results
            save_processed_data(doc_id, "pdfplumber_extraction", pdfplumber_result)
            print(f"✅ pdfplumber extraction completed!")
            
            # Display key findings
            bbox_data = pdfplumber_result.get("bounding_box_data", {})
            if bbox_data:
                print(f"   📍 Bounding box extractions:")
                for field, data in bbox_data.items():
                    if data.get("text") and data.get("confidence", 0) > 0:
                        print(f"      {field}: '{data['text'][:50]}{'...' if len(data['text']) > 50 else ''}'")
            
            regex_data = pdfplumber_result.get("regex_data", {})
            if regex_data:
                print(f"   🔍 Regex pattern matches:")
                for field, data in regex_data.items():
                    match_count = data.get("match_count", 0)
                    if match_count > 0:
                        print(f"      {field}: {match_count} matches found")
            
            text_search_data = pdfplumber_result.get("text_search_data", {})
            if text_search_data:
                print(f"   🔎 Text search results:")
                for field, data in text_search_data.items():
                    match_count = data.get("match_count", 0)
                    if match_count > 0:
                        print(f"      {field}: {match_count} contexts found")
            
            # Demonstrate combined parsing (LlamaParse + pdfplumber)
            print(f"\n🔄 Testing combined parsing (LlamaParse + pdfplumber)...")
            
            try:
                combined_result = perform_combined_parsing(pdf_path, extraction_rules)
                
                # Save combined results
                save_processed_data(doc_id, "combined_parsing", combined_result)
                
                methods_used = combined_result.get("metadata", {}).get("methods_used", [])
                processing_time = combined_result.get("metadata", {}).get("processing_time_seconds", 0)
                
                print(f"✅ Combined parsing completed!")
                print(f"   Methods used: {', '.join(methods_used)}")
                print(f"   Processing time: {processing_time} seconds")
                
                # Show cross-validation results if available
                cross_validation = combined_result.get("combined_analysis", {}).get("cross_validation", {})
                if cross_validation:
                    print(f"   🔗 Cross-validation results:")
                    for field, validation in cross_validation.items():
                        found = "✅" if validation.get("found_in_markdown", False) else "❌"
                        print(f"      {field}: {found} (confidence: {validation.get('confidence', 0):.1f})")
                
            except Exception as e:
                print(f"⚠️  Combined parsing failed: {e}")
                save_processed_data(doc_id, "combined_parsing_error", {"error": str(e)})
            
        except Exception as e:
            print(f"⚠️  pdfplumber extraction failed: {e}")
            save_processed_data(doc_id, "pdfplumber_error", {"error": str(e)})
        
        # Perform LLM-based entity extraction
        print(f"\n🤖 Testing LLM entity extraction with Gemini...")
        
        entity_extraction_performed = False
        form_filling_performed = False
        try:
            if check_llm_availability():
                # Prepare document content for entity extraction
                document_content_for_llm = ""
                
                # Try to get content from LlamaParse first
                try:
                    combined_data = get_processed_data(doc_id, "combined_parsing")
                    if "llamaparse_results" in combined_data and "markdown_content" in combined_data["llamaparse_results"]:
                        document_content_for_llm = combined_data["llamaparse_results"]["markdown_content"]
                        print(f"   📝 Using LlamaParse content ({len(document_content_for_llm)} chars)")
                except:
                    pass
                
                # Fallback to pdfplumber results if no LlamaParse content
                if not document_content_for_llm:
                    try:
                        pdfplumber_data = get_processed_data(doc_id, "pdfplumber_extraction")
                        # Convert pdfplumber results to text format
                        content_parts = []
                        
                        # Add regex matches
                        for field, data in pdfplumber_data.get("regex_data", {}).items():
                            if data.get("matches"):
                                matches_text = ", ".join([m["match"] for m in data["matches"]])
                                content_parts.append(f"{field}: {matches_text}")
                        
                        # Add text search contexts
                        for field, data in pdfplumber_data.get("text_search_data", {}).items():
                            if data.get("contexts"):
                                for context in data["contexts"][:2]:  # First 2 contexts
                                    content_parts.append(context["context"])
                        
                        if content_parts:
                            document_content_for_llm = "\n\n".join(content_parts)
                            print(f"   📋 Using pdfplumber content ({len(document_content_for_llm)} chars)")
                    except:
                        pass
                
                # Perform entity extraction if we have content
                if document_content_for_llm:
                    print(f"🧠 Starting entity extraction with Gemini API...")
                    
                    extraction_result = extract_entities_with_gemini(document_content_for_llm)
                    
                    # Validate extracted entities
                    validation_result = validate_extracted_entities(extraction_result["extracted_entities"])
                    
                    # Combine results
                    final_result = {
                        "extracted_entities": extraction_result["extracted_entities"],
                        "validation": validation_result,
                        "metadata": extraction_result["metadata"]
                    }
                    
                    # Save entity extraction results
                    save_processed_data(doc_id, "llm_entity_extraction", final_result)
                    print(f"✅ Entity extraction completed!")
                    
                    # Display key findings
                    entities = extraction_result["extracted_entities"]
                    validation_report = validation_result["validation_report"]
                    
                    print(f"   🎯 Extracted entities: {validation_report['populated_fields']}/{validation_report['total_fields']} fields")
                    print(f"   📊 Confidence score: {validation_report['confidence_score']:.2f}")
                    print(f"   ⚡ Processing time: {extraction_result['metadata']['processing_time_seconds']} seconds")
                    
                    # Show key extracted entities
                    key_entities = ["patient_name", "requested_drug_name", "primary_diagnosis", "prescriber_name", "insurance_plan"]
                    found_key_entities = []
                    for key in key_entities:
                        if key in entities and entities[key]:
                            found_key_entities.append(f"{key}: {entities[key]}")
                    
                    if found_key_entities:
                        print(f"   🔍 Key entities found:")
                        for entity in found_key_entities[:3]:  # Show first 3
                            print(f"      {entity}")
                    
                    if validation_report["validation_issues"]:
                        print(f"   ⚠️  Validation issues: {len(validation_report['validation_issues'])}")
                    
                    # Update document status
                    save_document_metadata(doc_id, {"status": "entity_extraction_completed"})
                    entity_extraction_performed = True
                    
                    # Step 5: Form Filling with extracted entities
                    print(f"\n📋 Starting form filling process...")
                    form_filling_performed = False
                    
                    try:
                        if check_form_filler_availability():
                            # Try to populate InsureCo Ozempic form as example
                            populated_form = load_and_populate_form(entities, "InsureCo_Ozempic")
                            
                            # Save form filling results
                            save_processed_data(doc_id, "form_filling_InsureCo_Ozempic", populated_form)
                            
                            form_metadata = populated_form["form_metadata"]
                            print(f"✅ Form filling completed!")
                            print(f"   📋 Form: {form_metadata['schema_name']} v{form_metadata['schema_version']}")
                            print(f"   📊 Completion: {form_metadata['populated_fields_count']}/{form_metadata['total_fields_count']} fields ({form_metadata['completion_rate']:.1%})")
                            
                            if form_metadata["missing_fields"]:
                                print(f"   ⚠️  Missing required fields: {len(form_metadata['missing_fields'])}")
                                if len(form_metadata["missing_fields"]) <= 3:
                                    print(f"      {', '.join(form_metadata['missing_fields'])}")
                            
                            # Show sample populated fields
                            form_data = populated_form["form_data"]
                            sample_fields = ["member_id", "patient_first_name", "requested_drug_name", "primary_diagnosis_description"]
                            populated_fields = []
                            
                            for field in sample_fields:
                                if field in form_data and form_data[field]["value"]:
                                    populated_fields.append(f"{field}: {form_data[field]['value']}")
                            
                            if populated_fields:
                                print(f"   📝 Sample populated fields:")
                                for field_info in populated_fields[:3]:  # Show first 3
                                    print(f"      {field_info}")
                            
                            # Update document status
                            save_document_metadata(doc_id, {"status": "form_filling_completed"})
                            form_filling_performed = True
                            
                            # Step 6: Generate filled PDF
                            print(f"\n📄 Starting PDF generation...")
                            pdf_generation_performed = False
                            
                            try:
                                # Check if template exists
                                template_path = Path("data/prior_auth_template.pdf")
                                if template_path.exists():
                                    # Generate output path
                                    output_path = Path(f"data/{doc_id}_filled_form.pdf")
                                    
                                    # Use FormFillerService to generate filled PDF
                                    form_service = FormFillerService()
                                    form_service.generate_filled_pdf(
                                        str(template_path),
                                        populated_form,
                                        str(output_path)
                                    )
                                    
                                    # Get PDF generation stats from metadata
                                    pdf_stats = populated_form["form_metadata"].get("pdf_generation", {})
                                    
                                    print(f"✅ PDF generation completed!")
                                    print(f"   📄 Output: {output_path.name}")
                                    print(f"   📊 Fields filled: {pdf_stats.get('fill_statistics', {}).get('fields_filled', 0)}")
                                    print(f"   📈 Completion: {pdf_stats.get('completion_rate', 0):.1%}")
                                    
                                    # Save PDF generation results
                                    save_processed_data(doc_id, "pdf_generation", {
                                        "output_path": str(output_path),
                                        "template_used": str(template_path),
                                        "generation_stats": pdf_stats
                                    })
                                    
                                    # Update document status
                                    save_document_metadata(doc_id, {"status": "pdf_generation_completed"})
                                    pdf_generation_performed = True
                                    
                                else:
                                    print(f"⚠️  PDF template not found: {template_path}")
                                    print(f"   Run 'python create_pdf_template.py' to create template")
                                    save_processed_data(doc_id, "pdf_generation_error", {"error": "Template not found"})
                                    
                            except FormFillerError as e:
                                print(f"❌ PDF generation failed: {e}")
                                save_processed_data(doc_id, "pdf_generation_error", {"error": str(e)})
                            except Exception as e:
                                print(f"❌ Unexpected PDF generation error: {e}")
                                save_processed_data(doc_id, "pdf_generation_error", {"error": str(e)})
                            
                        else:
                            print(f"⚠️  Form filler service not available")
                            save_processed_data(doc_id, "form_filling_error", {"error": "Form filler service not available"})
                            
                    except FormFillerError as e:
                        print(f"❌ Form filling failed: {e}")
                        save_processed_data(doc_id, "form_filling_error", {"error": str(e)})
                    except Exception as e:
                        print(f"❌ Unexpected form filling error: {e}")
                        save_processed_data(doc_id, "form_filling_error", {"error": str(e)})
                    
                else:
                    print(f"⚠️  No content available for entity extraction")
                    save_processed_data(doc_id, "llm_entity_extraction_error", {"error": "No document content available"})
                    
            else:
                print(f"⚠️  LLM service not available (check GEMINI_API_KEY)")
                save_document_metadata(doc_id, {"status": "llm_unavailable"})
                
        except LLMServiceError as e:
            print(f"❌ LLM entity extraction failed: {e}")
            save_processed_data(doc_id, "llm_entity_extraction_error", {"error": str(e)})
        except Exception as e:
            print(f"❌ Unexpected LLM error: {e}")
            save_processed_data(doc_id, "llm_entity_extraction_error", {"error": str(e)})
        
        # Display stored data
        print(f"\n📊 Document Processing Summary")
        print("-" * 35)
        stored_metadata = get_document_metadata(doc_id)
        print(f"Document ID: {doc_id[:8]}...")
        print(f"Status: {stored_metadata['status']}")
        print(f"Created: {stored_metadata['created_at']}")
        print(f"OCR performed: {'Yes' if ocr_performed else 'No'}")
        print(f"Parsing performed: {'Yes' if parsing_performed else 'No'}")
        print(f"Entity extraction performed: {'Yes' if entity_extraction_performed else 'No'}")
        print(f"Form filling performed: {'Yes' if form_filling_performed else 'No'}")
        print(f"PDF generation performed: {'Yes' if 'pdf_generation_performed' in locals() and pdf_generation_performed else 'No'}")
        
        # Show processing stages
        from services.data_store import get_document_stages
        stages = get_document_stages(doc_id)
        if stages:
            print(f"Processing stages: {', '.join(stages)}")
        
        print("✅ All processing completed successfully!")
        return doc_id
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return None
    except Exception as e:
        print(f"❌ Error testing PDF: {e}")
        return None


def main():
    """
    Main function to demonstrate PDF utility functions.
    """
    print("🤖 PriorAuthAutomation - PDF Utils Test")
    print("=" * 50)
    
    # Display service information
    print("\n🔧 Service Status:")
    print("-" * 20)
    
    # OCR Service
    ocr_info = get_ocr_service_info()
    print(f"OCR: {ocr_info['service_name']}")
    print(f"  Model: {ocr_info['model']}")
    print(f"  API Key: {'✅' if ocr_info['api_key_configured'] else '❌'}")
    
    # Parsing Service
    parsing_info = get_parsing_service_info()
    print(f"Parser: {parsing_info['service_name']}")
    print(f"  Output: {parsing_info['output_format']}")
    print(f"  API Key: {'✅' if parsing_info['api_key_configured'] else '❌'}")
    print(f"  Formats: {', '.join(parsing_info['supported_formats'])}")
    
    # LLM Service
    llm_info = get_llm_service_info()
    print(f"LLM: {llm_info['service_name']}")
    print(f"  Model: {llm_info['model']}")
    print(f"  API Key: {'✅' if llm_info['api_key_configured'] else '❌'}")
    print(f"  Output: {llm_info['response_format']}")
    
    # Form Filler Service
    form_filler_info = get_form_filler_service_info()
    print(f"Form Filler: {form_filler_info['service_name']}")
    print(f"  Available: {'✅' if check_form_filler_availability() else '❌'}")
    print(f"  Features: {len(form_filler_info['supported_features'])} features")
    print(f"  Schema Dir: {Path(form_filler_info['schema_directory']).name}/")
    
    # Check if a test PDF was provided as command line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if os.path.exists(pdf_path):
            test_pdf_functions(pdf_path)
        else:
            print(f"❌ PDF file not found: {pdf_path}")
            return
    else:
        # Try to create a sample PDF for testing
        sample_pdf = create_sample_pdf()
        
        if sample_pdf and os.path.exists(sample_pdf):
            doc_id = test_pdf_functions(sample_pdf)
            
            # Show stored documents
            print(f"\n📁 Currently stored documents:")
            documents = list_documents()
            for doc in documents[-3:]:  # Show last 3 documents
                try:
                    meta = get_document_metadata(doc)
                    print(f"   - {doc[:8]}... ({meta.get('status', 'unknown')})")
                except:
                    print(f"   - {doc[:8]}... (metadata error)")
            
            # Clean up the sample file
            try:
                os.remove(sample_pdf)
                print(f"🗑️  Cleaned up sample file: {sample_pdf}")
            except OSError:
                print(f"⚠️  Could not remove sample file: {sample_pdf}")
        else:
            print("\n📝 Usage:")
            print("python main.py [path_to_pdf_file]")
            print("\nOr install reportlab to create a sample PDF:")
            print("pip install reportlab")


if __name__ == "__main__":
    main() 