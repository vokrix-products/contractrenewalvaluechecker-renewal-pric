import csv
import datetime
import io
import json
import os
import re

ALLOWED_STATUSES = {
    "missing:warning",
    "expired:critical",
    "valid:good",
    "flagged:warning",
    "compliant:good",
    "deviates:critical",
    "at_risk:warning",
    "unverified:warning",
    "document_derived_fact:good",
    "unverified_finding:warning",
    "silent_change_detected:critical",
    "benchmark_outlier:warning",
    "billing_discrepancy:critical",
    "auto_renewal_trap:critical",
    "escalation_cap_breach:critical",
    "minimum_commitment_shortfall:warning",
    "notice_window_passed:critical",
    "notice_window_approaching:warning",
    "quote_expired:critical",
    "no_baseline:warning",
}

FIELD_NAMES = (
    "vendor_name",
    "contract_title",
    "contract_id",
    "signed_date",
    "effective_date",
    "expiration_date",
    "renewal_date",
    "renewal_term_length",
    "notice_period_days",
    "notice_deadline_date",
    "auto_renewal_flag",
    "opt_out_method",
    "notice_delivery_method",
    "governing_law",
    "contract_value",
    "annual_contract_value",
    "total_contract_value",
    "currency",
    "billing_frequency",
    "payment_terms",
    "unit_price",
    "unit_of_measure",
    "quantity",
    "seat_count",
    "minimum_commitment",
    "minimum_commitment_period",
    "true_up_terms",
    "overage_rate",
    "discount_percent",
    "discount_expiration",
    "price_escalation_clause",
    "escalation_cap_percent",
    "escalation_schedule",
    "indexation_reference",
    "indexation_cap",
    "renewal_price_formula",
    "cap_on_renewal_increase",
    "floor_price",
    "ceiling_price",
    "most_favored_customer_clause",
    "quoted_renewal_price",
    "quoted_renewal_date",
    "quoted_notice_period_days",
    "quoted_term_length",
    "quote_date",
    "quote_expiration_date",
    "quoted_escalation_percent",
    "quoted_minimum_commitment",
    "price_delta_amount",
    "price_delta_percent",
    "date_delta_days",
    "notice_delta_days",
    "escalation_delta_percent",
    "minimum_commitment_delta",
    "overall_verdict",
    "deviation_reason",
    "source_document",
    "page_number",
    "section_heading",
    "clause_text_verbatim",
    "extraction_confidence",
    "finding_type",
    "audit_trail_id",
    "baseline_document_version",
    "current_document_version",
    "vendor_pricing_page_diff",
    "tos_diff",
    "dpa_diff",
    "subprocessor_list_diff",
    "detected_change_date",
    "materiality_flag",
    "benchmark_price_percentile",
    "benchmark_source",
    "benchmark_sample_size",
    "benchmark_date",
    "comparable_cohort",
    "price_fairness_verdict",
    "invoice_amount",
    "invoice_date",
    "invoice_line_item",
    "contract_billing_amount",
    "billing_discrepancy_amount",
    "billing_discrepancy_flag",
)


def process_file(file_bytes: bytes) -> list:
    """
    Extract records from PDF, Excel, CSV, or plain text bytes.

    Always returns a list of dicts. Each dict has top-level keys:
    title, status, details, due_date.
    """
    if not isinstance(file_bytes, bytes):
        raise ValueError("process_file expects file_bytes to be bytes")

    text = _extract_text(file_bytes)

    if not text.strip():
        return _missing_record()

    records = _extract_from_tabular_text(text)
    if records:
        return records

    if _should_use_model(text):
        model_records = _extract_with_deepseek(text)
        if model_records:
            return model_records

    return _fallback_records(text)


def _extract_text(file_bytes: bytes) -> str:
    """Try PDF first, then Excel, then UTF-8 plain text/CSV."""
    # PDF
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                pages.append(page_text)
        if any(pages):
            return "\n".join(pages)
    except Exception:
        pass

    # Excel
    try:
        import openpyxl

        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes),
            read_only=True,
            data_only=True,
        )
        rows = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                values = ["" if cell is None else str(cell) for cell in row]
                rows.append("\t".join(values))
        if rows:
            return "\n".join(rows)
    except Exception:
        pass

    # Plain text, CSV, or other decodeable text
    return file_bytes.decode("utf-8", errors="ignore")


def _extract_from_tabular_text(text: str) -> list | None:
    if not text.strip():
        return None

    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = None
    if "\t" in first_line:
        delimiter = "\t"
    elif "," in first_line:
        delimiter = ","

    if not delimiter:
        return None

    try:
        sample = "\n".join(text.splitlines()[:30])
        reader = csv.reader(io.StringIO(sample), delimiter=delimiter)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]

        if len(rows) < 2:
            return None

        headers = [cell.strip() for cell in rows[0]]
        records = []

        for data_row in rows[1:]:
            values = [cell.strip() for cell in data_row]
            while len(values) < len(headers):
                values.append("")

            details = {headers[i]: values[i] for i in range(len(headers))}
            title = _title_from_details(details)
            due_date = _find_due_date(details)

            records.append(
                {
                    "title": title,
                    "status": "valid:good",
                    "details": details,
                    "due_date": due_date,
                }
            )

        return records if records else None
    except Exception:
        return None


