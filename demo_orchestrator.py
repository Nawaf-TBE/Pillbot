#!/usr/bin/env python3
"""
Demo of the PriorAuthAutomation Orchestrator

This script demonstrates the orchestrator functionality with minimal dependencies,
showing how it coordinates services and handles pipeline execution.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.orchestrator import (
    PipelineOrchestrator, get_pipeline_info, run_pipeline, 
    PipelineError, PipelineStage
)

def demo_pipeline_info():
    """Demonstrate pipeline information retrieval."""
    print("🔧 Pipeline Information Demo")
    print("=" * 50)
    
    try:
        info = get_pipeline_info()
        
        print(f"Pipeline: {info['pipeline_name']} v{info['version']}")
        print(f"Total Stages: {len(info['stages'])}")
        
        print("\n📋 Pipeline Stages:")
        for i, stage in enumerate(info['stages'], 1):
            print(f"  {i}. {stage.replace('_', ' ').title()}")
        
        print(f"\n🔧 Service Availability:")
        for service, available in info['service_availability'].items():
            status = "✅ Available" if available else "❌ Not Available"
            service_name = service.replace('_', ' ').title()
            print(f"  {service_name}: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting pipeline info: {e}")
        return False

def demo_orchestrator_creation():
    """Demonstrate orchestrator creation and initialization."""
    print("\n🤖 Orchestrator Creation Demo")
    print("=" * 50)
    
    try:
        # Create orchestrator with custom output directory
        orchestrator = PipelineOrchestrator(output_directory="demo_output")
        
        print(f"✅ Orchestrator created successfully")
        print(f"📁 Output directory: {orchestrator.output_directory}")
        print(f"🔧 Current stage: {orchestrator.current_stage.value}")
        print(f"📊 Stage results: {len(orchestrator.stage_results)} stored")
        
        # Check service availability
        availability = orchestrator._check_service_availability()
        available_services = sum(availability.values())
        total_services = len(availability)
        
        print(f"🏥 Services: {available_services}/{total_services} available")
        
        return orchestrator
        
    except Exception as e:
        print(f"❌ Error creating orchestrator: {e}")
        return None

def demo_pipeline_stages():
    """Demonstrate pipeline stage enumeration."""
    print("\n📋 Pipeline Stages Demo")
    print("=" * 50)
    
    try:
        print("Available Pipeline Stages:")
        
        for stage in PipelineStage:
            stage_name = stage.value.replace('_', ' ').title()
            print(f"  • {stage_name}")
            
            # Show stage description based on stage type
            if stage == PipelineStage.INITIALIZATION:
                print("    └─ Sets up pipeline and validates inputs")
            elif stage == PipelineStage.PDF_ANALYSIS:
                print("    └─ Analyzes PDF properties and determines processing needs")
            elif stage == PipelineStage.OCR_PROCESSING:
                print("    └─ Extracts text from scanned documents (conditional)")
            elif stage == PipelineStage.DOCUMENT_PARSING:
                print("    └─ Parses document content using LlamaParse or pdfplumber")
            elif stage == PipelineStage.ENTITY_EXTRACTION:
                print("    └─ Extracts medical entities using LLM")
            elif stage == PipelineStage.FORM_FILLING:
                print("    └─ Populates form fields with extracted data")
            elif stage == PipelineStage.PDF_GENERATION:
                print("    └─ Generates filled PDF from template")
            elif stage == PipelineStage.COMPLETION:
                print("    └─ Finalizes pipeline and saves results")
        
        return True
        
    except Exception as e:
        print(f"❌ Error demonstrating stages: {e}")
        return False

def demo_error_handling():
    """Demonstrate error handling in the orchestrator."""
    print("\n⚠️  Error Handling Demo")
    print("=" * 50)
    
    try:
        # Attempt to run pipeline with non-existent file
        print("Testing pipeline with non-existent file...")
        
        try:
            results = run_pipeline(
                document_path="non_existent_file.pdf",
                schema_name="InsureCo_Ozempic",
                output_directory="demo_output"
            )
            print("❌ Expected error did not occur")
            
        except PipelineError as e:
            print(f"✅ Caught expected PipelineError:")
            print(f"   Stage: {e.stage.value}")
            print(f"   Message: {e.message}")
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in error handling demo: {e}")
        return False

def demo_data_persistence():
    """Demonstrate data persistence capabilities."""
    print("\n💾 Data Persistence Demo")
    print("=" * 50)
    
    try:
        from src.services.data_store import (
            generate_document_id, save_document_metadata, 
            get_document_metadata, list_documents
        )
        
        # Generate a sample document ID
        doc_id = generate_document_id()
        print(f"📋 Generated Document ID: {doc_id[:8]}...")
        
        # Save sample metadata
        sample_metadata = {
            "status": "demo",
            "pipeline_metadata": {
                "document_path": "demo_document.pdf",
                "schema_name": "InsureCo_Ozempic",
                "stages_completed": ["initialization", "pdf_analysis"],
                "service_availability": {
                    "ocr_service": False,
                    "parsing_service": False,
                    "llm_service": False,
                    "form_filler_service": True
                }
            }
        }
        
        save_document_metadata(doc_id, sample_metadata)
        print(f"✅ Saved metadata for document")
        
        # Retrieve and verify metadata
        retrieved_metadata = get_document_metadata(doc_id)
        if retrieved_metadata:
            print(f"✅ Retrieved metadata successfully")
            print(f"   Status: {retrieved_metadata['status']}")
            stages = retrieved_metadata['pipeline_metadata']['stages_completed']
            print(f"   Completed stages: {len(stages)}")
        
        # List documents
        documents = list_documents()
        print(f"📄 Total documents in store: {len(documents)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in data persistence demo: {e}")
        return False

def cleanup_demo():
    """Clean up demo files."""
    print("\n🗑️  Cleanup")
    print("=" * 50)
    
    try:
        demo_files = [
            "sample_prior_auth.pdf",
            "demo_output"
        ]
        
        for item in demo_files:
            item_path = Path(item)
            if item_path.exists():
                if item_path.is_file():
                    item_path.unlink()
                    print(f"🗑️  Removed file: {item}")
                elif item_path.is_dir():
                    import shutil
                    shutil.rmtree(item_path)
                    print(f"🗑️  Removed directory: {item}")
        
        print("✅ Cleanup completed")
        
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

def main():
    """Main demo function."""
    print("🤖 PriorAuthAutomation Orchestrator Demo")
    print("=" * 60)
    print("This demo shows the orchestrator functionality without")
    print("requiring external API keys or dependencies.")
    print("=" * 60)
    
    success_count = 0
    total_demos = 5
    
    # Run demos
    if demo_pipeline_info():
        success_count += 1
    
    if demo_orchestrator_creation():
        success_count += 1
    
    if demo_pipeline_stages():
        success_count += 1
    
    if demo_error_handling():
        success_count += 1
    
    if demo_data_persistence():
        success_count += 1
    
    # Clean up
    cleanup_demo()
    
    # Summary
    print(f"\n📊 Demo Summary")
    print("=" * 50)
    print(f"Successful demos: {success_count}/{total_demos}")
    
    if success_count == total_demos:
        print("✅ All demos completed successfully!")
        print("\n🚀 The orchestrator is ready for use!")
        print("\nTo run with a real document and API keys:")
        print("1. Set up API keys (GEMINI_API_KEY, LLAMAPARSE_API_KEY, etc.)")
        print("2. Install optional dependencies (pip install pdfplumber)")
        print("3. Run: python main.py [path_to_pdf]")
    else:
        print("⚠️  Some demos had issues. Check the output above.")
    
    print(f"\n📋 Pipeline Features:")
    print("• Multi-stage document processing pipeline")
    print("• Robust error handling and logging")
    print("• Data persistence and retrieval")
    print("• Service availability checking")
    print("• Conditional stage execution")
    print("• Comprehensive metadata tracking")

if __name__ == "__main__":
    main() 