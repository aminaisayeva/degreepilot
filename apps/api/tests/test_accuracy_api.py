import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import get_settings
from app.core.db import get_session
from app.main import app
from app.models.course import Course
from app.models.requirement import Requirement
from app.seed.courses import CS_AND_ECON_COURSES
from app.seed.expand import expand_dynamic_requirements
from app.seed.requirements import PROGRAMS


@pytest.fixture
def client(monkeypatch):
    # TestClient triggers the lifespan; never let it seed the real file DB.
    monkeypatch.setattr(get_settings(), "seed_on_startup", False)

    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        for spec in CS_AND_ECON_COURSES:
            s.add(Course(**spec))
        for program, reqs in expand_dynamic_requirements(PROGRAMS, CS_AND_ECON_COURSES).items():
            for spec in reqs:
                s.add(Requirement(program=program, **spec))
        s.commit()

        def _override():
            yield s

        app.dependency_overrides[get_session] = _override
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


def test_accuracy_data_shape(client):
    r = client.get("/admin/accuracy/data")
    assert r.status_code == 200
    data = r.json()
    slugs = [p["slug"] for p in data["programs"]]
    assert "columbia_cs_major" in slugs and "columbia_ms_cs" in slugs
    cs = next(p for p in data["programs"] if p["slug"] == "columbia_cs_major")
    req_names = [q["name"] for q in cs["requirements"]]
    assert "Data Structures" in req_names
    ds = next(q for q in cs["requirements"] if q["name"] == "Data Structures")
    codes = [c["code"] for c in ds["courses"]]
    assert "COMS W3134" in codes
    assert all(c["in_catalog"] for c in ds["courses"])
    assert "columbia_cs_major" in data["summary"]
    assert data["catalog_size"] == len(CS_AND_ECON_COURSES)


def test_check_upsert_and_reset(client):
    body = {"entity_type": "course", "entity_key": "COMS W3134",
            "status": "verified", "notes": "matches bulletin"}
    r = client.post("/admin/accuracy/check", json=body)
    assert r.status_code == 200
    assert r.json()["status"] == "verified"

    # upsert (same key) flips status, doesn't duplicate
    body["status"] = "incorrect"
    r = client.post("/admin/accuracy/check", json=body)
    assert r.status_code == 200

    data = client.get("/admin/accuracy/data").json()
    assert data["summary"]["columbia_cs_major"]["incorrect"] >= 1

    # reset deletes
    body["status"] = "unchecked"
    r = client.post("/admin/accuracy/check", json=body)
    assert r.status_code == 200
    data = client.get("/admin/accuracy/data").json()
    assert data["summary"]["columbia_cs_major"]["incorrect"] == 0


def test_requirement_check_roundtrip(client):
    key = "columbia_cs_major/Data Structures"
    r = client.post("/admin/accuracy/check", json={
        "entity_type": "requirement", "entity_key": key, "status": "verified"})
    assert r.status_code == 200
    data = client.get("/admin/accuracy/data").json()
    cs = next(p for p in data["programs"] if p["slug"] == "columbia_cs_major")
    ds = next(q for q in cs["requirements"] if q["name"] == "Data Structures")
    assert ds["check"]["status"] == "verified"


def test_accuracy_page_served(client):
    r = client.get("/admin/accuracy")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "DegreePilot" in r.text and "accuracy" in r.text.lower()


def test_check_validation(client):
    r = client.post("/admin/accuracy/check", json={
        "entity_type": "course", "entity_key": "FAKE X0000", "status": "verified"})
    assert r.status_code == 404
    r = client.post("/admin/accuracy/check", json={
        "entity_type": "course", "entity_key": "COMS W3134", "status": "banana"})
    assert r.status_code == 422
    r = client.post("/admin/accuracy/check", json={
        "entity_type": "recipe", "entity_key": "COMS W3134", "status": "verified"})
    assert r.status_code == 422
