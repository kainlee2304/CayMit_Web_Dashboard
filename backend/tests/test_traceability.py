from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, TraceEvent, get_db
from routers.traceability import router


def make_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'traceability.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), testing_session


def bootstrap(client):
    response = client.post("/api/traceability/auth/bootstrap", json={
        "username": "admin", "password": "Admin@123",
        "display_name": "Quản trị Tam Mỹ", "organization": "Tam Mỹ Smart Fruit",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_traceability_chain_and_qr(tmp_path):
    client, _ = make_client(tmp_path)
    headers = bootstrap(client)
    created = client.post("/api/traceability/batches", json={
        "product_name": "Mít tươi",
        "variety": "Mít Thái",
        "farm_name": "HTX Tam Mỹ",
        "origin": "Quảng Nam",
    }, headers=headers)
    assert created.status_code == 201
    batch = created.json()
    assert batch["verified"] is True
    assert len(batch["events"]) == 1

    appended = client.post(f"/api/traceability/{batch['trace_code']}/events", json={
        "stage": "harvest",
        "title": "Thu hoạch đạt chuẩn",
        "location": "Quảng Nam",
    }, headers=headers)
    assert appended.status_code == 201
    assert appended.json()["events"][1]["previous_hash"] == batch["events"][0]["block_hash"]
    qr = client.get(f"/api/traceability/{batch['trace_code']}/qr")
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/png"
    assert qr.content.startswith(b"\x89PNG")


def test_tampering_is_detected(tmp_path):
    client, testing_session = make_client(tmp_path)
    headers = bootstrap(client)
    batch = client.post("/api/traceability/batches", json={
        "product_name": "Mít tươi", "farm_name": "Vườn A", "origin": "Tam Mỹ",
    }, headers=headers).json()
    with testing_session() as db:
        event = db.query(TraceEvent).first()
        event.details = "Dữ liệu đã bị sửa"
        db.commit()
    verified = client.get(f"/api/traceability/{batch['trace_code']}").json()
    assert verified["verified"] is False
    assert verified["broken_at_block"] == 0


def test_role_permissions(tmp_path):
    client, _ = make_client(tmp_path)
    admin_headers = bootstrap(client)
    for username, role in (("nongho", "producer"), ("donggoi", "processor"), ("vanchuyen", "logistics")):
        response = client.post("/api/traceability/users", headers=admin_headers, json={
            "username": username, "password": "Operator@123", "display_name": username,
            "organization": f"Đơn vị {username}", "role": role,
        })
        assert response.status_code == 201

    login = client.post("/api/traceability/auth/login", json={"username":"nongho", "password":"Operator@123"})
    producer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post("/api/traceability/batches", headers=producer_headers, json={
        "product_name":"Mít VietGAP", "farm_name":"Vườn B", "origin":"Quảng Nam",
    })
    assert created.status_code == 201
    code = created.json()["trace_code"]
    assert client.post(f"/api/traceability/{code}/events", headers=producer_headers, json={
        "stage":"harvest", "title":"Thu hoạch",
    }).status_code == 201
    assert client.post(f"/api/traceability/{code}/events", headers=producer_headers, json={
        "stage":"packing", "title":"Đóng gói trái phép",
    }).status_code == 403
    assert client.post("/api/traceability/batches", json={
        "product_name":"Ẩn danh", "farm_name":"Vườn X", "origin":"X",
    }).status_code == 401
    assert client.get(f"/api/traceability/{code}").status_code == 200


def test_batch_ownership_access_workflow_and_pagination(tmp_path):
    client, _ = make_client(tmp_path)
    admin_headers = bootstrap(client)
    for username, role, organization in (
        ("farm_a", "producer", "HTX A"),
        ("factory_b", "processor", "Nhà máy B"),
    ):
        assert client.post("/api/traceability/users", headers=admin_headers, json={
            "username": username, "password": "Operator@123", "display_name": username,
            "organization": organization, "role": role,
        }).status_code == 201

    def login(username):
        response = client.post("/api/traceability/auth/login", json={
            "username": username, "password": "Operator@123",
        })
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    farm_headers, factory_headers = login("farm_a"), login("factory_b")
    created = client.post("/api/traceability/batches", headers=farm_headers, json={
        "product_name": "Mít thật", "farm_name": "Vườn A", "origin": "Quảng Nam",
    })
    code = created.json()["trace_code"]
    assert created.json()["owner_organization"] == "HTX A"
    assert client.get("/api/traceability/batches", headers=factory_headers).json()["total"] == 0
    denied = client.post(f"/api/traceability/{code}/events", headers=factory_headers, json={
        "stage": "processing", "title": "Sơ chế chưa được cấp quyền",
    })
    assert denied.status_code == 403

    granted = client.post(f"/api/traceability/batches/{code}/access", headers=farm_headers,
                          json={"username": "factory_b"})
    assert granted.status_code == 201
    listing = client.get("/api/traceability/batches?page=1&page_size=1&search=Mít", headers=factory_headers).json()
    assert listing["total"] == 1 and listing["pages"] == 1
    invalid = client.post(f"/api/traceability/{code}/events", headers=factory_headers, json={
        "stage": "processing", "title": "Sơ chế quá sớm",
    })
    assert invalid.status_code == 409
    assert client.post(f"/api/traceability/{code}/events", headers=farm_headers, json={
        "stage": "harvest", "title": "Thu hoạch",
    }).status_code == 201
    assert client.post(f"/api/traceability/{code}/events", headers=factory_headers, json={
        "stage": "processing", "title": "Sơ chế",
    }).status_code == 201
    locked = client.post(f"/api/traceability/batches/{code}/lock", headers=farm_headers)
    assert locked.status_code == 200 and locked.json()["locked"] is True
    assert client.post(f"/api/traceability/{code}/events", headers=factory_headers, json={
        "stage": "packing", "title": "Không được ghi sau khóa",
    }).status_code == 409


def test_unknown_code_does_not_create_demo_data(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/api/traceability/TM-260817-A1B2C3").status_code == 404
