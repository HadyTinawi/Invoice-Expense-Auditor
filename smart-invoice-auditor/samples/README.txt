# Sample Invoices for Testing

This directory contains sample invoice files for testing the OCR functionality.

## Sample Format

Ideally, sample invoices should include:
- Invoice Number/ID
- Issue Date
- Vendor Information
- Line Items
- Subtotal
- Tax
- Total Amount
- Payment Terms

## Testing Process

1. Upload the invoice to the OCR UI (run `python app.py` from the project root)
2. Check the extracted information for accuracy
3. Note any fields that weren't correctly extracted
4. Adjust the OCR extraction logic if needed

## Sources for Sample Invoices

You can create sample invoices using:
- Templates from Microsoft Office, Google Docs, etc.
- Online invoice generators
- Anonymized versions of real invoices (with sensitive information removed)
- Scanned printed invoices

## Testing Quality

For thorough testing, include:
- High-quality digital PDFs
- Scanned document samples
- Different invoice layouts
- Invoices with varying clarity and resolution
- Samples with different fonts and formatting 