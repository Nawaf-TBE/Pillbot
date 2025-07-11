"""
Orchestrator for PriorAuthAutomation Pipeline

This module provides the main orchestrator for the entire prior authorization document processing
pipeline, coordinating all services and managing the workflow from document input to final PDF output.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all services
from services.pdf_utils import check_pdf_is_native, get_pdf_page_count, get_pdf_info
from services.data_store import (
    generate_document_id, save_document_metadata, save_processed_data,
    get_document_metadata, get_processed_data, list_documents
)
from services.ocr_service import (
    perform_tesseract_ocr, check_ocr_availability, get_ocr_service_info, OCRError
)
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
    FormFillerService, load_and_populate_form, generate_filled_pdf,
    get_form_filler_service_info, check_form_filler_availability, FormFillerError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    """Enumeration of pipeline stages for tracking progress."""
    INITIALIZATION = "initialization"
    PDF_ANALYSIS = "pdf_analysis"
    OCR_PROCESSING = "ocr_processing"
    DOCUMENT_PARSING = "document_parsing"
    ENTITY_EXTRACTION = "entity_extraction"
    FORM_FILLING = "form_filling"
    PDF_GENERATION = "pdf_generation"
    COMPLETION = "completion"

class PipelineStatus(Enum):
    """Enumeration of pipeline status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class PipelineError(Exception):
    """Custom exception for pipeline errors."""
    def __init__(self, stage: PipelineStage, message: str, original_error: Optional[Exception] = None):
        self.stage = stage
        self.message = message
        self.original_error = original_error
        super().__init__(f"Pipeline failed at {stage.value}: {message}")

