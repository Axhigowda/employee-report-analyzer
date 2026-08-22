# Employee Report Analyzer

A Python-based data processing and reporting application for analyzing employee project reports stored in Excel workbooks.

The system ingests raw Excel project reports, cleans and normalizes inconsistent data, converts records into structured project models, performs project-level analysis, and generates a human-readable report through a command-line interface.

## Features

- Excel workbook ingestion using Pandas and OpenPyXL
- Project data cleaning and normalization
- Boolean value normalization
- Project status parsing
- Lifecycle stage classification
- Handling of multi-row project details
- Project-level analytics
- Identification of projects requiring action
- Detection of unknown lifecycle stages
- Employee project selection through CLI
- Automated test coverage
- Real-world Excel workbook integration testing

## Architecture

```text
Excel Workbook
      |
      v
+-------------+
|  Ingestion  |
+-------------+
      |
      v
+----------------+
| Transformation |
|  & Parsing     |
+----------------+
      |
      v
+-------------+
|   Models    |
+-------------+
      |
      v
+-------------+
|   Analysis  |
+-------------+
      |
      v
+-------------+
|  Reporting  |
+-------------+
      |
      v
+-------------+
|     CLI     |
+-------------+
