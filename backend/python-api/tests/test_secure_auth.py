import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add app folder to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import hash_password, verify_password

# In-memory mock database stores
db_stores = {
    "users": [],
    "user_profiles": [],
    "auth_events": [],
    "pending_registrations": []
}

class MockCollection:
    def __init__(self, name, store):
        self.name = name
        self.store = store

    async def find_one(self, query):
        email = query.get("email")
        code = query.get("code")
        for doc in self.store:
            if doc.get("email") == email:
                if code is not None and doc.get("code") != code:
                    continue
                return doc
        return None

    async def insert_one(self, document):
        class InsertOneResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        doc_copy = dict(document)
        if "_id" not in doc_copy:
            import uuid
            doc_copy["_id"] = str(uuid.uuid4())
        self.store.append(doc_copy)
        return InsertOneResult(doc_copy["_id"])

    async def update_one(self, query, update):
        email = query.get("email")
        set_vals = update.get("$set", {})
        count = 0
        for doc in self.store:
            if doc.get("email") == email:
                doc.update(set_vals)
                count += 1
        return MagicMock(modified_count=count)

    async def delete_many(self, query):
        email = query.get("email")
        original_len = len(self.store)
        self.store[:] = [doc for doc in self.store if doc.get("email") != email]
        return MagicMock(deleted_count=original_len - len(self.store))

def get_mock_database():
    mock_db = MagicMock()
    def get_collection(name):
        if name not in db_stores:
            db_stores[name] = []
        return MockCollection(name, db_stores[name])
    mock_db.__getitem__.side_effect = get_collection
    return mock_db

# Patch get_database and validate_email
db_patcher = patch('app.services.auth.get_database', side_effect=get_mock_database)
db_patcher.start()

email_validator_patcher = patch('app.services.auth.validate_email')
mock_validate_email = email_validator_patcher.start()

client = TestClient(app)

def test_auth_flow():
    global db_stores
    # Reset all stores
    for key in db_stores:
        db_stores[key] = []
    
    print("Running test cases for secure authentication...")
    
    # 1. Login with non-existent Gmail user -> should fail with 404
    response = client.post("/api/auth/records", json={
        "mode": "login",
        "email": "nonexistent@gmail.com",
        "password": "Password123!"
    })
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert "Account not found" in response.json()["detail"]
    print("✔ Test 1: Login with non-existent user rejected (404)")

    # 2. Register with non-gmail domain -> should fail with 400
    response = client.post("/api/auth/records", json={
        "mode": "register",
        "email": "testuser@yahoo.com",
        "password": "SecureP@ss123",
        "firstName": "Test",
        "lastName": "User"
    })
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert "Only Gmail addresses" in response.json()["detail"]
    print("✔ Test 2: Yahoo email registration rejected (400)")

    # 3. Register a new user (gmail) -> should succeed with 201, status "pending"
    response = client.post("/api/auth/records", json={
        "mode": "register",
        "email": "testuser@gmail.com",
        "password": "SecureP@ss123",
        "firstName": "Test",
        "lastName": "User"
    })
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["insertedId"] == "pending"
    assert "Verification code sent" in response.json()["message"]
    
    # Verify nothing is in "users" database, but details are in "pending_registrations"
    assert len(db_stores["users"]) == 0
    assert len(db_stores["pending_registrations"]) == 1
    
    pending_record = db_stores["pending_registrations"][0]
    assert pending_record["email"] == "testuser@gmail.com"
    assert pending_record["firstName"] == "Test"
    assert pending_record["lastName"] == "User"
    assert len(pending_record["code"]) == 6
    print("✔ Test 3: Gmail registration initiated (201, pending)")

    # 4. Verify OTP code: invalid code -> fails with 400
    response = client.post("/api/auth/verify", json={
        "email": "testuser@gmail.com",
        "code": "000000"
    })
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert "Invalid or expired" in response.json()["detail"]
    print("✔ Test 4: Verification with wrong code rejected (400)")

    # 5. Verify OTP code: correct code -> succeeds with 200, creates account and profile
    correct_code = pending_record["code"]
    response = client.post("/api/auth/verify", json={
        "email": "testuser@gmail.com",
        "code": correct_code
    })
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "Registration verified" in response.json()["message"]
    
    # Verify user is now in "users" store and pending record is removed
    assert len(db_stores["users"]) == 1
    assert len(db_stores["pending_registrations"]) == 0
    
    registered_doc = db_stores["users"][0]
    assert registered_doc["email"] == "testuser@gmail.com"
    assert "password" not in registered_doc
    assert "password_hash" in registered_doc
    print("✔ Test 5: Registration verified successfully (200) and user created")

    # 6. Login with correct password -> should succeed with 201
    response = client.post("/api/auth/records", json={
        "mode": "login",
        "email": "testuser@gmail.com",
        "password": "SecureP@ss123"
    })
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    print("✔ Test 6: Login with correct password accepted (201)")

    # 7. Login with incorrect password -> should fail with 401
    response = client.post("/api/auth/records", json={
        "mode": "login",
        "email": "testuser@gmail.com",
        "password": "WrongPassword99!"
    })
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert "Incorrect password" in response.json()["detail"]
    print("✔ Test 7: Login with incorrect password rejected (401)")

    # 8. Legacy account migration: user exists in DB but has no password hash
    legacy_doc = {
        "_id": "legacy-id",
        "email": "legacy@gmail.com",
        "first_name": "Legacy",
        "last_name": "Account"
    }
    db_stores["users"].append(legacy_doc)
    
    # Login with legacy account -> should succeed, auto-migrate (hash the password), and store it
    response = client.post("/api/auth/records", json={
        "mode": "login",
        "email": "legacy@gmail.com",
        "password": "NewPassword123!"
    })
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    
    # Verify legacy doc was updated in DB with password_hash and password_salt
    updated_legacy_doc = next(doc for doc in db_stores["users"] if doc["email"] == "legacy@gmail.com")
    assert "password_hash" in updated_legacy_doc
    assert "password_salt" in updated_legacy_doc
    assert verify_password("NewPassword123!", updated_legacy_doc["password_hash"], updated_legacy_doc["password_salt"])
    print("✔ Test 8: Legacy account auto-migrated successfully on first login")

    # 9. Register with weak password -> should fail with 400
    response = client.post("/api/auth/records", json={
        "mode": "register",
        "email": "weakpass@gmail.com",
        "password": "weakpassword",
        "firstName": "Weak",
        "lastName": "Password"
    })
    assert response.status_code == 400
    assert "Password must be at least 10" in response.json()["detail"]
    print("✔ Test 9: Weak password complexity rejected (400)")

    # 10. Register with invalid name characters -> should fail with 400
    response = client.post("/api/auth/records", json={
        "mode": "register",
        "email": "invalidname@gmail.com",
        "password": "SecureP@ss123",
        "firstName": "Ava<script>",
        "lastName": "Smith"
    })
    assert response.status_code == 400
    assert "First name can only contain letters" in response.json()["detail"]
    print("✔ Test 10: Script injection in name rejected (400)")

    print("\nAll corporate registration and secure authentication tests passed successfully!")

if __name__ == "__main__":
    try:
        test_auth_flow()
    finally:
        db_patcher.stop()
        email_validator_patcher.stop()
