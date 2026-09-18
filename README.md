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

## Architecture

- `dashboard/` - React + Vite + TanStack Router admin dashboard, deployed to Vercel.
- `poller.py` - long-running Railway worker that polls the Supabase jobs table,
  downloads uploads, runs the processor, writes records, and enqueues notifications.
- `processor.py` / `backend/processor.py` - document extraction logic shared by the poller.
- `requirements.txt` - runtime dependencies for the poller and processor.
- `Dockerfile` - Railway build image (python:3.12-slim) running `python3 poller.py`.

## Archetype

Document-in, records-out extraction service.

- Input: raw file bytes (PDF, Excel, CSV, or plain text).
- Processing: text extraction via `pdfplumber` for PDF and `openpyxl` for Excel,
  with a UTF-8 decode fallback for CSV and plain text. Simple tabular data is
  parsed directly; contract-like narrative text is routed to the model for
  structured extraction when an API key is present.
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

## Poller

`poller.py` runs an infinite loop (`poll()`) with a 60 second sleep. On each tick it:

1. Queries Supabase `jobs` for rows where `status=eq.pending`,
   `job_type=eq.process_upload`, and `product_id=eq.$PRODUCT_ID`.
2. Downloads the upload from the `uploads` storage bucket using the service key,
   sending both `Authorization: Bearer` and `apikey` headers.
3. Calls `processor.process_file(file_bytes)` to extract records.
4. Inserts one row per record into the `records` table with `product_id`,
   `customer_id` (from the job), `title`, `status`, `details`, `source_file_path`,
   and `due_date`.
5. Uploads the JSON result to the `results` bucket.
6. Marks the job `completed` or `failed` with `output_file_path`,
   `result_summary`, and `completed_at`.
7. Inserts a `success` or `error` notification row for the job customer.

Environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `PRODUCT_ID`,
`ANTHROPIC_API_KEY`.

## Dashboard

The Vercel dashboard is built from the vokrix dashboard template and customized
via `VITE_*` environment variables configured in the Vercel project:

- `VITE_PRODUCT_ARCHETYPE=extraction`
- `VITE_RECORDS_LABEL=Contract Renewals`
- `VITE_RECORDS_SUBTITLE=Compliance and price-fairness verdicts for each vendor renewal quote against the signed contract`
- `VITE_FILTER_PLACEHOLDER=Filter by vendor, contract, or status`
- `VITE_UPLOAD_DESCRIPTION=Upload your signed contract and vendor renewal quote PDFs and we will detect renewal pricing and terms compliance automatically.`
- `VITE_UPLOAD_EMPTY_STATE=No contracts or renewal quotes uploaded yet.`

The task surface is customized in `dashboard/src/features/tasks/data/data.tsx`
with renewal-compliance statuses and matching lucide-react icons.

## Files

| File | Purpose |
|------|---------|
| `processor.py` | Main extraction processor. Returns records with `title`, `status`, `details`, `due_date`. |
| `poller.py` | Railway worker polling Supabase jobs and writing records. |
| `run_demo.py` | Zero-argument demo that runs `process_file` on hardcoded CSV bytes and prints the JSON result. Exits `0`. |
| `run_tests.py` | Zero-argument tests for CSV parsing, required top-level keys, status membership, and fallback handling. Exits `0` when all pass. |
| `requirements.txt` | Runtime dependencies. |

## Running

```
pip install -r requirements.txt
python3 run_demo.py
python3 run_tests.py
python3 poller.py
```
