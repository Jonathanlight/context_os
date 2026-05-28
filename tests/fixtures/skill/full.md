---
name: pdf-extract
title: PDF invoice extraction
description: |
  Extract structured data (vendor, total, tax, line items) from PDF
  invoices in French or English. Triggers when the user asks to parse,
  extract, or process an invoice PDF.
trigger_keywords:
  - pdf
  - invoice
  - extract
  - facture
applies_to:
  - data-extraction
languages_supported:
  - fr
  - en
files:
  - scripts/extract.py
  - examples/invoice_fr.pdf
  - examples/invoice_en.pdf
required_runtime: python>=3.10
example_invocation: Extract the line items from this invoice.pdf
expected_output_format: json
tags:
  - data
  - pdf
  - extraction
---

# PDF invoice extraction

## When to use

When the user uploads a PDF file with the words "invoice" or "facture"
in the filename, or asks to extract structured data from an invoice.

## Files

- `scripts/extract.py` — pdfplumber + regex pipeline.
- `examples/invoice_fr.pdf` — sample French invoice.
- `examples/invoice_en.pdf` — sample English invoice.

## Example invocation

```
Extract the line items from this invoice.pdf
```
