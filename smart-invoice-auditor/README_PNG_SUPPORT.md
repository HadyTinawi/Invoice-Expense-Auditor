# PNG and Image File Support for Smart Invoice Auditor

This document outlines the new image file support feature added to the Smart Invoice Auditor application.

## Feature Overview

The OCR functionality has been enhanced to support the following file types:
- PDF (previously supported)
- PNG (new)
- JPG/JPEG (new)
- TIFF (new)
- BMP (new)
- GIF (new)

## How It Works

The application now uses a more generalized approach to file processing:

1. The `process_file` method in the `OCRProcessor` class now detects the file type based on extension and routes to the appropriate processing method.
2. Both `TesseractProcessor` and `TextractProcessor` classes now have dedicated `process_image` methods that handle image files directly.
3. The UI has been updated to clearly indicate that both PDF and image files are supported.

## Using the Feature

You can use image files with the Smart Invoice Auditor in the following ways:

### Through the Web UI

1. Start the application by running `python app.py` from the smart-invoice-auditor directory.
2. Open your browser to the displayed URL (typically http://127.0.0.1:7865).
3. Upload any supported file type (PDF, PNG, JPG, etc.) using the file uploader.
4. Click "Process Invoice" to extract information.

### Through the API

```python
from src.ocr.processor import create_processor

# Create an OCR processor
processor = create_processor("tesseract")  # or "textract"

# Process any supported file type
ocr_data = processor.process_file("path/to/invoice.png")  # or .pdf, .jpg, etc.

# Use the extracted data
print(f"Invoice ID: {ocr_data.get('invoice_id')}")
print(f"Total Amount: {ocr_data.get('total')}")
```

## Testing the Feature

A test script is included to verify image processing functionality:

```bash
python test_png_processing.py
```

This script tests the OCR engine with a sample PNG invoice and reports the results.

## Sample Files

The `samples` directory includes example files for testing:
- `sample_invoice.pdf` - A sample PDF invoice
- `sample_invoice.png` - A sample PNG image of an invoice

## Dependencies

The image support relies on the following Python libraries:
- Pillow (PIL) - For image processing
- pytesseract - For OCR using Tesseract
- boto3 - For AWS Textract integration (when using the TextractProcessor)

All dependencies are listed in the requirements.txt file.

## Troubleshooting

If you encounter issues with image processing:

1. Ensure the image is clear and readable by humans
2. Try preprocessing the image (increasing contrast, grayscale conversion) before uploading
3. Check the logs for detailed error messages
4. Verify that Tesseract is properly installed on your system

## Limitations

- GIF files support only the first frame of the animation
- Very large or high-resolution images may require more memory
- Image quality significantly affects OCR accuracy 