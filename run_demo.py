from processor import process_file
import json


def main() -> int:
    test_bytes = b"supplier,product,price\nAcme,Widget,9.99"
    results = process_file(test_bytes)

    assert isinstance(results, list)
    assert len(results) > 0

    record = results[0]
    assert isinstance(record, dict)
    assert isinstance(record["details"], dict)
    assert set(["title", "status", "details", "due_date"]).issubset(record.keys())

    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
