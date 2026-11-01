from __future__ import annotations

import json
import logging

from app.api.routes import health
from app.services.speech_recognition import get_model


def test_health_and_readiness_do_not_load_model(client):
    assert get_model.cache_info().currsize == 0

    health_response = client.get("/health")
    readiness_response = client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert readiness_response.status_code == 200
    assert readiness_response.json()["model_loaded"] is False
    assert get_model.cache_info().currsize == 0


def test_warmup_returns_stable_error_when_model_load_fails(client, monkeypatch):
    monkeypatch.setattr(health, "warmup_model", lambda: (_ for _ in ()).throw(RuntimeError("private cause")))

    response = client.post("/api/model/warmup")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "MODEL_NOT_READY"
    assert "private cause" not in body["detail"]
    assert len(body["error"]["request_id"]) == 32


def test_openapi_documents_sequence_and_request_logging(client, caplog):
    caplog.set_level(logging.INFO, logger="multilingual.stt")
    schema = client.get("/openapi.json").json()
    response = client.get("/health")

    multipart_schema = schema["paths"]["/api/transcribe"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]
    if "$ref" in multipart_schema:
        component_name = multipart_schema["$ref"].rpartition("/")[2]
        multipart_schema = schema["components"]["schemas"][component_name]
    parameter_names = set(multipart_schema["properties"])
    request_logs = [record.message for record in caplog.records if record.message.startswith("request_complete ")]

    assert {"audio", "language", "sequence"} <= parameter_names
    assert response.headers["X-Request-ID"].isalnum()
    assert json.loads(request_logs[-1].removeprefix("request_complete "))["path"] == "/health"
