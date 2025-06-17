"""
PDF utility functions for processing PDF documents.
"""

import os
from typing import Optional
from pypdf import PdfReader


def check_pdf_is_native(file_path: str) -> bool:
    """
    Check if a PDF has selectable text content (native PDF vs scanned image).
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        bool: True if PDF has selectable text, False if it's likely a scanned image
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If there's an error reading the PDF
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        reader = PdfReader(file_path)
        
        # Check first few pages for text content
        pages_to_check = min(3, len(reader.pages))
        total_text_length = 0
        
        for i in range(pages_to_check):
            page = reader.pages[i]
            text = page.extract_text().strip()
            total_text_length += len(text)
        
        # If we found meaningful text content, it's likely a native PDF
        # Using a threshold of 50 characters across checked pages
        return total_text_length > 50
        
    except Exception as e:
        raise Exception(f"Error reading PDF {file_path}: {str(e)}")


def get_pdf_page_count(file_path: str) -> int:
    """
    Get the total number of pages in a PDF document.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        int: Number of pages in the PDF
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If there's an error reading the PDF
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        reader = PdfReader(file_path)
        return len(reader.pages)
        
    except Exception as e:
        raise Exception(f"Error reading PDF {file_path}: {str(e)}")


def get_pdf_info(file_path: str) -> dict:
    """
    Get comprehensive information about a PDF file.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        dict: Dictionary containing PDF information
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        reader = PdfReader(file_path)
        
        info = {
            'page_count': len(reader.pages),
            'is_native': check_pdf_is_native(file_path),
            'file_size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
            'metadata': reader.metadata if reader.metadata else {}
        }
        
        return info
        
    except Exception as e:
        raise Exception(f"Error analyzing PDF {file_path}: {str(e)}") 