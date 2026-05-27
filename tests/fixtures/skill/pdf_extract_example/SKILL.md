---
name: pdf-invoice-extract
description: Extract structured fields (vendor, total, tax, currency, line items) from PDF invoices in French or English. Use when the user asks to parse, extract, read, or process a PDF invoice or facture.
compatibility: python>=3.10, pdfplumber>=0.10
---

# PDF invoice extraction

## Overview

Parse a PDF invoice and return a JSON object with normalized fields. Handles
both French (`facture`) and English (`invoice`) layouts. Falls back to OCR
via `tesseract` if text extraction returns less than 50 characters.

## When to use this skill

- The user uploads a PDF and asks for "the total", "the line items", or "the vendor"
- The user pastes an invoice URL and asks for a structured summary
- The user wants to compare two invoices

Do NOT use this skill for:

- Image invoices (use the dedicated OCR skill)
- Receipts (different layout — use `receipt-parse` skill)
- Tax filings (different schema)

## Workflow

1. Load the PDF with `pdfplumber`.
2. Extract text page by page.
3. Detect language from the first 200 characters (`fr` vs `en`).
4. Apply the language-specific regex bank to find anchors (`Total`, `TVA`, `VAT`, `Facture nº`).
5. Parse line items from the table region.
6. Normalize currency to ISO 4217.
7. Return the JSON.

## Files in this skill

- `scripts/extract.py` — main extraction logic
- `scripts/normalize.py` — currency and date normalization
- `references/anchors_fr.yaml` — French regex bank
- `references/anchors_en.yaml` — English regex bank
- `examples/invoice_fr.pdf` — sample French invoice
- `examples/invoice_en.pdf` — sample English invoice

## Example invocation

> Extract the line items from this invoice.pdf and return the totals.

## Expected output

```json
{
  "vendor": "Acme SAS",
  "invoice_number": "FA-2026-00142",
  "issue_date": "2026-03-12",
  "currency": "EUR",
  "subtotal": 1250.00,
  "tax": 250.00,
  "total": 1500.00,
  "line_items": [
    {"description": "Consulting Q1", "quantity": 10, "unit_price": 125.00}
  ]
}
```
