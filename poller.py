import os
import time
import json
import base64
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://njyvnmczoydsaewvfhyq.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
PRODUCT_ID = os.environ.get("PRODUCT_ID", "")
REST_URL = f"{SUPABASE_URL}/rest/v1"

SB_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "apikey": SUPABASE_SERVICE_KEY,
}


def download_file(bucket, file_path):
    if file_path.startswith(bucket + "/"):
        file_path = file_path[len(bucket) + 1:]
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "apikey": SUPABASE_SERVICE_KEY})
    resp.raise_for_status()
    return resp.content


def upload_file(bucket, file_path, data, content_type="application/octet-stream"):
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp


def fetch_pending_jobs():
    url = (
        f"{REST_URL}/jobs?status=eq.pending&job_type=eq.process_upload"
        f"&product_id=eq.{PRODUCT_ID}&select=*"
    )
    resp = requests.get(url, headers=SB_HEADERS)
    resp.raise_for_status()
    return resp.json()


def update_job(job_id, payload):
    url = f"{REST_URL}/jobs?id=eq.{job_id}"
    headers = {**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"}
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp


def insert_records(records, job):
    customer_id = job.get("customer_id")
    for r in records:
        requests.post(
            REST_URL + "/records",
            headers={**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={
                "product_id": PRODUCT_ID,
                "customer_id": customer_id,
                "title": r["title"],
                "status": r["status"],
                "details": r["details"],
                "source_file_path": job["input_file_path"],
                "due_date": r.get("due_date"),
            },
        )


def insert_notification(product_id, customer_id, title, body, notif_type):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/notifications",
            headers={**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={
                "product_id": product_id,
                "customer_id": customer_id,
                "title": title,
                "body": body,
                "type": notif_type,
                "read": False,
            },
        )
    except Exception as e:
        print(f"Notification failed (non-fatal): {e}")


def process_job(job):
    job_id = job.get("id")
    customer_id = job.get("customer_id")
    input_file_path = job.get("input_file_path")
    try:
        import processor

        file_bytes = download_file("uploads", input_file_path)
        records = processor.process_file(file_bytes)

        insert_records(records, job)

        summary = json.dumps({"record_count": len(records)})
        output_path = f"{PRODUCT_ID}/{job_id}/results.json"
        try:
            upload_file(
                "results",
                output_path,
                json.dumps(records).encode("utf-8"),
                "application/json",
            )
        except Exception as e:
            print(f"Storage upload failed (non-fatal): {e}")

        update_job(job_id, {
            "status": "completed",
            "output_file_path": output_path,
            "result_summary": summary,
            "completed_at": "now()",
        })

        insert_notification(
            PRODUCT_ID, customer_id,
            "Processing complete",
            "Your upload has been processed successfully.",
            "success",
        )
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        try:
            update_job(job_id, {
                "status": "failed",
                "result_summary": str(e)[:500],
                "completed_at": "now()",
            })
        except Exception as ue:
            print(f"Failed to mark job failed: {ue}")

        insert_notification(
            PRODUCT_ID, customer_id,
            "Processing failed",
            "There was an error processing your upload.",
            "error",
        )


def poll():
    while True:
        try:
            jobs = fetch_pending_jobs()
            for job in jobs:
                process_job(job)
        except Exception as e:
            print(f"Poll cycle error: {e}")
        time.sleep(60)


if __name__ == "__main__":
    print("Poller started")
    poll()
