import requests


def test_ping():
    r = requests.get("http://localhost:8000/api/ping")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"


if __name__ == "__main__":
    print("Running smoke test...")
    test_ping()
    print("OK")
