"""End-to-end tests for the FastAPI HTTP surface."""

from __future__ import annotations


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_landing_page_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Smart Invoice Generator" in res.text
    assert "Generate Invoice" in res.text


def test_app_renders_template(client):
    res = client.get("/app")
    assert res.status_code == 200
    assert "Smart Invoice Generator" in res.text
    assert "Document Settings" in res.text


def test_generate_returns_pdf(client, sample_payload):
    res = client.post("/generate", json=sample_payload)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")
    assert "invoice-2026-001.pdf" in res.headers["content-disposition"]


def test_generate_filename_sanitized(client, sample_payload):
    sample_payload["doc_number"] = "INV/2026 #1"
    res = client.post("/generate", json=sample_payload)
    assert res.status_code == 200
    cd = res.headers["content-disposition"]
    assert "/" not in cd.split("filename=")[1]
    assert "#" not in cd.split("filename=")[1]


def test_generate_validation_error_shape(client, sample_payload):
    sample_payload["currency"] = "XYZ"
    res = client.post("/generate", json=sample_payload)
    assert res.status_code == 422
    body = res.json()
    assert body["title"] == "Validation error"
    assert isinstance(body["detail"], list)


def test_generate_missing_required(client):
    res = client.post("/generate", json={})
    assert res.status_code == 422
    assert isinstance(res.json()["detail"], list)


def test_quote_does_not_require_due_date(client, sample_payload):
    sample_payload["doc_type"] = "Quote"
    sample_payload["due_date"] = None
    res = client.post("/generate", json=sample_payload)
    assert res.status_code == 200


def test_extra_field_rejected(client, sample_payload):
    sample_payload["malicious"] = "drop tables"
    res = client.post("/generate", json=sample_payload)
    assert res.status_code == 422


def test_preview_returns_totals(client, sample_payload):
    res = client.post("/api/preview", json=sample_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["currency"] == "USD"
    assert body["subtotal"] == "1119.88"
    assert body["discount_amount"] == "111.99"
    assert body["tax_amount"] == "161.26"
    assert body["grand_total"] == "1169.15"


def test_preview_validation_error(client, sample_payload):
    sample_payload["currency"] = "ZZZ"
    res = client.post("/api/preview", json=sample_payload)
    assert res.status_code == 422


def test_meta_endpoint(client):
    res = client.get("/api/meta")
    assert res.status_code == 200
    body = res.json()
    assert "currencies" in body
    assert "doc_types" in body
    assert "USD" in body["currencies"]
    assert "Invoice" in body["doc_types"]
