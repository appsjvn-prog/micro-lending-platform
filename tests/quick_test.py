from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post('/register', json={
    'email': 'test123@example.com',
    'phone': {'country_code': '+91', 'national_number': '9876543210'},
    'role': 'BORROWER'
})

print("Status:", response.status_code)
print("Response:", response.json())