from processor import process_file, ALLOWED_STATUSES


def main() -> int:
    sample = b"supplier,product,price\nAcme,Widget,9.99"
    results = process_file(sample)

    assert isinstance(results, list)
    assert results

    record = results[0]
    assert isinstance(record, dict)

    for key in ("title", "status", "details", "due_date"):
        assert key in record

    assert isinstance(record["details"], dict)
    assert isinstance(record["due_date"], str) or record["due_date"] is None
    assert record["status"] in ALLOWED_STATUSES
    assert record["title"] == "Acme"

    fallback = process_file(b"%PDF-1.6 broken fake")
    assert isinstance(fallback, list)
    assert fallback

    print("run_tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
