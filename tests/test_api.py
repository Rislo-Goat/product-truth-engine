"""Tests d'API (santé + analyse de sourcing synchrone)."""
from fastapi.testclient import TestClient

from jarvis_os.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "connectors" in body
    # AliExpress sans credentials => AUTH_REQUIRED (jamais AVAILABLE par défaut)
    assert body["connectors"]["aliexpress"] in ("AUTH_REQUIRED", "AVAILABLE")


def test_capabilities():
    r = client.get("/capabilities")
    assert r.status_code == 200
    assert "reborn_doll" in r.json()["categories"]


def test_analyze_endpoint_blocks_lie():
    payload = {
        "category": "reborn_doll",
        "selling_price": 109.99,
        "destination": "UK",
        "claim": {"source": "shopify:kim", "title": "Full Silicone Reborn Boy 50cm"},
        "candidates": [{
            "supplier": "manual", "external_id": "s2", "title": "Reborn doll 50cm",
            "price": 20,
            "listing": {"source": "supplier:manual#s2", "title": "Reborn doll 50cm",
                        "specifications": {"material": "vinyl", "body": "cloth body"},
                        "description": "soft cloth body with vinyl limbs boy"},
        }],
    }
    r = client.post("/sourcing/analyze", json=payload)
    assert r.status_code == 200
    opp = r.json()["opportunities"][0]
    assert opp["hard_blocks"]
    assert opp["recommendation"] == "REJECT"


def test_analyze_requires_candidates():
    payload = {"category": "reborn_doll",
               "claim": {"source": "shopify:kim", "title": "Reborn Boy"}, "candidates": []}
    r = client.post("/sourcing/analyze", json=payload)
    assert r.status_code == 400
