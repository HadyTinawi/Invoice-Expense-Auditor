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
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process any file type (PDF or image) and extract text and structured data
        
        Args:
            file_path: Path to the file (PDF or image)
            
        Returns:
            Dict containing extracted text and structured data
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # If it's a PDF, use the PDF processing method
        if file_extension == '.pdf':
            return self.process_pdf(file_path)
        # If it's an image file, use the image processing method
        elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
            return self.process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Supported types are: .pdf, .png, .jpg, .jpeg, .tiff, .bmp, .gif")
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PDF file and extract text and structured data"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process an image file and extract text and structured data"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def validate_file(self, file_path: str) -> bool:
        """
        Validate that the file exists and is accessible
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is valid
            
        Raises:
            OCRError: If the file is invalid or inaccessible
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            raise OCRError(f"File does not exist: {file_path}")
        
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            raise OCRError(f"File is not readable: {file_path}")
        
        # Check if file is not empty
        if path.stat().st_size == 0:
            raise OCRError(f"File is empty: {file_path}")
        
        return True
    
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
    
    def validate_image(self, image_path: str) -> bool:
        """
        Validate that the image file exists and is accessible
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if the image is valid
            
        Raises:
            OCRError: If the image is invalid or inaccessible
        """
        path = Path(image_path)
        
        # Check if file exists
        if not path.exists():
            raise OCRError(f"Image file does not exist: {image_path}")
        
        # Check if file is an image (by extension)
        valid_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
        if path.suffix.lower() not in valid_extensions:
            raise OCRError(f"File is not a supported image type: {image_path}. Supported types: {', '.join(valid_extensions)}")
        
        # Check if file is readable
        if not os.access(image_path, os.R_OK):
            raise OCRError(f"Image file is not readable: {image_path}")
        
        # Check if file is not empty
        if path.stat().st_size == 0:
            raise OCRError(f"Image file is empty: {image_path}")
        
        # Try to open with PIL to validate it's a proper image
        try:
            with Image.open(image_path) as img:
                # Just accessing a property to ensure the image is valid
                _ = img.size
            return True
        except Exception as e:
            raise OCRError(f"Invalid image file: {image_path}. Error: {str(e)}")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess an image to improve OCR quality
        
        Args:
            image: PIL Image to preprocess
            
        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply noise reduction
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Sharpen the image
        image = image.filter(ImageFilter.SHARPEN)
        
        return image


class TesseractProcessor(OCRProcessor):
    """OCR processor using Tesseract"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Tesseract processor with configuration"""
        super().__init__(config)
        
        # Configuration for Tesseract
        self.tesseract_config = {
            'lang': self.config.get('language', 'eng'),
            'config': '--psm 6'  # Page segmentation mode: Assume a single uniform block of text
        }
        
        # DPI for PDF to image conversion
        self.dpi = self.config.get('dpi', 300)
        
        # Regular expressions for data extraction
        self.patterns = {
            'invoice_id': r'(?i)(?:invoice|inv|bill)(?:\s+)?(?:no|number|#|num)?(?:\s*)?[:.]?\s*([A-Z0-9][\w\-]*\d)',
            'date': r'(?i)(?:date|invoice date|bill date)(?:\s*)?[:.]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
            'total': r'(?i)(?:total|amount|sum|balance)(?:\s+)?(?:due|paid)?(?:\s*)?[:.]?\s*[$£€]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)',
            'vendor': r'(?i)(?:from|vendor|supplier|company|business)(?:\s*)?[:.]?\s*([A-Z][A-Za-z0-9\s&,\.]{2,50}(?:Inc|LLC|Ltd|Co|Corp|Corporation)?)'
        }
    
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
        """Extract date from OCR results"""
        all_text = "\n".join([r["text"] for r in results])
        
        self.logger.debug(f"Extracting date from text: {all_text[:200]}...")
        
        # Look for lines containing date-related keywords
        date_keywords = ['date', 'issued', 'invoice date', 'bill date', 'dated']
        date_lines = []
        for line in all_text.split('\n'):
            if any(keyword in line.lower() for keyword in date_keywords):
                date_lines.append(line)
                self.logger.debug(f"Found potential date line: {line}")
        
        # Try regex pattern first using labeled date fields
        pattern = self.patterns['date']
        matches = re.findall(pattern, all_text)
        
        if matches:
            date_str = matches[0].strip()
            self.logger.info(f"Extracted date using primary pattern: {date_str}")
            return date_str
        
        # Expanded set of date patterns to match more formats
        date_patterns = [
            # Check for common formats with explicit date labels
            r'(?i)(?:date|invoice date|bill date)(?:\s*)?[:.]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'(?i)(?:date|invoice date|bill date)(?:\s*)?[:.]?\s*(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
            
            # Common date formats (without labels)
            r'\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b',  # 01/31/2022, 31-01-2022, etc.
            r'\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})\b',     # 2022/01/31, 2022-01-31, etc.
            
            # Text date formats
            r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}\b'
        ]
        
        # Check date lines first (these are more likely to contain the invoice date)
        for pattern in date_patterns:
            for line in date_lines:
                matches = re.findall(pattern, line)
                if matches:
                    date_str = matches[0].strip()
                    self.logger.info(f"Extracted date from keyword line using pattern {pattern}: {date_str}")
                    return date_str
        
        # Then check the entire text
        for pattern in date_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                date_str = matches[0].strip()
                self.logger.info(f"Extracted date from full text using pattern {pattern}: {date_str}")
                return date_str
        
        # If we still don't have a date, try a more aggressive approach
        # Look for any sequence that looks like a date
        broader_date_pattern = r'\b\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}\b'
        matches = re.findall(broader_date_pattern, all_text)
        if matches:
            # Take the first one that appears after "date" or near the top if no "date" keyword
            possible_date = matches[0].strip()
            self.logger.info(f"Extracted potential date using broader pattern: {possible_date}")
            return possible_date
        
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

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process an image file using Tesseract OCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict containing extracted information and raw text
            
        Raises:
            OCRError: If the image is invalid
            OCRExtractionError: If OCR extraction fails
        """
        try:
            # Validate the image file
            self.validate_image(image_path)
            
            # Open and process the image
            self.logger.info(f"Processing image: {image_path}")
            
            try:
                # Open the image with PIL
                img = Image.open(image_path)
                
                # Preprocess the image for better OCR results
                processed_img = self.preprocess_image(img)
                
                # Perform OCR on the processed image
                text = pytesseract.image_to_string(processed_img, **self.tesseract_config)
                
                # Store the extracted text
                results = [{
                    "page": 1,  # Single page for images
                    "text": text,
                    "confidence": self._get_confidence(processed_img)
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
                    "raw_text": text,
                    "pages": 1,
                    "confidence": self._get_confidence(processed_img)
                }
                
                self.logger.info(f"Extraction completed with confidence: {extracted_data['confidence']:.2f}%")
                return extracted_data
                
            except Exception as e:
                self.logger.error(f"Error processing image: {str(e)}")
                raise OCRExtractionError(f"Failed to process image: {str(e)}")
                
        except OCRError:
            raise
        except Exception as e:
            self.logger.error(f"OCR extraction error: {str(e)}")
            raise OCRExtractionError(f"Failed to process image: {str(e)}")


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

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process an image file using AWS Textract
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict containing extracted information and raw text
            
        Raises:
            OCRError: If the image is invalid
            OCRExtractionError: If OCR extraction fails
        """
        try:
            # Validate the image file
            self.validate_image(image_path)
            
            # Read the image file as bytes
            with open(image_path, 'rb') as file:
                image_bytes = file.read()
            
            # Process the image with Textract
            self.logger.info(f"Processing image with AWS Textract: {image_path}")
            
            # Use the synchronous API for images
            try:
                response = self.textract_client.detect_document_text(Document={'Bytes': image_bytes})
                text_blocks = response['Blocks']
            
                # Extract text from Textract blocks
                full_text = ""
                for block in text_blocks:
                    if block['BlockType'] == 'LINE':
                        full_text += block['Text'] + "\n"
                
                # Create a result structure
                results = [{
                    "page": 1,  # Single page for images
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
                    "pages": 1,
                    "confidence": self._get_confidence(text_blocks)
                }
                
                self.logger.info(f"Extraction completed with confidence: {extracted_data['confidence']:.2f}%")
                return extracted_data
                
            except boto3.exceptions.Boto3Error as e:
                self.logger.error(f"AWS Textract error: {str(e)}")
                raise OCRExtractionError(f"Failed to process with AWS Textract: {str(e)}")
                
        except OCRError:
            raise
        except Exception as e:
            self.logger.error(f"OCR extraction error: {str(e)}")
            raise OCRExtractionError(f"Failed to process image: {str(e)}")


def create_processor(processor_type: str = "tesseract", config: Optional[Dict[str, Any]] = None) -> OCRProcessor:
    """
    Create an OCR processor of the specified type
    
    Args:
        processor_type: Type of processor to create ('tesseract' or 'textract')
        config: Configuration for the processor
        
    Returns:
        An instance of OCRProcessor
        
    Raises:
        ValueError: If the processor type is invalid
    """
    if processor_type.lower() == "tesseract":
        return TesseractProcessor(config)
    elif processor_type.lower() == "textract":
        return TextractProcessor(config)
    else:
        raise ValueError(f"Invalid processor type: {processor_type}. Valid types are 'tesseract' or 'textract'")