class PipelineOrchestrator:
    """
    Main orchestrator for the PriorAuthAutomation pipeline.
    
    Manages the complete workflow from document input to final PDF output,
    with comprehensive error handling, logging, and progress tracking.
    """
    
    def __init__(self, output_directory: Optional[str] = None):
        """
        Initialize the pipeline orchestrator.
        
        Args:
            output_directory: Directory for output files (optional)
        """
        self.output_directory = Path(output_directory) if output_directory else Path("data")
        self.output_directory.mkdir(exist_ok=True)
        
        # Pipeline state
        self.document_id: Optional[str] = None
        self.document_path: Optional[Path] = None
        self.current_stage = PipelineStage.INITIALIZATION
        self.stage_results: Dict[PipelineStage, Dict[str, Any]] = {}
        self.pipeline_metadata: Dict[str, Any] = {}
        
        # Service availability cache
        self._service_availability: Dict[str, bool] = {}
        
        logger.info("Pipeline orchestrator initialized")
    
    def run_pipeline(self, document_path: str, schema_name: str = "InsureCo_Ozempic", document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the complete prior authorization processing pipeline.
        
        Args:
            document_path: Path to the input PDF document
            schema_name: Name of the form schema to use
            document_id: Optional document ID to use (generates new one if not provided)
            
        Returns:
            Dictionary containing pipeline results and metadata
            
        Raises:
            PipelineError: If any critical stage fails
        """
        try:
            # Initialize pipeline
            pipeline_start_time = datetime.now()
            self.document_path = Path(document_path)
            self.document_id = document_id if document_id else generate_document_id()
            
            if not self.document_path.exists():
                raise PipelineError(
                    PipelineStage.INITIALIZATION,
                    f"Document not found: {document_path}"
                )
            
            logger.info(f"🚀 Starting pipeline for document: {self.document_path.name}")
            logger.info(f"📋 Document ID: {self.document_id}")
            logger.info(f"🔧 Schema: {schema_name}")
            
            # Initialize pipeline metadata
            self.pipeline_metadata = {
                "document_id": self.document_id,
                "document_path": str(self.document_path),
                "schema_name": schema_name,
                "pipeline_start_time": pipeline_start_time.isoformat(),
                "stages_completed": [],
                "stages_skipped": [],
                "stages_failed": [],
                "service_availability": self._check_service_availability()
            }
            
            # Save initial metadata
            self._save_pipeline_metadata("pipeline_started")
            
            # Execute pipeline stages
            results = {}
            
            # Stage 1: PDF Analysis
            results["pdf_analysis"] = self._execute_stage(
                PipelineStage.PDF_ANALYSIS,
                self._stage_pdf_analysis
            )
            
            # Stage 2: OCR Processing (conditional)
            results["ocr_processing"] = self._execute_stage(
                PipelineStage.OCR_PROCESSING,
                self._stage_ocr_processing,
                conditional=True
            )
            
            # Stage 3: Document Parsing
            results["document_parsing"] = self._execute_stage(
                PipelineStage.DOCUMENT_PARSING,
                self._stage_document_parsing
            )
            
            # Stage 4: Entity Extraction
            results["entity_extraction"] = self._execute_stage(
                PipelineStage.ENTITY_EXTRACTION,
                self._stage_entity_extraction
            )
            
            # Stage 5: Form Filling
            results["form_filling"] = self._execute_stage(
                PipelineStage.FORM_FILLING,
                lambda: self._stage_form_filling(schema_name)
            )
            
            # Stage 6: PDF Generation
            results["pdf_generation"] = self._execute_stage(
                PipelineStage.PDF_GENERATION,
                self._stage_pdf_generation
            )
            
            # Complete pipeline
            pipeline_end_time = datetime.now()
            total_duration = (pipeline_end_time - pipeline_start_time).total_seconds()
            
            self.pipeline_metadata.update({
                "pipeline_end_time": pipeline_end_time.isoformat(),
                "total_duration_seconds": total_duration,
                "status": "completed"
            })
            
            self._save_pipeline_metadata("pipeline_completed")
            
            logger.info(f"✅ Pipeline completed successfully in {total_duration:.2f} seconds")
            
            # Prepare final results
            final_results = {
                "pipeline_metadata": self.pipeline_metadata,
                "stage_results": results,
                "document_id": self.document_id,
                "summary": self._generate_pipeline_summary(results)
            }
            
            return final_results
            
        except PipelineError:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected pipeline error: {e}")
            self._handle_pipeline_failure(PipelineStage.INITIALIZATION, str(e), e)
            raise PipelineError(PipelineStage.INITIALIZATION, f"Unexpected error: {e}", e)
    
    def _execute_stage(self, stage: PipelineStage, stage_func, conditional: bool = False) -> Dict[str, Any]:
        """Execute a single pipeline stage with error handling."""
        self.current_stage = stage
        stage_start_time = datetime.now()
        
        logger.info(f"🔄 Starting stage: {stage.value}")
        
        try:
            result = stage_func()
            stage_duration = (datetime.now() - stage_start_time).total_seconds()
            
            stage_result = {
                "status": PipelineStatus.COMPLETED.value,
                "start_time": stage_start_time.isoformat(),
                "duration_seconds": stage_duration,
                "result": result
            }
            
            self.stage_results[stage] = stage_result
            self.pipeline_metadata["stages_completed"].append(stage.value)
            
            logger.info(f"✅ Stage {stage.value} completed in {stage_duration:.2f}s")
            return stage_result
            
        except Exception as e:
            stage_duration = (datetime.now() - stage_start_time).total_seconds()
            
            if conditional:
                logger.warning(f"⚠️  Stage {stage.value} skipped: {e}")
                
                stage_result = {
                    "status": PipelineStatus.SKIPPED.value,
                    "start_time": stage_start_time.isoformat(),
                    "duration_seconds": stage_duration,
                    "reason": str(e)
                }
                
                self.stage_results[stage] = stage_result
                self.pipeline_metadata["stages_skipped"].append(stage.value)
                return stage_result
            else:
                logger.error(f"❌ Stage {stage.value} failed: {e}")
                self._handle_pipeline_failure(stage, str(e), e)
                raise PipelineError(stage, str(e), e)
    
    def _stage_pdf_analysis(self) -> Dict[str, Any]:
        """Execute PDF analysis stage."""
        try:
            page_count = get_pdf_page_count(str(self.document_path))
            is_native = check_pdf_is_native(str(self.document_path))
            pdf_info = get_pdf_info(str(self.document_path))
            
            result = {
                "page_count": page_count,
                "has_native_text": is_native,
                "file_size_mb": pdf_info["file_size_mb"],
                "metadata": pdf_info["metadata"],
                "needs_ocr": not is_native
            }
            
            save_processed_data(self.document_id, "pdf_analysis", result)
            logger.info(f"📄 PDF Analysis: {page_count} pages, native text: {is_native}")
            
            return result
        except Exception as e:
            raise Exception(f"PDF analysis failed: {e}")
    
    def _stage_ocr_processing(self) -> Dict[str, Any]:
        """Execute OCR processing stage (conditional)."""
        pdf_analysis = self.stage_results.get(PipelineStage.PDF_ANALYSIS, {}).get("result", {})
        needs_ocr = pdf_analysis.get("needs_ocr", True)
        
        if not needs_ocr:
            raise Exception("PDF has native text, OCR not needed")
        
        if not check_ocr_availability():
            raise Exception("OCR service not available (check Tesseract installation)")
        
        try:
            ocr_result = perform_tesseract_ocr(str(self.document_path))
            
            result = {
                "extracted_text": ocr_result["extracted_text"],
                "confidence_score": ocr_result["confidence_score"],
                "processing_time": ocr_result["processing_time_seconds"],
                "page_count": ocr_result["page_count"]
            }
            
            save_processed_data(self.document_id, "ocr_processing", result)
            logger.info(f"👁️  OCR completed: {len(result['extracted_text'])} characters extracted")
            
            return result
        except OCRError as e:
            raise Exception(f"OCR processing failed: {e}")
    
    def _stage_document_parsing(self) -> Dict[str, Any]:
        """Execute document parsing stage."""
        try:
            content_available = False
            parsing_results = {}
            
            # Try LlamaParse first
            if check_parsing_availability():
                try:
                    llamaparse_result = perform_llamaparse_with_metadata(str(self.document_path))
                    parsing_results["llamaparse"] = {
                        "success": True,
                        "markdown_content": llamaparse_result["markdown_content"],
                        "metadata": llamaparse_result["metadata"]
                    }
                    content_available = True
                    logger.info("📝 LlamaParse completed successfully")
                except ParsingError as e:
                    parsing_results["llamaparse"] = {
                        "success": False,
                        "error": str(e)
                    }
                    logger.warning(f"⚠️  LlamaParse failed: {e}")
            else:
                parsing_results["llamaparse"] = {
                    "success": False,
                    "error": "LlamaParse service not available"
                }
                logger.warning("⚠️  LlamaParse service not available")
            
            # Try pdfplumber as fallback
            try:
                extraction_rules = self._create_extraction_rules()
                pdfplumber_result = extract_with_pdfplumber(str(self.document_path), extraction_rules)
                
                parsing_results["pdfplumber"] = {
                    "success": True,
                    "extracted_data": pdfplumber_result["extracted_data"],
                    "metadata": pdfplumber_result["metadata"]
                }
                content_available = True
                logger.info("📊 pdfplumber extraction completed")
            except Exception as e:
                parsing_results["pdfplumber"] = {
                    "success": False,
                    "error": str(e)
                }
                logger.warning(f"⚠️  pdfplumber extraction failed: {e}")
            
            if not content_available:
                raise Exception("All parsing methods failed")
            
            result = {
                "parsing_methods": parsing_results,
                "content_available": content_available,
                "primary_content": self._get_primary_content(parsing_results)
            }
            
            save_processed_data(self.document_id, "document_parsing", result)
            return result
            
        except Exception as e:
            raise Exception(f"Document parsing failed: {e}")
    
    def _stage_entity_extraction(self) -> Dict[str, Any]:
        """Execute entity extraction stage."""
        if not check_llm_availability():
            raise Exception("LLM service not available (check GEMINI_API_KEY)")
        
        try:
            document_content = self._get_document_content()
            
            if not document_content:
                raise Exception("No document content available for entity extraction")
            
            extraction_result = extract_entities_with_gemini(document_content)
            validation_result = validate_extracted_entities(extraction_result["extracted_entities"])
            
            result = {
                "extracted_entities": extraction_result["extracted_entities"],
                "metadata": extraction_result["metadata"],
                "validation_report": validation_result["validation_report"],
                "confidence_score": validation_result["validation_report"]["confidence_score"]
            }
            
            save_processed_data(self.document_id, "entity_extraction", result)
            
            entities_count = validation_result["validation_report"]["populated_fields"]
            total_fields = validation_result["validation_report"]["total_fields"]
            confidence = validation_result["validation_report"]["confidence_score"]
            
            logger.info(f"🎯 Entity extraction: {entities_count}/{total_fields} fields, confidence: {confidence:.2f}")
            
            return result
            
        except LLMServiceError as e:
            raise Exception(f"Entity extraction failed: {e}")
    
    def _stage_form_filling(self, schema_name: str) -> Dict[str, Any]:
        """Execute form filling stage."""
        if not check_form_filler_availability():
            raise Exception("Form filler service not available")
        
        try:
            entity_results = self.stage_results.get(PipelineStage.ENTITY_EXTRACTION, {}).get("result", {})
            entities = entity_results.get("extracted_entities", {})
            
            if not entities:
                raise Exception("No extracted entities available for form filling")
            
            populated_form = load_and_populate_form(entities, schema_name)
            
            result = {
                "populated_form": populated_form,
                "schema_name": schema_name,
                "completion_rate": populated_form["form_metadata"]["completion_rate"],
                "populated_fields": populated_form["form_metadata"]["populated_fields_count"],
                "total_fields": populated_form["form_metadata"]["total_fields_count"]
            }
            
            save_processed_data(self.document_id, "form_filling", result)
            
            completion_rate = result["completion_rate"]
            populated_fields = result["populated_fields"]
            total_fields = result["total_fields"]
            
            logger.info(f"📋 Form filling: {populated_fields}/{total_fields} fields ({completion_rate:.1%})")
            
            return result
            
        except FormFillerError as e:
            raise Exception(f"Form filling failed: {e}")
    
    def _stage_pdf_generation(self) -> Dict[str, Any]:
        """Execute PDF generation stage."""
        try:
            form_results = self.stage_results.get(PipelineStage.FORM_FILLING, {}).get("result", {})
            populated_form = form_results.get("populated_form", {})
            
            if not populated_form:
                raise Exception("No populated form data available for PDF generation")
            
            output_filename = f"{self.document_id}_filled_form.pdf"
            output_path = self.output_directory / output_filename
            
            # Check if user provided a form template
            template_path = None
            user_template_path = self.output_directory / f"{self.document_id}_form_template.pdf"
            default_template_path = self.output_directory / "prior_auth_template.pdf"
            
            if user_template_path.exists():
                template_path = user_template_path
                logger.info(f"📝 Using user-provided form template: {template_path}")
            elif default_template_path.exists():
                template_path = default_template_path
                logger.info(f"📝 Using default form template: {template_path}")
            else:
                # Generate a simple PDF with the data if no template exists
                logger.info("📝 No template found, generating simple data PDF")
                return self._generate_simple_data_pdf(populated_form, output_path)
            
            # Generate filled PDF using template with enhanced field matching
            form_service = FormFillerService()
            
            try:
                # Try standard form filling first
                form_service.generate_filled_pdf(
                    str(template_path),
                    populated_form,
                    str(output_path)
                )
                
                pdf_stats = populated_form["form_metadata"].get("pdf_generation", {})
                fill_stats = pdf_stats.get("fill_statistics", {})
                fields_filled = fill_stats.get("fields_filled", 0)
                fields_found = fill_stats.get("fields_found", 0)
                
                # If no fields were filled (field name mismatch), use hybrid approach
                if fields_filled == 0 and fields_found > 0:
                    logger.info("📝 No field matches found, generating hybrid PDF with data overlay")
                    return self._generate_hybrid_pdf(populated_form, template_path, output_path)
                
                completion_rate = pdf_stats.get("completion_rate", 0)
                
                result = {
                    "output_path": str(output_path),
                    "template_path": str(template_path),
                    "generation_stats": pdf_stats,
                    "file_size_kb": output_path.stat().st_size / 1024 if output_path.exists() else 0,
                    "generation_method": "form_filling"
                }
                
                save_processed_data(self.document_id, "pdf_generation", result)
                
                logger.info(f"📄 PDF generation: {fields_filled} fields filled ({completion_rate:.1%})")
                
                return result
                
            except Exception as e:
                logger.warning(f"Standard form filling failed: {e}")
                logger.info("📝 Falling back to hybrid PDF generation")
                return self._generate_hybrid_pdf(populated_form, template_path, output_path)
            
        except Exception as e:
            raise Exception(f"PDF generation failed: {e}")
    
    def _generate_hybrid_pdf(self, populated_form: Dict[str, Any], template_path: Path, output_path: Path) -> Dict[str, Any]:
        """Generate a hybrid PDF using the template as background and overlaying extracted data."""
        try:
            import fitz  # PyMuPDF
            
            # Open the template PDF
            template_doc = fitz.open(str(template_path))
            
            # Get form data
            form_data = populated_form.get("form_data", {})
            form_metadata = populated_form.get("form_metadata", {})
            
            # Add a new page at the end with extracted data
            data_page = template_doc.new_page()
            
            # Add title
            title_rect = fitz.Rect(50, 50, 550, 80)
            data_page.insert_textbox(title_rect, "Extracted Information", 
                                   fontsize=16, fontname="helv-bold", color=(0, 0, 0))
            
            # Add metadata
            y_pos = 100
            metadata_text = f"Generated: {form_metadata.get('population_timestamp', 'Unknown')}\n"
            metadata_text += f"Schema: {form_metadata.get('schema_name', 'Unknown')}\n"
            metadata_text += f"Completion: {form_metadata.get('populated_fields_count', 0)}/{form_metadata.get('total_fields_count', 0)} fields\n"
            metadata_text += f"Template: {template_path.name}\n"
            
            metadata_rect = fitz.Rect(50, y_pos, 550, y_pos + 80)
            data_page.insert_textbox(metadata_rect, metadata_text, fontsize=10, color=(0.3, 0.3, 0.3))
            
            # Add extracted data in a clean format
            y_pos = 200
            line_height = 20
            
            # Organize data by sections for better readability
            sections = {
                "Patient Information": ["member_id", "patient_first_name", "patient_last_name", "patient_date_of_birth"],
                "Prescriber Information": ["prescriber_name", "prescriber_npi", "prescriber_phone"],
                "Diagnosis": ["primary_diagnosis_code", "primary_diagnosis_description"],
                "Medication": ["requested_drug_name", "requested_strength", "quantity_requested", "days_supply"],
                "Clinical Data": ["a1c_value", "bmi_value", "previous_medications_tried", "clinical_justification"]
            }
            
            for section_name, section_fields in sections.items():
                # Add section header
                if y_pos > 720:  # Add new page if needed
                    data_page = template_doc.new_page()
                    y_pos = 50
                
                section_rect = fitz.Rect(50, y_pos, 550, y_pos + line_height)
                data_page.insert_textbox(section_rect, section_name, 
                                       fontsize=12, fontname="helv-bold", color=(0.2, 0.2, 0.2))
                y_pos += line_height + 5
                
                # Add section fields
                section_has_data = False
                for field_name in section_fields:
                    if field_name in form_data:
                        field_info = form_data[field_name]
                        value = field_info.get("value", "")
                        
                        if value and str(value).strip():
                            section_has_data = True
                            
                            if y_pos > 750:  # Add new page if needed
                                data_page = template_doc.new_page()
                                y_pos = 50
                            
                            # Format field name (make it readable)
                            display_name = field_name.replace("_", " ").title()
                            
                            # Add field with value
                            field_text = f"  {display_name}: {value}"
                            field_rect = fitz.Rect(50, y_pos, 550, y_pos + line_height)
                            data_page.insert_textbox(field_rect, field_text, fontsize=11)
                            
                            y_pos += line_height + 2
                
                if not section_has_data:
                    # Add "No data available" message
                    no_data_rect = fitz.Rect(50, y_pos, 550, y_pos + line_height)
                    data_page.insert_textbox(no_data_rect, "  No data available", 
                                           fontsize=11, color=(0.6, 0.6, 0.6))
                    y_pos += line_height + 2
                
                y_pos += 10  # Extra spacing between sections
            
            # Save the hybrid PDF
            template_doc.save(str(output_path))
            template_doc.close()
            
            file_size_kb = output_path.stat().st_size / 1024 if output_path.exists() else 0
            
            result = {
                "output_path": str(output_path),
                "template_path": str(template_path),
                "generation_type": "hybrid_pdf",
                "file_size_kb": file_size_kb,
                "fields_included": len([f for f in form_data.values() if f.get("value")]),
                "generation_method": "hybrid_overlay"
            }
            
            save_processed_data(self.document_id, "pdf_generation", result)
            
            logger.info(f"📄 Hybrid PDF generated: {result['fields_included']} fields overlaid, {file_size_kb:.1f} KB")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate hybrid PDF: {e}")
            # Fall back to simple data PDF
            return self._generate_simple_data_pdf(populated_form, output_path)
    
    def _generate_simple_data_pdf(self, populated_form: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """Generate a simple PDF with extracted data when no template is available."""
        try:
            import fitz  # PyMuPDF
            
            # Create a new PDF document
            doc = fitz.open()
            page = doc.new_page()
            
            # Get form data
            form_data = populated_form.get("form_data", {})
            form_metadata = populated_form.get("form_metadata", {})
            
            # Add title
            title_rect = fitz.Rect(50, 50, 550, 80)
            page.insert_textbox(title_rect, "Prior Authorization - Extracted Data", 
                              fontsize=16, fontname="helv-bold", color=(0, 0, 0))
            
            # Add metadata
            y_pos = 100
            metadata_text = f"Generated: {form_metadata.get('population_timestamp', 'Unknown')}\n"
            metadata_text += f"Schema: {form_metadata.get('schema_name', 'Unknown')}\n"
            metadata_text += f"Completion: {form_metadata.get('populated_fields_count', 0)}/{form_metadata.get('total_fields_count', 0)} fields\n"
            
            metadata_rect = fitz.Rect(50, y_pos, 550, y_pos + 60)
            page.insert_textbox(metadata_rect, metadata_text, fontsize=10, color=(0.3, 0.3, 0.3))
            
            # Add extracted data
            y_pos = 180
            line_height = 20
            
            for field_name, field_info in form_data.items():
                if y_pos > 750:  # Add new page if needed
                    page = doc.new_page()
                    y_pos = 50
                
                value = field_info.get("value", "")
                confidence = field_info.get("confidence", 0)
                
                if value and str(value).strip():
                    # Format field name (make it readable)
                    display_name = field_name.replace("_", " ").title()
                    
                    # Add field label
                    label_rect = fitz.Rect(50, y_pos, 200, y_pos + line_height)
                    page.insert_textbox(label_rect, f"{display_name}:", 
                                      fontsize=11, fontname="helv-bold")
                    
                    # Add field value
                    value_rect = fitz.Rect(210, y_pos, 550, y_pos + line_height)
                    page.insert_textbox(value_rect, str(value), fontsize=11)
                    
                    # Add confidence if available
                    if confidence > 0:
                        conf_rect = fitz.Rect(560, y_pos, 600, y_pos + line_height)
                        page.insert_textbox(conf_rect, f"{confidence:.0%}", 
                                          fontsize=9, color=(0.5, 0.5, 0.5))
                    
                    y_pos += line_height + 5
            
            # Save the PDF
            doc.save(str(output_path))
            doc.close()
            
            file_size_kb = output_path.stat().st_size / 1024 if output_path.exists() else 0
            
            result = {
                "output_path": str(output_path),
                "template_path": None,
                "generation_type": "simple_data_pdf",
                "file_size_kb": file_size_kb,
                "fields_included": len([f for f in form_data.values() if f.get("value")])
            }
            
            save_processed_data(self.document_id, "pdf_generation", result)
            
            logger.info(f"📄 Simple data PDF generated: {result['fields_included']} fields, {file_size_kb:.1f} KB")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate simple data PDF: {e}")
            raise Exception(f"Simple PDF generation failed: {e}")
    
    def _check_service_availability(self) -> Dict[str, bool]:
        """Check availability of all services."""
        return {
            "ocr_service": check_ocr_availability(),
            "parsing_service": check_parsing_availability(),
            "llm_service": check_llm_availability(),
            "form_filler_service": check_form_filler_availability()
        }
    
    def _create_extraction_rules(self) -> Dict[str, Any]:
        """Create sample extraction rules for pdfplumber."""
        return {
            "regex_patterns": {
                "member_id": {
                    "pattern": r"[A-Z]{2,3}\d{6,9}",
                    "flags": 0,
                    "page": "all"
                },
                "dates": {
                    "pattern": r"\d{1,2}/\d{1,2}/\d{4}",
                    "flags": 0,
                    "page": "all"
                },
                "medications": {
                    "pattern": r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\d+(?:\.\d+)?\s*(?:mg|ml|g)",
                    "flags": 0,
                    "page": "all"
                }
            },
            "text_search": {
                "patient_info": {
                    "search_terms": ["Patient Name", "Member Name", "DOB", "Date of Birth"],
                    "context_lines": 3,
                    "page": "all"
                },
                "diagnosis_info": {
                    "search_terms": ["Diagnosis", "Condition", "ICD-10"],
                    "context_lines": 2,
                    "page": "all"
                }
            }
        }
    
    def _get_primary_content(self, parsing_results: Dict[str, Any]) -> str:
        """Get primary document content from parsing results."""
        if parsing_results.get("llamaparse", {}).get("success"):
            return parsing_results["llamaparse"]["markdown_content"]
        
        if parsing_results.get("pdfplumber", {}).get("success"):
            extracted_data = parsing_results["pdfplumber"]["extracted_data"]
            text_parts = []
            for page_data in extracted_data.get("pages", []):
                if "text" in page_data:
                    text_parts.append(page_data["text"])
            return "\n\n".join(text_parts)
        
        return ""
    
    def _get_document_content(self) -> str:
        """Get document content from previous processing stages."""
        parsing_results = self.stage_results.get(PipelineStage.DOCUMENT_PARSING, {}).get("result", {})
        if parsing_results:
            content = parsing_results.get("primary_content", "")
            if content:
                return content
        
        ocr_results = self.stage_results.get(PipelineStage.OCR_PROCESSING, {}).get("result", {})
        if ocr_results:
            return ocr_results.get("extracted_text", "")
        
        return ""
    
    def _handle_pipeline_failure(self, stage: PipelineStage, error_message: str, original_error: Exception):
        """Handle pipeline failure by saving error state."""
        self.pipeline_metadata.update({
            "status": "failed",
            "failed_stage": stage.value,
            "error_message": error_message,
            "failure_time": datetime.now().isoformat()
        })
        
        self.pipeline_metadata["stages_failed"].append(stage.value)
        
        save_processed_data(self.document_id, f"{stage.value}_error", {
            "error_message": error_message,
            "error_type": type(original_error).__name__ if original_error else "Unknown"
        })
        
        self._save_pipeline_metadata("pipeline_failed")
    
    def _save_pipeline_metadata(self, status: str):
        """Save pipeline metadata to data store."""
        try:
            save_document_metadata(self.document_id, {
                "status": status,
                "pipeline_metadata": self.pipeline_metadata
            })
        except Exception as e:
            logger.error(f"Failed to save pipeline metadata: {e}")
    
    def _generate_pipeline_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of pipeline execution."""
        summary = {
            "total_stages": len(PipelineStage),
            "completed_stages": len(self.pipeline_metadata["stages_completed"]),
            "skipped_stages": len(self.pipeline_metadata["stages_skipped"]),
            "failed_stages": len(self.pipeline_metadata["stages_failed"]),
            "success_rate": len(self.pipeline_metadata["stages_completed"]) / len(PipelineStage),
            "output_files": []
        }
        
        pdf_gen_result = results.get("pdf_generation", {}).get("result", {})
        if pdf_gen_result and "output_path" in pdf_gen_result:
            summary["output_files"].append({
                "type": "filled_pdf",
                "path": pdf_gen_result["output_path"],
                "size_kb": pdf_gen_result.get("file_size_kb", 0)
            })
        
        return summary


def run_pipeline(document_path: str, schema_name: str = "InsureCo_Ozempic", 
                output_directory: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to run the complete pipeline.
    
    Args:
        document_path: Path to the input PDF document
        schema_name: Name of the form schema to use
        output_directory: Directory for output files
        document_id: Optional document ID to use (generates new one if not provided)
        
    Returns:
        Dictionary containing pipeline results and metadata
    """
    orchestrator = PipelineOrchestrator(output_directory)
    return orchestrator.run_pipeline(document_path, schema_name, document_id)


def get_pipeline_info() -> Dict[str, Any]:
    """Get information about the pipeline and service availability."""
    orchestrator = PipelineOrchestrator()
    
    return {
        "pipeline_name": "PriorAuthAutomation Pipeline",
        "version": "1.0.0",
        "stages": [stage.value for stage in PipelineStage],
        "service_availability": orchestrator._check_service_availability(),
        "services": {
            "ocr": get_ocr_service_info(),
            "parsing": get_parsing_service_info(),
            "llm": get_llm_service_info(),
            "form_filler": get_form_filler_service_info()
        }
    }
 