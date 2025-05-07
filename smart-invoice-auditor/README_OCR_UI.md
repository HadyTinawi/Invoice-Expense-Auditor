# OCR Testing UI for Smart Invoice Auditor

This is a simple UI for testing the OCR (Optical Character Recognition) functionality of the Smart Invoice Auditor application. It allows you to upload a PDF invoice or an image of an invoice and see the extracted information.

## Requirements

- Python 3.7+
- Tesseract OCR (must be installed on your system)
- Required Python packages (install using `pip install -r requirements.txt` or see below)

### Required Python Packages

- gradio
- pytesseract
- pdf2image
- pillow
- boto3 (only if using AWS Textract)

### Installing Tesseract OCR

#### macOS
```bash
brew install tesseract
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### Windows
Download and install the latest installer from: https://github.com/UB-Mannheim/tesseract/wiki

## Running the UI

Navigate to the project directory and run:

```bash
python app.py
```

This will start a web server at http://localhost:7860. You can then open this URL in your browser to use the interface.

## Using the UI

1. Upload a PDF or image file of an invoice using the file upload area
2. Select the OCR processor to use (Tesseract is recommended for local use)
3. Click the "Process Invoice" button
4. View the extracted information:
   - Invoice Summary: Displays a human-readable summary of the invoice
   - JSON Data: Shows the structured data in JSON format
   - Raw Text: Shows the raw text extracted from the document

## Sample Files

You can place sample invoice files in the `samples` directory for testing purposes.

## Troubleshooting

If you encounter errors:

1. Make sure Tesseract OCR is properly installed and in your system PATH
2. Check that all required Python packages are installed
3. Ensure the invoice file is a valid PDF or image file
4. For higher quality results, use clear, high-resolution images

## Note on Performance

OCR performance may vary depending on:
- Image quality and resolution
- Invoice layout and complexity
- Font types and sizes
- Presence of noise, watermarks, or background elements

For best results, use high-quality scans or digital PDFs. 