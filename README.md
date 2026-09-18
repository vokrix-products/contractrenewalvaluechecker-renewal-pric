# ContractRenewalValueChecker (Renewal Pricing & Terms Compliance)

## Product

ContractRenewalValueChecker is a backend extraction service for the RenewalGuard
product line. It ingests vendor contract, pricing, and billing documents and
turns them into structured records that a renewal-compliance dashboard can
compare against a known baseline.

It is built to detect renewal risk: price escalation beyond a contractual cap,
notice windows that have already passed, auto-renewal traps, minimum-commitment
shortfalls, billing discrepancies, and quotes that have expired before they
were signed.

## Archetype

Document-in, records-out extraction service.

- Input: raw file bytes (PDF, Excel, CSV, or plain text).
- Processing: text extraction via `pdfplumber` for PDF and `openpyxl` for
  Excel, with a UTF-8 decode fallback for CSV and plain text. Simple tabular
  data is parsed directly; contract-like narrative text is routed to DeepSeek
  for structured extraction when `DEEPSEEK_API_KEY` is present.
- Output: a JSON list of records, each with top-level keys `title`, `status`,
  `details`, and `due_date`.

## Record contract

Every record returned by `process_file` has exactly these top-level keys:

| Key | Type | Meaning |
|-----|------|---------|
| `title` | string | The real-world entity being tracked (vendor, supplier, counterparty). Never a document type. Falls back to `Unknown vendor`. |
| `status` | string | One of the allowed status labels (see below). |
| `details` | object | Flat object of extracted contract/pricing/billing fields. |
| `due_date` | string or null | Top-level ISO 8601 date for the relevant deadline. |

The processor never nests `due_date` inside `details`.

## Allowed statuses

`missing:warning`, `expired:critical`, `valid:good`, `flagged:warning`,
`compliant:good`, `deviates:critical`, `at_risk:warning`, `unverified:warning`,
`document_derived_fact:good`, `unverified_finding:warning`,
`silent_change_detected:critical`, `benchmark_outlier:warning`,
`billing_discrepancy:critical`, `auto_renewal_trap:critical`,
`escalation_cap_breach:critical`, `minimum_commitment_shortfall:warning`,
`notice_window_passed:critical`, `notice_window_approaching:warning`,
`quote_expired:critical`, `no_baseline:warning`.

## What the poller expects as input

The poller reads one document per job from its input bucket and passes the raw
bytes directly to `processor.process_file(file_bytes)`. Supported inputs:

- PDF: vendor contracts, order forms, statements of work, renewal notices.
- Excel (`.xlsx`/`.xlsm`): pricing schedules, seat-count tables, billing exports.
- CSV / TSV: line-item pricing, invoice exports, subprocessor lists.
- Plain text: pasted contract or notice bodies.

`process_file` accepts `bytes` only. It always returns a JSON-serializable
`list` of record dicts, even for empty, corrupt, or unparseable input.

## Files

| File | Purpose |
|------|---------|
| `processor.py` | Main extraction processor. Returns records with `title`, `status`, `details`, `due_date`. |
| `run_demo.py` | Zero-argument demo that runs `process_file` on hardcoded CSV bytes and prints the JSON result. Exits `0`. |
| `run_tests.py` | Zero-argument tests for CSV parsing, required top-level keys, status membership, and fallback handling. Exits `0` when all pass. |
| `requirements.txt` | Runtime dependencies. |

## Running

```
pip install -r requirements.txt
python3 run_demo.py
python3 run_tests.py
```
