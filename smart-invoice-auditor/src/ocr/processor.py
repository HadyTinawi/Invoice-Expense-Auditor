"""
OCR Processing Module

This module handles the extraction of text and structured data from invoice PDFs
using OCR technology (Tesseract or AWS Textract).
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdf2image
import boto3
import tempfile
import json
import numpy as np
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRError(Exception):
    """Base exception for OCR processing errors"""
    pass

class PDFValidationError(OCRError):
    """Exception raised when a PDF is invalid or corrupted"""
    pass

class OCRExtractionError(OCRError):
    """Exception raised when OCR extraction fails"""
    pass

class OCRProcessor:
    """Base class for OCR processing"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the OCR processor with configuration"""
        self.config = config or {}
        self.logger = logger
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PDF file and extract text and structured data"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Validate that the PDF file exists and is accessible
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if the PDF is valid
            
        Raises:
            PDFValidationError: If the PDF is invalid or inaccessible
        """
        path = Path(pdf_path)
        
        # Check if file exists
        if not path.exists():
            raise PDFValidationError(f"PDF file does not exist: {pdf_path}")
        
        # Check if file is a PDF (by extension)
        if path.suffix.lower() != '.pdf':
            raise PDFValidationError(f"File is not a PDF: {pdf_path}")
        
        # Check if file is readable
        if not os.access(pdf_path, os.R_OK):
            raise PDFValidationError(f"PDF file is not readable: {pdf_path}")
        
        # Check if file is not empty
        if path.stat().st_size == 0:
            raise PDFValidationError(f"PDF file is empty: {pdf_path}")
        
        return True
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image to enhance OCR quality.
        
        This function applies various image processing techniques to make the image
        more readable for OCR. It includes adaptive thresholding and noise reduction.
        
        Args:
            image: The input image as a numpy array
            
        Returns:
            The processed image ready for OCR
        """
        self.logger.debug("Preprocessing image for OCR enhancement")
        
        # Convert to grayscale if image is in color
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Store original dimensions for later comparison
        original_height, original_width = gray.shape
        
        # Check if we need to scale up small images
        scale_factor = 1
        min_width = 1500
        if original_width < min_width:
            scale_factor = min_width / original_width
            self.logger.debug(f"Scaling up image by factor of {scale_factor:.2f} for better OCR quality")
            gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        
        # Create a copy of the original for comparison
        original_processed = gray.copy()
        
        # Apply multiple preprocessing techniques and choose the best result
        preprocessed_images = []
        
        # 1. Basic adaptive thresholding
        threshold = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        preprocessed_images.append(("adaptive_threshold", threshold))
        
        # 2. Bilateral filtering for noise reduction while preserving edges
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        # Apply adaptive threshold after bilateral filtering
        bilateral_threshold = cv2.adaptiveThreshold(
            bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        preprocessed_images.append(("bilateral_filtering", bilateral_threshold))
        
        # 3. Otsu's thresholding for global binary processing
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images.append(("otsu_threshold", otsu))
        
        # 4. Dilated image to connect broken text
        kernel = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(gray, kernel, iterations=1)
        # Apply adaptive threshold after dilation
        dilated_threshold = cv2.adaptiveThreshold(
            dilated, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        preprocessed_images.append(("dilated_threshold", dilated_threshold))
        
        # 5. Eroded image for thin text
        eroded = cv2.erode(gray, kernel, iterations=1)
        # Apply adaptive threshold after erosion
        eroded_threshold = cv2.adaptiveThreshold(
            eroded, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        preprocessed_images.append(("eroded_threshold", eroded_threshold))
        
        # 6. Contrast enhancement
        # Create a CLAHE object (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_applied = clahe.apply(gray)
        # Apply adaptive threshold after contrast enhancement
        clahe_threshold = cv2.adaptiveThreshold(
            clahe_applied, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        preprocessed_images.append(("contrast_enhanced", clahe_threshold))
        
        # OCR each preprocessed image variant to find the one that yields the best results
        best_confidence = 0
        best_image = original_processed  # Default to original if no improvement
        
        for name, processed_image in preprocessed_images:
            try:
                # Save the processed image temporarily
                temp_file = self._save_temp_image(processed_image)
                
                # Run OCR on the preprocessed image using Tesseract
                text = pytesseract.image_to_string(
                    temp_file,
                    config=self.config,
                    lang='eng'
                )
                
                # Calculate a simple confidence score based on text length and valid character proportion
                char_count = len(text)
                if char_count > 0:
                    # Calculate the ratio of alphanumeric and punctuation characters
                    valid_chars = sum(1 for c in text if c.isalnum() or c in ".,;:!?-()[]{}'\"/\\")
                    confidence = valid_chars / char_count * 100
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_image = processed_image
                        self.logger.debug(f"Better preprocessing found: {name} with confidence {confidence:.2f}%")
                
                # Clean up the temporary file
                os.remove(temp_file)
                
            except Exception as e:
                self.logger.warning(f"Error during preprocessing evaluation for {name}: {str(e)}")
        
        self.logger.info(f"Best preprocessing method achieved {best_confidence:.2f}% confidence")
        return best_image

    def _save_temp_image(self, image: np.ndarray) -> str:
        """Save a temporary image and return the file path."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        cv2.imwrite(temp_file, image)
        return temp_file

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process an image file using OCR to extract text and structured data.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            A dictionary containing the extracted data
            
        Raises:
            OCRError: If OCR processing fails
        """
        try:
            self.logger.info(f"Processing image: {image_path}")
            
            # Read the image using OpenCV
            image = cv2.imread(image_path)
            if image is None:
                raise OCRError(f"Failed to load image: {image_path}")
            
            # Preprocess the image to improve OCR quality
            preprocessed = self.preprocess_image(image)
            
            # Save the preprocessed image temporarily for tesseract
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            cv2.imwrite(temp_file, preprocessed)
            
            try:
                # Apply OCR to extract text
                ocr_results = []
                
                # Extract text using pytesseract
                ocr_text = pytesseract.image_to_string(
                    temp_file,
                    config=self.config,
                    lang='eng'
                )
                
                # Get detailed OCR data including bounding boxes and confidence
                ocr_data = pytesseract.image_to_data(
                    temp_file,
                    config=self.config,
                    lang='eng',
                    output_type=pytesseract.Output.DICT
                )
                
                # Calculate overall confidence score
                confidence_scores = [float(conf) for conf in ocr_data['conf'] if float(conf) > 0]
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
                
                self.logger.info(f"OCR extraction completed with confidence: {avg_confidence:.2f}%")
                
                # Add all words with their bounding boxes and confidence to results
                for i in range(len(ocr_data['text'])):
                    if ocr_data['text'][i].strip():
                        word_data = {
                            'text': ocr_data['text'][i],
                            'conf': float(ocr_data['conf'][i]),
                            'bbox': [
                                ocr_data['left'][i],
                                ocr_data['top'][i],
                                ocr_data['width'][i],
                                ocr_data['height'][i]
                            ]
                        }
                        ocr_results.append(word_data)
                
                # Extract structured data from OCR results
                extracted_data = self._extract_structured_data(ocr_results)
                
                # Add raw text and confidence
                extracted_data['raw_text'] = ocr_text
                extracted_data['confidence'] = avg_confidence
                
                # Add source file information
                extracted_data['source_file'] = image_path
                
                return extracted_data
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                
        except Exception as e:
            self.logger.error(f"OCR processing error: {str(e)}")
            raise OCRError(f"Failed to process image: {str(e)}")


class TesseractProcessor(OCRProcessor):
    """OCR processor using Tesseract"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the TesseractProcessor with configuration."""
        super().__init__(config)
        
        # Default Tesseract configuration
        self.config = '--oem 3 --psm 6'
        if config and 'tesseract_config' in config:
            self.config = config['tesseract_config']
            
        # Regular expression patterns for extracting structured data
        self.patterns = {
            # Invoice number patterns - expanded to catch more variants
            'invoice_id': r'(?i)(?:invoice|bill|receipt)(?:\s+(?:no|num|number|#|code|id))?(?:\s*[:.\s])?\s*([\w\d\-]+)',
            'invoice_alt': r'(?i)(?:inv|bill|order|transaction|document)(?:\s+(?:no|num|number|#|code|id))?(?:\s*[:.\s])?\s*([\w\d\-]+)',
            
            # Extended date patterns
            'date': r'(?i)(?:date|invoice\s+date|bill\s+date|issued|issued\s+on|dated)(?:\s*[:.\s])?\s*(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}|\d{1,2}[-/\.\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/\.\s]+\d{2,4})',
            'due_date': r'(?i)(?:due|payment\s+due|due\s+date|payment\s+date|pay\s+by)(?:\s*[:.\s])?\s*(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}|\d{1,2}[-/\.\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/\.\s]+\d{2,4})',
            
            # Vendor information patterns - enhanced to catch more company name formats
            'vendor': r'(?i)(?:vendor|supplier|seller|from|by|company|business|issued\s+by|merchant|store|billed\s+from|payee|provider)(?:\s*[:.\s])?\s*([A-Z&\'\s]{3,}(?:\s+LLC|\s+Inc|\s+Corp|\s+Ltd)?)',
            'vendor_alt': r'(?i)(?:\s+LLC|\s+Inc\.?|\s+Corp\.?|\s+Ltd\.?|\s+Corporation|\s+Company|\s+GmbH)$',
            
            # Total amount patterns - expanded with currency symbols and more formats
            'total': r'(?i)(?:total|amount|grand\s+total|balance|sum|payment|charge)(?:\s*[:.\s])?\s*(?:\$|€|£|¥)?(?:\s*)?([\d,]+\.\d{2}|\d+)',
            'total_alt': r'(?i)(?:total(?:\s+due)?|amount(?:\s+due)?|balance(?:\s+due)?|to\s+pay)(?:\s*[:.\s])?\s*(?:\$|€|£|¥)?(?:\s*)?([\d,]+\.\d{2}|\d+)',
            
            # Subtotal and tax patterns - improved to catch more variants
            'subtotal': r'(?i)(?:subtotal|sub\s*total|net|net\s+amount|amount|goods|merchandise|net\s+total)(?:\s*[:.\s])?\s*(?:\$|€|£|¥)?(?:\s*)?([\d,]+\.\d{2}|\d+)',
            'tax': r'(?i)(?:tax|vat|gst|hst|sales\s+tax|tax\s+amount)(?:\s*[:.\s])?\s*(?:\$|€|£|¥)?(?:\s*)?([\d,]+\.\d{2}|\d+)',
            
            # Payment info patterns
            'payment_terms': r'(?i)(?:terms|payment\s+terms|due\s+in)(?:\s*[:.\s])?\s*(.{3,30})',
            'payment_method': r'(?i)(?:(?:payment|paid|pay)\s+(?:method|via|using|by)|method\s+of\s+payment)(?:\s*[:.\s])?\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)',
            
            # Line item patterns with improved structure detection
            'line_item_header': r'(?i)(description|item|service|product|qty|quantity|price|amount|total)',
            'line_item_row': r'([A-Za-z0-9\s\-&]{3,})\s+([\d.]+)\s+(?:x\s+)?(\$?[\d.,]+)\s+(?:=\s+)?(\$?[\d.,]+)',
        }
        
        # DPI for PDF to image conversion
        self.dpi = self.config.get('dpi', 300)
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF file using Tesseract OCR
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict containing extracted information and raw text
            
        Raises:
            PDFValidationError: If the PDF is invalid
            OCRExtractionError: If OCR extraction fails
        """
        try:
            # Validate the PDF file
            self.validate_pdf(pdf_path)
            
            # Convert PDF to images
            self.logger.info(f"Converting PDF to images: {pdf_path}")
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='jpeg',
                grayscale=False,
                thread_count=2,
                use_pdftocairo=True
            )
            
            if not images:
                raise OCRExtractionError(f"Failed to convert PDF to images: {pdf_path}")
            
            self.logger.info(f"PDF converted to {len(images)} images")
            
            # Extract text from each page
            results = []
            for i, img in enumerate(images):
                try:
                    # Preprocess the image for better OCR results
                    processed_img = self.preprocess_image(img)
                    
                    # Perform OCR on the processed image
                    self.logger.info(f"Processing page {i+1}/{len(images)}")
                    text = pytesseract.image_to_string(processed_img, **self.tesseract_config)
                    
                    # Store the page number and extracted text
                    results.append({
                        "page": i+1,
                        "text": text,
                        "confidence": self._get_confidence(processed_img)
                    })
                except Exception as e:
                    self.logger.error(f"Error processing page {i+1}: {str(e)}")
                    results.append({
                        "page": i+1,
                        "text": f"ERROR: {str(e)}",
                        "confidence": 0
                    })
            
            # Combine all the text for entities extraction
            all_text = "\n".join([r["text"] for r in results])
            
            # Extract structured data from the text
            extracted_data = {
                "invoice_id": self._extract_invoice_id(results),
                "date": self._extract_date(results),
                "total": self._extract_total(results),
                "vendor": self._extract_vendor(results),
                "line_items": self._extract_line_items(results),
                "subtotal": self._extract_subtotal(results),
                "tax": self._extract_tax(results),
                "raw_text": all_text,
                "pages": len(results),
                "confidence": sum(r.get("confidence", 0) for r in results) / len(results) if results else 0
            }
            
            self.logger.info(f"Extraction completed with confidence: {extracted_data['confidence']:.2f}%")
            return extracted_data
            
        except PDFValidationError as e:
            self.logger.error(f"PDF validation error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"OCR extraction error: {str(e)}")
            raise OCRExtractionError(f"Failed to process PDF: {str(e)}")
    
    def _get_confidence(self, image: Image.Image) -> float:
        """Get the OCR confidence level (0-100)"""
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, **self.tesseract_config)
            conf_values = [float(conf) for conf in data['conf'] if conf != '-1']
            return sum(conf_values) / len(conf_values) if conf_values else 0
        except Exception:
            return 0
    
    def _extract_invoice_id(self, results: List[Dict[str, Any]]) -> str:
        """Extract invoice ID from OCR results"""
        all_text = "\n".join([r["text"] for r in results])
        
        # Try regex pattern first
        pattern = self.patterns['invoice_id']
        matches = re.findall(pattern, all_text)
        
        if matches:
            return matches[0].strip()
        
        # Fallback: Look for anything that might be an invoice ID
        lines = all_text.split('\n')
        for line in lines:
            if 'invoice' in line.lower() and '#' in line:
                # Extract text after '#'
                return line.split('#', 1)[1].strip()
        
        return ""
    
    def _extract_date(self, results: List[Dict[str, Any]]) -> str:
        """Extract date from OCR results with enhanced detection"""
        all_text = "\n".join([r["text"] for r in results])
        
        self.logger.debug(f"Extracting date from text: {all_text[:200]}...")
        
        # Look for lines containing date-related keywords
        date_keywords = [
            'date', 'issued', 'invoice date', 'bill date', 'dated', 
            'issued on', 'invoice issued', 'invoice: ', 'date of issue',
            'issue date', 'created on', 'issued date', 'billing date'
        ]
        
        # Create a more targeted search for date lines
        date_lines = []
        for i, line in enumerate(all_text.split('\n')):
            lower_line = line.lower()
            
            # Check if line contains date keywords
            if any(keyword in lower_line for keyword in date_keywords):
                date_lines.append((i, line))
                self.logger.debug(f"Found potential date line: {line}")
                
                # Also include the next line, as dates are often on the line after the label
                if i + 1 < len(all_text.split('\n')):
                    date_lines.append((i+1, all_text.split('\n')[i+1]))
        
        # Try expanded set of date patterns on the targeted date lines first
        date_patterns = [
            # Common date formats with separators (ordered by likelihood)
            r'\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b',  # 01/31/2022, 31-01-2022, etc.
            r'\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})\b',    # 2022/01/31, 2022-01-31, etc.
            
            # Month/Year formats
            r'\b(\d{1,2}[-/\.]\d{4})\b',  # 01/2022, 1-2022
            r'\b(\d{4}[-/\.]\d{1,2})\b',  # 2022/01, 2022-01
            
            # Text date formats with various separators
            r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
            r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?\b',
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}\b',
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b',
            
            # Simple date formats without separators (harder to identify correctly)
            r'\b(\d{8})\b',     # 20220131, 01312022
            r'\b(\d{6})\b',     # 012022, 202201 (month/year formats)
            
            # Looser patterns with context
            r'(?:date|invoice|issued|created)[\s:]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'(?:date|invoice|issued|created)[\s:]*(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})'
        ]
        
        # First check date-specific lines
        for _, line in date_lines:
            # Try with keyword context - most reliable
            for pattern in date_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    date_str = matches[0]
                    # If it's a tuple (from a group with multiple captures), take the first element
                    if isinstance(date_str, tuple):
                        date_str = date_str[0]
                    date_str = date_str.strip()
                    self.logger.info(f"Extracted date from keyword line: {date_str}")
                    return date_str
        
        # If that fails, try the original approach with all text
        # Try regex pattern first using labeled date fields
        pattern = self.patterns['date']
        matches = re.findall(pattern, all_text)
        
        if matches:
            date_str = matches[0].strip()
            self.logger.info(f"Extracted date using primary pattern: {date_str}")
            return date_str
        
        # If we still haven't found a date, check each line for date-like patterns
        for line in all_text.split('\n'):
            for pattern in date_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    date_str = matches[0]
                    # If it's a tuple (from a group with multiple captures), take the first element
                    if isinstance(date_str, tuple):
                        date_str = date_str[0]
                    date_str = date_str.strip()
                    self.logger.info(f"Extracted date from full text: {date_str}")
                    return date_str
        
        # If nothing works, look for any digit patterns that might be dates
        # Try to find anything that looks remotely like a date
        for line in all_text.split('\n'):
            # Look for patterns like "date: 01.02.2023" or variations
            if re.search(r'(?i)date.*?(\d[\d\s\./-]+)', line):
                date_part = re.search(r'(?i)date.*?(\d[\d\s\./-]+)', line).group(1)
                self.logger.info(f"Found potential date using loose pattern: {date_part.strip()}")
                return date_part.strip()
        
        self.logger.warning("No date could be extracted from the invoice")
        return ""
    
    def _extract_total(self, results: List[Dict[str, Any]]) -> float:
        """Extract total amount from OCR results"""
        all_text = "\n".join([r["text"] for r in results])
        
        # Try regex pattern first
        pattern = self.patterns['total']
        matches = re.findall(pattern, all_text)
        
        if matches:
            # Get the last match (usually the final total)
            amount_str = matches[-1].strip()
            try:
                # Remove any non-numeric characters except decimal point
                amount_str = re.sub(r'[^\d.]', '', amount_str)
                return float(amount_str)
            except ValueError:
                pass
        
        # Fallback: Look for any number after "total"
        total_line = None
        lines = all_text.split('\n')
        for line in lines:
            if 'total' in line.lower():
                total_line = line
                break
        
        if total_line:
            # Extract any numbers from the line
            numbers = re.findall(r'\d+\.\d+|\d+', total_line)
            if numbers:
                try:
                    return float(numbers[-1])
                except ValueError:
                    pass
        
        return 0.0
    
    def _extract_vendor(self, results: List[Dict[str, Any]]) -> str:
        """Extract vendor information from OCR results"""
        # Usually the vendor name is at the top of the invoice
        if not results:
            return ""
        
        # Check the first page for vendor information
        first_page_text = results[0]["text"]
        lines = first_page_text.split('\n')
        
        # Look for company name in the first few lines
        for i in range(min(5, len(lines))):
            line = lines[i].strip()
            if line and len(line) > 3 and not line.startswith(('Invoice', 'INVOICE', 'Bill', 'BILL')):
                return line
        
        # Fallback to regex pattern
        all_text = "\n".join([r["text"] for r in results])
        pattern = self.patterns['vendor']
        matches = re.findall(pattern, all_text)
        
        if matches:
            return matches[0].strip()
        
        return ""
    
    def _extract_subtotal(self, results: List[Dict[str, Any]]) -> float:
        """Extract subtotal amount from OCR results"""
        all_text = "\n".join([r["text"] for r in results])
        
        # Look for subtotal keyword
        subtotal_pattern = r'(?i)(?:subtotal|sub-total|sub total)(?:\s*)?[:.]?\s*[$£€]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)'
        matches = re.findall(subtotal_pattern, all_text)
        
        if matches:
            amount_str = matches[0].strip()
            try:
                # Remove any non-numeric characters except decimal point
                amount_str = re.sub(r'[^\d.]', '', amount_str)
                return float(amount_str)
            except ValueError:
                pass
        
        return 0.0
    
    def _extract_tax(self, results: List[Dict[str, Any]]) -> float:
        """Extract tax amount from OCR results"""
        all_text = "\n".join([r["text"] for r in results])
        
        # Look for tax keywords
        tax_pattern = r'(?i)(?:tax|vat|gst|hst|pst|sales tax)(?:\s*)?[:.]?\s*[$£€]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)'
        matches = re.findall(tax_pattern, all_text)
        
        if matches:
            amount_str = matches[0].strip()
            try:
                # Remove any non-numeric characters except decimal point
                amount_str = re.sub(r'[^\d.]', '', amount_str)
                return float(amount_str)
            except ValueError:
                pass
        
        return 0.0
    
    def _extract_line_items(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract line items from OCR results"""
        # This is a complex task that often requires custom extraction logic for different invoice formats
        # For the MVP, we'll implement a simple version that looks for patterns in the text
        
        all_text = "\n".join([r["text"] for r in results])
        line_items = []
        
        # Look for a table structure in the text
        # This is a simple approach that might not work for all invoice formats
        lines = all_text.split('\n')
        item_section = False
        current_item = {}
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if we're in the line items section
            if 'item' in line.lower() and ('description' in line.lower() or 'qty' in line.lower() or 'price' in line.lower()):
                item_section = True
                continue
            
            # Check if we've reached the end of line items (subtotal, tax, total, etc.)
            if item_section and ('subtotal' in line.lower() or 'total' in line.lower() or 'tax' in line.lower()):
                item_section = False
                continue
            
            # Process line items
            if item_section:
                # Try to extract item details
                # This is a simple approach that assumes items are on a single line
                # Format: Description Quantity Price Amount
                parts = line.split()
                if len(parts) >= 3:
                    # Try to identify price and quantity
                    price = None
                    quantity = None
                    # Look for numbers in the line
                    numbers = [part for part in parts if re.match(r'^\d+\.?\d*$', part)]
                    
                    if len(numbers) >= 2:
                        # Assume last number is the amount
                        try:
                            quantity = float(numbers[0])
                            price = float(numbers[-2])
                            description = ' '.join([p for p in parts if p not in numbers])
                            
                            line_items.append({
                                "description": description.strip(),
                                "quantity": quantity,
                                "price": price,
                                "amount": quantity * price
                            })
                        except (ValueError, IndexError):
                            pass
        
        # If we didn't find any line items using the table approach, try another method
        if not line_items:
            # Look for patterns like "2 x Widget at $10.00 each"
            item_pattern = r'(\d+)\s*(?:x|\*)\s*([A-Za-z][\w\s\-]+)\s*(?:at|@)\s*\$?\s*(\d+\.?\d*)'
            matches = re.findall(item_pattern, all_text)
            
            for match in matches:
                try:
                    quantity = float(match[0])
                    description = match[1].strip()
                    price = float(match[2])
                    
                    line_items.append({
                        "description": description,
                        "quantity": quantity,
                        "price": price,
                        "amount": quantity * price
                    })
                except (ValueError, IndexError):
                    pass
        
        return line_items


class TextractProcessor(OCRProcessor):
    """OCR processor using AWS Textract"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Textract processor"""
        super().__init__(config)
        
        # Set up AWS credentials from config or environment variables
        aws_access_key = self.config.get('aws_access_key') or os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = self.config.get('aws_secret_key') or os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = self.config.get('aws_region') or os.environ.get('AWS_REGION', 'us-east-1')
        
        # Create Textract client
        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        self.textract_client = session.client('textract')
        
        # Regular expressions for data extraction (same as TesseractProcessor)
        self.patterns = {
            'invoice_id': r'(?i)(?:invoice|inv|bill)(?:\s+)?(?:no|number|#|num)?(?:\s*)?[:.]?\s*([A-Z0-9][\w\-]*\d)',
            'date': r'(?i)(?:date|invoice date|bill date)(?:\s*)?[:.]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
            'total': r'(?i)(?:total|amount|sum|balance)(?:\s+)?(?:due|paid)?(?:\s*)?[:.]?\s*[$£€]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)',
            'vendor': r'(?i)(?:from|vendor|supplier|company|business)(?:\s*)?[:.]?\s*([A-Z][A-Za-z0-9\s&,\.]{2,50}(?:Inc|LLC|Ltd|Co|Corp|Corporation)?)'
        }
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF file using AWS Textract
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict containing extracted information and raw text
            
        Raises:
            PDFValidationError: If the PDF is invalid
            OCRExtractionError: If OCR extraction fails
        """
        try:
            # Validate the PDF file
            self.validate_pdf(pdf_path)
            
            # Read the PDF file as bytes
            with open(pdf_path, 'rb') as file:
                pdf_bytes = file.read()
            
            # Process the document with Textract
            self.logger.info(f"Processing document with AWS Textract: {pdf_path}")
            
            # For documents less than 5MB, we can use the synchronous API
            if len(pdf_bytes) < 5 * 1024 * 1024:  # 5MB
                response = self.textract_client.detect_document_text(Document={'Bytes': pdf_bytes})
                text_blocks = response['Blocks']
            else:
                # For larger documents, use the asynchronous API (not implemented in this version)
                raise OCRExtractionError("Document too large for synchronous processing. Asynchronous API not implemented yet.")
            
            # Extract text from Textract blocks
            full_text = ""
            for block in text_blocks:
                if block['BlockType'] == 'LINE':
                    full_text += block['Text'] + "\n"
            
            # Create a result structure similar to TesseractProcessor
            results = [{
                "page": 1,  # Textract doesn't separate pages in the synchronous API
                "text": full_text,
                "confidence": self._get_confidence(text_blocks)
            }]
            
            # Extract structured data from the text
            extracted_data = {
                "invoice_id": self._extract_invoice_id(results),
                "date": self._extract_date(results),
                "total": self._extract_total(results),
                "vendor": self._extract_vendor(results),
                "line_items": self._extract_line_items(results),
                "subtotal": self._extract_subtotal(results),
                "tax": self._extract_tax(results),
                "raw_text": full_text,
                "pages": 1,  # Textract doesn't separate pages in the synchronous API
                "confidence": self._get_confidence(text_blocks)
            }
            
            self.logger.info(f"Extraction completed with confidence: {extracted_data['confidence']:.2f}%")
            return extracted_data
            
        except PDFValidationError:
            raise
        except boto3.exceptions.Boto3Error as e:
            self.logger.error(f"AWS Textract error: {str(e)}")
            raise OCRExtractionError(f"Failed to process with AWS Textract: {str(e)}")
        except Exception as e:
            self.logger.error(f"OCR extraction error: {str(e)}")
            raise OCRExtractionError(f"Failed to process PDF: {str(e)}")
    
    def _get_confidence(self, text_blocks: List[Dict[str, Any]]) -> float:
        """Get the average confidence level (0-100) from Textract blocks"""
        confidence_values = []
        for block in text_blocks:
            if 'Confidence' in block:
                confidence_values.append(block['Confidence'])
        
        return sum(confidence_values) / len(confidence_values) if confidence_values else 0
    
    # Reuse the extraction methods from TesseractProcessor
    # In a production system, we would implement Textract-specific extraction methods
    # that leverage Textract's form and table extraction capabilities
    _extract_invoice_id = TesseractProcessor._extract_invoice_id
    _extract_date = TesseractProcessor._extract_date
    _extract_total = TesseractProcessor._extract_total
    _extract_vendor = TesseractProcessor._extract_vendor
    _extract_subtotal = TesseractProcessor._extract_subtotal
    _extract_tax = TesseractProcessor._extract_tax
    _extract_line_items = TesseractProcessor._extract_line_items


def create_processor(processor_type: str = "tesseract", config: Optional[Dict[str, Any]] = None) -> OCRProcessor:
    """Factory function to create an OCR processor"""
    if processor_type.lower() == "tesseract":
        return TesseractProcessor(config)
    elif processor_type.lower() == "textract":
        return TextractProcessor(config)
    else:
        raise ValueError(f"Unsupported processor type: {processor_type}")