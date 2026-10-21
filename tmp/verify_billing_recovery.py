import requests

url = "https://api-som-fastapi-production-e66d.up.railway.app/invoicing/facturables"
with requests.Session() as session:
    for i in range(100):
        response = session.get(
            url, params={"cliente": "EL SURCO"},
            headers={"X-Company-Code": "MCI-CR"}, timeout=20,
        )
        response.raise_for_status()
        assert response.json()["total"] == 2
        if (i + 1) % 20 == 0:
            print(f"{i + 1}/100 consultas correctas", flush=True)