def _title_from_details(details: dict) -> str:
    lower = {str(k).lower(): v for k, v in details.items()}

    for key in (
        "vendor_name",
        "supplier",
        "vendor",
        "company_name",
        "legal_entity_name",
        "counterparty",
        "customer_name",
        "contract_party",
        "patient_name",
        "employee_name",
    ):
        value = lower.get(key)
        if value:
            candidate = str(value).strip()
            if candidate:
                return candidate

    fallback = lower.get("contract_title")
    if fallback:
        candidate = str(fallback).strip()
        definitely_document_type = {
            "contract",
            "agreement",
            "master services agreement",
            "msa",
            "amendment",
            "statement of work",
            "sow",
            "order form",
            "quote",
            "invoice",
            "renewal notice",
        }
        if candidate.lower() not in definitely_document_type:
            return candidate

    return "Unknown vendor"


def _find_due_date(details: dict) -> str | None:
    lower = {str(k).lower(): str(v).strip() for k, v in details.items() if v is not None}

    for key in (
        "due_date",
        "renewal_date",
        "expiration_date",
        "notice_deadline_date",
        "quote_expiration_date",
        "invoice_date",
    ):
        value = lower.get(key)
        if value:
            iso_date = _to_iso_date(value)
            if iso_date:
                return iso_date

    return None


def _to_iso_date(value: str) -> str | None:
    if not value:
        return None

    value = value.strip()
    formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%b %d, %Y",
    )

    for fmt in formats:
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except Exception:
            pass

    return None


def _should_use_model(text: str) -> bool:
    if "DEEPSEEK_API_KEY" not in os.environ:
        return False
    if len(text.strip()) < 200:
        return False

    contract_markers = (
        "vendor_name",
        "contract",
        "renewal",
        "notice_period",
        "expiration_date",
        "auto_renewal",
        "governing_law",
        "payment_terms",
        "minimum_commitment",
        "price_escalation",
        "invoice_amount",
        "quoted_renewal_price",
        "agreement",
        "party",
        "supplier",
        "vendor",
        "statement of work",
        "service agreement",
    )

    lowered = text.lower()
    return any(marker in lowered for marker in contract_markers)


def _extract_with_deepseek(text: str) -> list | None:
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )

        field_names = ", ".join(FIELD_NAMES)
        status_names = ", ".join(sorted(ALLOWED_STATUSES))

        system_prompt = f"""
        You are an extraction engine for RenewalGuard, a contract and vendor document analyzer.
        Return ONLY a JSON array of extracted records. Do not include text before or after the JSON.

        Each record must have exactly these top-level keys:

        - "title": The primary entity the buyer tracks. This must be the vendor name, contract party,
          supplier, patient name, employee name, or similar real-world entity. NEVER use document type
          or category such as "Contract", "Invoice", "Quote", "Renewal", "MSA", etc.
        - "status": One of these exact labels only: {status_names}
        - "details": A flat JSON object. Include any of the following fields when present in the document:
          {field_names}
          Use null or omit unknown fields. Do not nest due_date inside details.
        - "due_date": Top-level ISO 8601 date string, or null if no relevant date exists.

        If you cannot confidently extract the primary entity, use "Unknown vendor".
        Prefer document-derived facts. Use "unverified_finding:warning" for low-confidence or missing evidence.
        """

        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:25000]},
            ],
            temperature=0,
        )

        content = response.choices[0].message.content
        return _parse_model_records(content)
    except Exception:
        return None


def _parse_model_records(content: str) -> list | None:
    if not content:
        return None

    try:
        data = json.loads(content)
    except Exception:
        match = re.search(r"\[[\s\S]*\]|\{[\s\S]*\}", content)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except Exception:
            return None

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None

    records = []
    for item in data:
        if not isinstance(item, dict):
            continue

        details = item.get("details", {})
        if not isinstance(details, dict):
            details = {}

        status = str(item.get("status", "unverified_finding:warning"))
        if status not in ALLOWED_STATUSES:
            status = "unverified_finding:warning"

        due_date = item.get("due_date")
        if not isinstance(due_date, str):
            due_date = None
        else:
            due_date = due_date.strip()

        title = str(item.get("title") or "Unknown vendor").strip()
        if not title:
            title = "Unknown vendor"

        records.append(
            {
                "title": title,
                "status": status,
                "details": details,
                "due_date": due_date,
            }
        )

    return records if records else None


def _fallback_records(text: str) -> list:
    return [
        {
            "title": _title_from_text(text),
            "status": "unverified_finding:warning",
            "details": {
                "source_document": "text",
                "clause_text_verbatim": text[:2000],
                "extraction_confidence": 0.4,
                "finding_type": "unverified_finding",
            },
            "due_date": None,
        }
    ]


def _missing_record() -> list:
    return [
        {
            "title": "Unknown vendor",
            "status": "unverified_finding:warning",
            "details": {
                "source_document": "unknown",
                "extraction_confidence": 0.0,
                "finding_type": "unverified_finding",
            },
            "due_date": None,
        }
    ]


def _title_from_text(text: str) -> str:
    document_type_words = (
        "contract",
        "agreement",
        "renewal",
        "invoice",
        "statement of work",
        "order form",
        "quote",
    )

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(word in lower for word in document_type_words):
            continue
        return line

    return "Unknown vendor"


def extract_text(file_bytes):
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ""
            for p in pdf.pages:
                text = text + (p.extract_text() or "") + "\n"
            if text.strip():
                return text
    except Exception:
        pass
    return file_bytes.decode("utf-8", errors="ignore")
