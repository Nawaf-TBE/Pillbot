"""
OCR service using Tesseract for document text extraction.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import logging
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF for PDF to image conversion
import cv2
import numpy as np

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
TESSERACT_CONFIG = '--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
TESSERACT_LANG = 'eng'  # Default language
IMAGE_DPI = 300  # DPI for PDF to image conversion
MAX_PAGES = 10  # Maximum pages to process


class OCRError(Exception):
    """Custom exception for OCR-related errors."""
    pass


class TesseractOCRService:
    """Service class for Tesseract OCR operations."""
    
    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = TESSERACT_LANG):
        """
        Initialize the Tesseract OCR service.
        
        Args:
            tesseract_cmd (str, optional): Path to tesseract executable
            lang (str): Language code for OCR (default: 'eng')
        """
        self.lang = lang
        self.config = TESSERACT_CONFIG
        
        # Set tesseract command path if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Test if tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR initialized successfully with language: {self.lang}")
        except Exception as e:
            raise OCRError(f"Tesseract not found or not properly installed: {str(e)}")
    
    def _pdf_to_images(self, pdf_path: str, max_pages: int = MAX_PAGES) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images.
        
        Args:
            pdf_path (str): Path to the PDF file
            max_pages (int): Maximum number of pages to process
            
        Returns:
            List[Image.Image]: List of PIL Images
        """
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            pages_to_process = min(len(doc), max_pages)
            logger.info(f"Converting {pages_to_process} pages from PDF to images")
            
            for page_num in range(pages_to_process):
                page = doc.load_page(page_num)
                
                # Render page to image with high DPI for better OCR
                mat = fitz.Matrix(IMAGE_DPI/72, IMAGE_DPI/72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                from io import BytesIO
                img = Image.open(BytesIO(img_data))
                images.append(img)
            
            doc.close()
            return images
            
        except Exception as e:
            raise OCRError(f"Failed to convert PDF to images: {str(e)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.
        
        Args:
            image (Image.Image): Input image
            
        Returns:
            Image.Image: Preprocessed image
        """
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert PIL to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply adaptive threshold to get better contrast
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(thresh)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed_image)
            processed_image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(processed_image)
            processed_image = enhancer.enhance(2.0)
            
            return processed_image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {str(e)}")
            return image
    
    def _extract_text_with_confidence(self, image: Image.Image) -> Dict:
        """
        Extract text from image with confidence scores.
        
        Args:
            image (Image.Image): Input image
            
        Returns:
            Dict: Extracted text with confidence and metadata
        """
        try:
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                image, 
                lang=self.lang, 
                config=self.config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text with confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(ocr_data['conf']):
                if int(conf) > 0:  # Only include confident text
                    text = ocr_data['text'][i].strip()
                    if text:
                        text_parts.append(text)
                        confidences.append(int(conf))
            
            # Calculate overall confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Join text parts
            full_text = ' '.join(text_parts)
            
            # Organize by lines/blocks for better structure
            structured_text = self._organize_text_structure(ocr_data)
            
            return {
                'text': full_text,
                'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
                'word_count': len(text_parts),
                'structured_text': structured_text,
                'raw_ocr_data': ocr_data
            }
            
        except Exception as e:
            raise OCRError(f"Text extraction failed: {str(e)}")
    
    def _organize_text_structure(self, ocr_data: Dict) -> List[Dict]:
        """
        Organize OCR data into structured format by lines and blocks.
        
        Args:
            ocr_data (Dict): Raw OCR data from pytesseract
            
        Returns:
            List[Dict]: Structured text data
        """
        structured = []
        current_line = []
        current_line_num = -1
        
        for i in range(len(ocr_data['text'])):
            if int(ocr_data['conf'][i]) > 30:  # Confidence threshold
                text = ocr_data['text'][i].strip()
                if text:
                    line_num = ocr_data['line_num'][i]
                    
                    if line_num != current_line_num:
                        # Save previous line
                        if current_line:
                            structured.append({
                                'type': 'line',
                                'text': ' '.join(current_line),
                                'line_number': current_line_num
                            })
                        
                        # Start new line
                        current_line = [text]
                        current_line_num = line_num
                    else:
                        current_line.append(text)
        
        # Add last line
        if current_line:
            structured.append({
                'type': 'line',
                'text': ' '.join(current_line),
                'line_number': current_line_num
            })
        
        return structured
    
    def perform_ocr_on_image(self, image_path: str) -> Dict:
        """
        Perform OCR on a single image file.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Dict: OCR results with text and metadata
        """
        try:
            logger.info(f"Performing OCR on image: {image_path}")
            
            # Load image
            image = Image.open(image_path)
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Extract text
            result = self._extract_text_with_confidence(processed_image)
            
            return {
                'success': True,
                'file_path': image_path,
                'extracted_text': result['text'],
                'confidence': result['confidence'],
                'word_count': result['word_count'],
                'structured_text': result['structured_text'],
                'processing_time': time.time(),
                'ocr_engine': 'tesseract',
                'language': self.lang
            }
            
        except Exception as e:
            logger.error(f"OCR failed for image {image_path}: {str(e)}")
            return {
                'success': False,
                'file_path': image_path,
                'error': str(e),
                'extracted_text': '',
                'confidence': 0.0
            }
    
    def perform_ocr_on_pdf(self, pdf_path: str, max_pages: int = MAX_PAGES) -> Dict:
        """
        Perform OCR on a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            max_pages (int): Maximum number of pages to process
            
        Returns:
            Dict: OCR results with text and metadata
        """
        try:
            start_time = time.time()
            logger.info(f"Performing OCR on PDF: {pdf_path}")
            
            # Convert PDF to images
            images = self._pdf_to_images(pdf_path, max_pages)
            
            # Process each page
            pages_data = []
            all_text = []
            total_confidence = 0
            total_words = 0
            
            for page_num, image in enumerate(images, 1):
                logger.info(f"Processing page {page_num}/{len(images)}")
                
                # Preprocess image
                processed_image = self._preprocess_image(image)
                
                # Extract text
                result = self._extract_text_with_confidence(processed_image)
                
                page_data = {
                    'page_number': page_num,
                    'text': result['text'],
                    'confidence': result['confidence'],
                    'word_count': result['word_count'],
                    'structured_text': result['structured_text']
                }
                
                pages_data.append(page_data)
                all_text.append(result['text'])
                total_confidence += result['confidence']
                total_words += result['word_count']
            
            # Calculate averages
            avg_confidence = total_confidence / len(images) if images else 0
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'file_path': pdf_path,
                'extracted_text': '\n\n'.join(all_text),
                'confidence': avg_confidence,
                'total_pages': len(images),
                'total_words': total_words,
                'pages': pages_data,
                'processing_time': processing_time,
                'ocr_engine': 'tesseract',
                'language': self.lang,
                'metadata': {
                    'document_type': 'pdf',
                    'pages_processed': len(images),
                    'average_confidence': avg_confidence
                }
            }
            
        except Exception as e:
            logger.error(f"OCR failed for PDF {pdf_path}: {str(e)}")
            return {
                'success': False,
                'file_path': pdf_path,
                'error': str(e),
                'extracted_text': '',
                'confidence': 0.0,
                'total_pages': 0
            }


# Global service instance
_ocr_service = None


def get_ocr_service() -> TesseractOCRService:
    """Get or create the OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = TesseractOCRService()
    return _ocr_service


def perform_tesseract_ocr(file_path: str) -> Dict:
    """
    Perform OCR on a file using Tesseract.
    
    Args:
        file_path (str): Path to the file (PDF or image)
        
    Returns:
        Dict: OCR results with extracted text and metadata
    """
    try:
        if not os.path.exists(file_path):
            raise OCRError(f"File not found: {file_path}")
        
        service = get_ocr_service()
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return service.perform_ocr_on_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return service.perform_ocr_on_image(file_path)
        else:
            raise OCRError(f"Unsupported file format: {file_ext}")
            
    except Exception as e:
        logger.error(f"OCR operation failed: {str(e)}")
        return {
            'success': False,
            'file_path': file_path,
            'error': str(e),
            'extracted_text': '',
            'confidence': 0.0
        }


def check_ocr_availability() -> bool:
    """
    Check if Tesseract OCR is available and working.
    
    Returns:
        bool: True if OCR is available, False otherwise
    """
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        logger.error(f"Tesseract not available: {str(e)}")
        return False


def get_ocr_service_info() -> Dict:
    """
    Get information about the OCR service.
    
    Returns:
        Dict: Service information
    """
    try:
        version = pytesseract.get_tesseract_version()
        languages = pytesseract.get_languages()
        
        return {
            'service': 'tesseract',
            'version': str(version),
            'available_languages': languages,
            'default_language': TESSERACT_LANG,
            'config': TESSERACT_CONFIG,
            'status': 'available' if check_ocr_availability() else 'unavailable'
        }
    except Exception as e:
        return {
            'service': 'tesseract',
            'status': 'unavailable',
            'error': str(e)
        }


# Backward compatibility - alias the main function
perform_mistral_ocr = perform_tesseract_ocr  # Keep the same function name for compatibility 