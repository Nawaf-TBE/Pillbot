"""
JSON-based data storage for document metadata and processed data.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


def _get_metadata_file_path(document_id: str) -> Path:
    """
    Get the file path for document metadata.
    
    Args:
        document_id (str): Unique document identifier
        
    Returns:
        Path: Path to the metadata JSON file
    """
    return DATA_DIR / f"{document_id}_metadata.json"


def _get_processed_data_file_path(document_id: str) -> Path:
    """
    Get the file path for processed data.
    
    Args:
        document_id (str): Unique document identifier
        
    Returns:
        Path: Path to the processed data JSON file
    """
    return DATA_DIR / f"{document_id}_processed.json"


def _safe_json_write(file_path: Path, data: Dict) -> None:
    """
    Safely write JSON data to file with error handling.
    
    Args:
        file_path (Path): Path to write to
        data (Dict): Data to write
        
    Raises:
        Exception: If file write operation fails
    """
    try:
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first, then move to final location
        temp_file = file_path.with_suffix('.tmp')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        # Atomic move
        temp_file.replace(file_path)
        logger.info(f"Successfully wrote data to {file_path}")
        
    except Exception as e:
        # Clean up temp file if it exists
        if temp_file.exists():
            temp_file.unlink()
        raise Exception(f"Failed to write JSON to {file_path}: {str(e)}")


def _safe_json_read(file_path: Path) -> Dict:
    """
    Safely read JSON data from file with error handling.
    
    Args:
        file_path (Path): Path to read from
        
    Returns:
        Dict: Loaded JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: If file read operation fails
    """
    try:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Successfully read data from {file_path}")
        return data
        
    except FileNotFoundError:
        raise
    except Exception as e:
        raise Exception(f"Failed to read JSON from {file_path}: {str(e)}")


def generate_document_id() -> str:
    """
    Generate a unique document ID.
    
    Returns:
        str: Unique document identifier
    """
    return str(uuid.uuid4())


def save_document_metadata(document_id: str, metadata: Dict) -> None:
    """
    Save metadata like is_native_pdf, status, file_path.
    
    Args:
        document_id (str): Unique document identifier
        metadata (Dict): Document metadata to save
        
    Raises:
        Exception: If save operation fails
    """
    try:
        file_path = _get_metadata_file_path(document_id)
        
        # Add timestamp and document_id to metadata
        enhanced_metadata = {
            "document_id": document_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **metadata
        }
        
        # If file exists, merge with existing data while preserving created_at
        if file_path.exists():
            try:
                existing_data = _safe_json_read(file_path)
                enhanced_metadata["created_at"] = existing_data.get("created_at", enhanced_metadata["created_at"])
            except Exception as e:
                logger.warning(f"Could not read existing metadata, creating new: {e}")
        
        _safe_json_write(file_path, enhanced_metadata)
        logger.info(f"Saved metadata for document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to save metadata for document {document_id}: {e}")
        raise


def get_document_metadata(document_id: str) -> Dict:
    """
    Retrieve metadata for a document.
    
    Args:
        document_id (str): Unique document identifier
        
    Returns:
        Dict: Document metadata
        
    Raises:
        FileNotFoundError: If metadata file doesn't exist
        Exception: If read operation fails
    """
    try:
        file_path = _get_metadata_file_path(document_id)
        metadata = _safe_json_read(file_path)
        logger.info(f"Retrieved metadata for document {document_id}")
        return metadata
        
    except FileNotFoundError:
        logger.error(f"Metadata not found for document {document_id}")
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata for document {document_id}: {e}")
        raise


def save_processed_data(document_id: str, stage_name: str, data: Any) -> None:
    """
    Store data extracted at different stages (e.g., OCR output, parsed data, extracted entities).
    
    Args:
        document_id (str): Unique document identifier
        stage_name (str): Name of the processing stage
        data (Any): Data to save for this stage
        
    Raises:
        Exception: If save operation fails
    """
    try:
        file_path = _get_processed_data_file_path(document_id)
        
        # Load existing processed data or create new structure
        processed_data = {}
        if file_path.exists():
            try:
                processed_data = _safe_json_read(file_path)
            except Exception as e:
                logger.warning(f"Could not read existing processed data, creating new: {e}")
        
        # Initialize structure if needed
        if "document_id" not in processed_data:
            processed_data["document_id"] = document_id
            processed_data["created_at"] = datetime.now().isoformat()
        
        # Update the data for this stage
        processed_data["updated_at"] = datetime.now().isoformat()
        processed_data[stage_name] = {
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        _safe_json_write(file_path, processed_data)
        logger.info(f"Saved processed data for document {document_id}, stage {stage_name}")
        
    except Exception as e:
        logger.error(f"Failed to save processed data for document {document_id}, stage {stage_name}: {e}")
        raise


def get_processed_data(document_id: str, stage_name: str) -> Any:
    """
    Retrieve processed data for a specific stage.
    
    Args:
        document_id (str): Unique document identifier
        stage_name (str): Name of the processing stage
        
    Returns:
        Any: Data for the specified stage
        
    Raises:
        FileNotFoundError: If processed data file doesn't exist
        KeyError: If stage data doesn't exist
        Exception: If read operation fails
    """
    try:
        file_path = _get_processed_data_file_path(document_id)
        processed_data = _safe_json_read(file_path)
        
        if stage_name not in processed_data:
            raise KeyError(f"Stage '{stage_name}' not found for document {document_id}")
        
        stage_data = processed_data[stage_name]["data"]
        logger.info(f"Retrieved processed data for document {document_id}, stage {stage_name}")
        return stage_data
        
    except (FileNotFoundError, KeyError):
        logger.error(f"Processed data not found for document {document_id}, stage {stage_name}")
        raise
    except Exception as e:
        logger.error(f"Failed to get processed data for document {document_id}, stage {stage_name}: {e}")
        raise


def get_all_processed_data(document_id: str) -> Dict:
    """
    Retrieve all processed data for a document.
    
    Args:
        document_id (str): Unique document identifier
        
    Returns:
        Dict: All processed data for the document
        
    Raises:
        FileNotFoundError: If processed data file doesn't exist
        Exception: If read operation fails
    """
    try:
        file_path = _get_processed_data_file_path(document_id)
        processed_data = _safe_json_read(file_path)
        logger.info(f"Retrieved all processed data for document {document_id}")
        return processed_data
        
    except FileNotFoundError:
        logger.error(f"Processed data not found for document {document_id}")
        raise
    except Exception as e:
        logger.error(f"Failed to get all processed data for document {document_id}: {e}")
        raise


def list_documents() -> List[str]:
    """
    List all document IDs that have metadata stored.
    
    Returns:
        List[str]: List of document IDs
    """
    try:
        document_ids = []
        for file_path in DATA_DIR.glob("*_metadata.json"):
            document_id = file_path.stem.replace("_metadata", "")
            document_ids.append(document_id)
        
        logger.info(f"Found {len(document_ids)} documents")
        return sorted(document_ids)
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return []


def delete_document_data(document_id: str) -> None:
    """
    Delete all data for a document (metadata and processed data).
    
    Args:
        document_id (str): Unique document identifier
        
    Raises:
        Exception: If deletion fails
    """
    try:
        metadata_file = _get_metadata_file_path(document_id)
        processed_file = _get_processed_data_file_path(document_id)
        
        files_deleted = 0
        
        if metadata_file.exists():
            metadata_file.unlink()
            files_deleted += 1
            logger.info(f"Deleted metadata file for document {document_id}")
        
        if processed_file.exists():
            processed_file.unlink()
            files_deleted += 1
            logger.info(f"Deleted processed data file for document {document_id}")
        
        if files_deleted == 0:
            logger.warning(f"No files found to delete for document {document_id}")
        else:
            logger.info(f"Deleted {files_deleted} files for document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete data for document {document_id}: {e}")
        raise


def get_document_stages(document_id: str) -> List[str]:
    """
    Get list of processing stages available for a document.
    
    Args:
        document_id (str): Unique document identifier
        
    Returns:
        List[str]: List of stage names
    """
    try:
        file_path = _get_processed_data_file_path(document_id)
        
        if not file_path.exists():
            return []
        
        processed_data = _safe_json_read(file_path)
        
        # Filter out metadata fields to get only stage names
        metadata_fields = {"document_id", "created_at", "updated_at"}
        stages = [key for key in processed_data.keys() if key not in metadata_fields]
        
        logger.info(f"Found {len(stages)} stages for document {document_id}")
        return sorted(stages)
        
    except Exception as e:
        logger.error(f"Failed to get stages for document {document_id}: {e}")
        return [] 