"""
OCR service using Mistral's vision models for document text extraction.
"""

import os
import base64
import json
import time
from pathlib import Path
from typing import Dict, Optional, List
import logging
import requests
from dotenv import load_dotenv
from PIL import Image
import fitz  # PyMuPDF for PDF to image conversion

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Configuration from environment variables
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_BASE_URL = os.getenv("MISTRAL_API_BASE_URL", "https://api.mistral.ai/v1")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "pixtral-12b-2409")
MISTRAL_TIMEOUT = int(os.getenv("MISTRAL_TIMEOUT", "60"))
MISTRAL_MAX_RETRIES = int(os.getenv("MISTRAL_MAX_RETRIES", "3"))


class OCRError(Exception):
    """Custom exception for OCR-related errors."""
    pass


class MistralOCRService:
    """Service class for Mistral OCR operations."""
    
    def __init__(self):
        """Initialize the Mistral OCR service."""
        if not MISTRAL_API_KEY:
            raise OCRError("MISTRAL_API_KEY environment variable is required")
        
        self.api_key = MISTRAL_API_KEY
        self.base_url = MISTRAL_API_BASE_URL
        self.model = MISTRAL_MODEL
        self.timeout = MISTRAL_TIMEOUT
        self.max_retries = MISTRAL_MAX_RETRIES
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def _pdf_to_images(self, pdf_path: str, max_pages: int = 10) -> List[str]:
        """
        Convert PDF pages to base64 encoded images.
        
        Args:
            pdf_path (str): Path to the PDF file
            max_pages (int): Maximum number of pages to process
            
        Returns:
            List[str]: List of base64 encoded images
        """
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            pages_to_process = min(len(doc), max_pages)
            logger.info(f"Converting {pages_to_process} pages from PDF to images")
            
            for page_num in range(pages_to_process):
                page = doc.load_page(page_num)
                
                # Render page to image (300 DPI for good OCR quality)
                mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                images.append(img_base64)
            
            doc.close()
            return images
            
        except Exception as e:
            raise OCRError(f"Failed to convert PDF to images: {str(e)}")
    
    def _image_to_base64(self, image_path: str) -> str:
        """
        Convert image file to base64 string.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Base64 encoded image
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise OCRError(f"Failed to encode image: {str(e)}")
    
    def _call_mistral_vision_api(self, image_base64: str, prompt: str = None) -> Dict:
        """
        Call Mistral's vision API for OCR.
        
        Args:
            image_base64 (str): Base64 encoded image
            prompt (str): Optional custom prompt for OCR
            
        Returns:
            Dict: API response
        """
        if not prompt:
            prompt = """Extract all text from this image. Please provide the text in a structured format that preserves the document layout and hierarchy. Return the result as JSON with the following structure:
{
  "extracted_text": "Full text content",
  "confidence": "Confidence score 0-1",
  "pages": [
    {
      "page_number": 1,
      "text": "Text content of the page",
      "sections": [
        {
          "type": "header|paragraph|table|list",
          "content": "Section content",
          "position": {"x": 0, "y": 0, "width": 100, "height": 20}
        }
      ]
    }
  ],
  "metadata": {
    "language": "detected language",
    "document_type": "detected document type",
    "processing_time": "time taken"
  }
}"""
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1,  # Low temperature for consistent OCR results
            "response_format": {"type": "json_object"}
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Calling Mistral Vision API (attempt {attempt + 1})")
                
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Successfully received OCR response from Mistral")
                    return result
                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API call timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise OCRError("API call timed out after all retries")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API call failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise OCRError(f"API call failed after all retries: {str(e)}")
                time.sleep(2 ** attempt)
        
        raise OCRError("Failed to get successful API response")
    
    def _extract_text_from_response(self, api_response: Dict) -> Dict:
        """
        Extract and structure text from Mistral API response.
        
        Args:
            api_response (Dict): Raw API response
            
        Returns:
            Dict: Structured OCR results
        """
        try:
            # Extract the content from Mistral's response format
            content = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Try to parse as JSON first
            try:
                ocr_data = json.loads(content)
                if isinstance(ocr_data, dict):
                    return ocr_data
            except json.JSONDecodeError:
                logger.warning("Response is not valid JSON, treating as plain text")
            
            # Fallback: create structured response from plain text
            return {
                "extracted_text": content,
                "confidence": 0.8,  # Default confidence for plain text
                "pages": [
                    {
                        "page_number": 1,
                        "text": content,
                        "sections": [
                            {
                                "type": "paragraph",
                                "content": content,
                                "position": {"x": 0, "y": 0, "width": 100, "height": 100}
                            }
                        ]
                    }
                ],
                "metadata": {
                    "language": "unknown",
                    "document_type": "unknown",
                    "processing_time": "unknown"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract text from API response: {str(e)}")
            raise OCRError(f"Failed to process API response: {str(e)}")


def perform_mistral_ocr(file_path: str) -> Dict:
    """
    Perform OCR on a PDF or image file using Mistral's vision models.
    
    Args:
        file_path (str): Path to the PDF or image file
        
    Returns:
        Dict: Structured OCR results containing extracted text and metadata
        
    Raises:
        OCRError: If OCR processing fails
        FileNotFoundError: If the input file doesn't exist
    """
    start_time = time.time()
    
    # Validate input file
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    try:
        # Initialize OCR service
        ocr_service = MistralOCRService()
        logger.info(f"Starting OCR processing for: {file_path}")
        
        # Handle different file types
        if file_extension == '.pdf':
            # Convert PDF to images
            images = ocr_service._pdf_to_images(str(file_path))
            
            if not images:
                raise OCRError("No images could be extracted from PDF")
            
            # Process each page
            all_pages_data = []
            full_text = ""
            
            for i, image_base64 in enumerate(images):
                logger.info(f"Processing page {i + 1} of {len(images)}")
                
                # Call Mistral API for this page
                api_response = ocr_service._call_mistral_vision_api(image_base64)
                page_data = ocr_service._extract_text_from_response(api_response)
                
                # Update page numbers
                if "pages" in page_data:
                    for page in page_data["pages"]:
                        page["page_number"] = i + 1
                        all_pages_data.extend([page])
                
                # Accumulate text
                if "extracted_text" in page_data:
                    full_text += f"\n--- Page {i + 1} ---\n{page_data['extracted_text']}\n"
            
            # Combine results
            ocr_result = {
                "extracted_text": full_text.strip(),
                "confidence": sum(page.get("confidence", 0.8) for page in all_pages_data) / len(all_pages_data) if all_pages_data else 0.8,
                "pages": all_pages_data,
                "metadata": {
                    "total_pages": len(images),
                    "file_type": "pdf",
                    "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                    "processing_time_seconds": round(time.time() - start_time, 2),
                    "ocr_method": "mistral_vision_api"
                }
            }
            
        elif file_extension in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            # Handle image files
            image_base64 = ocr_service._image_to_base64(str(file_path))
            
            # Call Mistral API
            api_response = ocr_service._call_mistral_vision_api(image_base64)
            ocr_result = ocr_service._extract_text_from_response(api_response)
            
            # Add metadata
            ocr_result["metadata"] = {
                "total_pages": 1,
                "file_type": "image",
                "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "processing_time_seconds": round(time.time() - start_time, 2),
                "ocr_method": "mistral_vision_api"
            }
            
        else:
            raise OCRError(f"Unsupported file type: {file_extension}")
        
        logger.info(f"OCR processing completed in {ocr_result['metadata']['processing_time_seconds']} seconds")
        return ocr_result
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise


def check_ocr_availability() -> bool:
    """
    Check if OCR service is available and properly configured.
    
    Returns:
        bool: True if OCR service is available, False otherwise
    """
    try:
        if not MISTRAL_API_KEY:
            logger.warning("MISTRAL_API_KEY not found in environment variables")
            return False
        
        # Test API connectivity (optional - could make a simple API call)
        logger.info("OCR service configuration verified")
        return True
        
    except Exception as e:
        logger.error(f"OCR service not available: {str(e)}")
        return False


def get_ocr_service_info() -> Dict:
    """
    Get information about the OCR service configuration.
    
    Returns:
        Dict: Service information
    """
    return {
        "service_name": "Mistral Vision OCR",
        "model": MISTRAL_MODEL,
        "api_base_url": MISTRAL_API_BASE_URL,
        "timeout": MISTRAL_TIMEOUT,
        "max_retries": MISTRAL_MAX_RETRIES,
        "api_key_configured": bool(MISTRAL_API_KEY),
        "supported_formats": [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]
    } 