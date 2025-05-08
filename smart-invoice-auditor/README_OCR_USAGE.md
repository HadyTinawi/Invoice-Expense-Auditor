# Smart Invoice Auditor - OCR Usage Guide

This guide explains how to use the OCR functionality in the Smart Invoice Auditor application to extract information from invoice files.

## Starting the OCR UI

1. Navigate to the project directory:
   ```
   cd /path/to/smart-invoice-auditor
   ```

2. Run the OCR UI application:
   ```
   python app.py
   ```

3. The application will start, and you should see a message like:
   ```
   Running on local URL: http://127.0.0.1:7860
   ```

4. Open your browser and go to: http://localhost:7860

## Using the OCR UI with Sample Invoices

The application includes example invoice files for testing:

### Testing Methods

1. **Using the Examples Feature**:
   - The application now includes sample files as examples directly in the UI
   - Simply click on one of the example files at the bottom of the interface

2. **Manual Upload**:
   - Upload a PDF or image file using the file upload button
   - Sample invoice files are located in the `samples` directory:
     - `sample_invoice.pdf`
     - `sample_invoice.png`

3. After uploading or selecting an example, click the "Process Invoice" button

### Sample Invoice Details

The sample invoice contains the following information:

- **Invoice Number**: INV-12345
- **Vendor**: Acme Corporation
- **Invoice Date**: 2023-05-07
- **Due Date**: 2023-06-07
- **Total Amount**: $1,234.56
- **Subtotal**: $1,125.00
- **Tax**: $109.56
- **Line Items**: 3 items (Office Supplies, Software License, Consulting Services)

## Recent Improvements

The OCR functionality has been significantly improved in the latest version:

1. **Robust File Handling**:
   - Better handling of different file types and formats
   - Improved error messages for problematic files

2. **Enhanced Date Extraction**:
   - Support for many date formats including month names
   - Fallback to current date when extraction fails
   - Date normalization to standard ISO format

3. **JSON Serialization**:
   - Fixed issues with JSON serialization of custom objects
   - Proper handling of Decimal values and complex data structures

4. **More Detailed Processing Information**:
   - Enhanced logging of the OCR process
   - More informative error messages
   - Debug information for troubleshooting extraction issues

## Understanding the Output

After processing, you'll see several output sections:

1. **Invoice Summary** - A human-readable summary of the extracted information
2. **Processing Log** - Detailed log of the processing steps and any issues
3. **Invoice Data (Tab)** - Structured JSON representation of the extracted invoice
4. **OCR Raw Data (Tab)** - Raw data from the OCR processor
5. **Extracted Text (Tab)** - Plain text extracted from the document

## Troubleshooting

If you encounter issues with the OCR functionality:

1. **Empty Results**:
   - Check that your file is a valid PDF or image
   - Ensure the file contains text (not just images of text)
   - Try using the Tesseract OCR processor option

2. **Missing Fields**:
   - Some fields may not be extracted if they're in an unusual format
   - The application now uses fallbacks for missing fields like dates
   - Check the Processing Log for details about what was found

3. **Server Errors**:
   - If the server crashes, restart it with `python app.py`
   - Check the logs directory for detailed error information
   - Make sure your Python environment has all required dependencies

4. **File Upload Issues**:
   - Ensure file size is under the maximum limit
   - Try converting PDFs to images if they're not processing correctly
   - Check file permissions if you're getting access errors

## Next Steps

Once you've successfully tested the OCR functionality:

1. Try uploading your own invoices to see how well the OCR works
2. Review the extracted data for accuracy
3. If needed, modify the OCR extraction logic in `src/ocr/processor.py`
4. Integrate the extracted invoice data with the policy validation system

For more information on developing the OCR functionality, see the code in:
- `src/ocr/processor.py` - OCR processing logic
- `src/models/utils.py` - Invoice creation from OCR data
- `app.py` - Web interface for OCR testing

## Feedback and Contributions

If you find issues or have suggestions for improving the OCR functionality:
1. Check the existing issues in the project tracker
2. Submit bug reports with sample invoices that demonstrate the issue
3. Contribute improvements to the OCR extraction logic 