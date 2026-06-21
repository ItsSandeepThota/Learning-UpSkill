import argparse
import os
import sys
import certifi
import dotenv
import pymongo
from datetime import datetime, timezone

# Parse command line arguments
parser = argparse.ArgumentParser(description="Initialize MongoDB collections with validation schemas and indexes.")
parser.add_argument("--empty", action="store_true", help="Do not seed default test users, leave the collections empty.")
args = parser.parse_args()

# Load environment variables from backend/python-api/.env
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
backend_path = os.path.join(project_root, "backend", "python-api")
dotenv.load_dotenv(os.path.join(backend_path, ".env"))

# Ensure backend package can be imported to use our password hashing service
sys.path.insert(0, backend_path)
from app.services.auth import hash_password

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    env_file_path = os.path.join(backend_path, ".env")
    print(f"Error: MONGODB_URI is not set. Tried loading environment variables from: {env_file_path}")
    print("Please make sure the file exists and contains a valid MONGODB_URI string.")
    sys.exit(1)

MONGODB_DB = os.getenv("MONGODB_DB", "BankApplication")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "users")

print(f"Connecting to MongoDB database '{MONGODB_DB}' on cluster...")

client_kwargs = {}
if MONGODB_URI.startswith("mongodb+srv://"):
    client_kwargs.update({"tls": True, "tlsCAFile": certifi.where()})

client = pymongo.MongoClient(MONGODB_URI, **client_kwargs)
db = client[MONGODB_DB]

# Drop old collections to ensure a clean slate
collections_to_drop = ["UserDetails", "user_profiles", "users", "auth_events", "pending_registrations"]
for name in collections_to_drop:
    if name in db.list_collection_names():
        print(f"Dropping collection '{name}'...")
        db.drop_collection(name)

# 1. Schema Validation for 'users' collection
users_validation = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["email", "password_hash", "password_salt"],
        "properties": {
            "email": {
                "bsonType": "string",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                "description": "must be a string and a valid email address"
            },
            "password_hash": {
                "bsonType": "string",
                "pattern": "^[a-fA-F0-9]{64}$",
                "description": "must be a 64-character hex string representing the SHA-256 hash"
            },
            "password_salt": {
                "bsonType": "string",
                "pattern": "^[a-fA-F0-9]{32}$",
                "description": "must be a 32-character hex string representing the salt"
            },
            "firstName": {
                "bsonType": "string",
                "description": "must be a string"
            },
            "lastName": {
                "bsonType": "string",
                "description": "must be a string"
            },
            "user_name": {
                "bsonType": "string",
                "description": "must be a string"
            },
            "account_no": {
                "bsonType": "string",
                "description": "must be a string"
            },
            "csv_no": {
                "bsonType": "int",
                "description": "must be an integer"
            },
            "created_on": {
                "bsonType": "date"
            },
            "modified_on": {
                "bsonType": "string"
            }
        }
    }
}

# 2. Schema Validation for 'user_profiles' collection
profiles_validation = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["email", "name", "balance", "currency"],
        "properties": {
            "email": {
                "bsonType": "string",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                "description": "must be a string and a valid email address"
            },
            "name": {
                "bsonType": "string"
            },
            "balance": {
                "bsonType": "double"
            },
            "currency": {
                "bsonType": "string"
            },
            "cards": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["id", "number", "holder", "expiry", "cvv", "color", "frozen", "limit", "type"],
                    "properties": {
                        "id": { "bsonType": "int" },
                        "number": { "bsonType": "string" },
                        "holder": { "bsonType": "string" },
                        "expiry": { "bsonType": "string" },
                        "cvv": { "bsonType": "string" },
                        "color": { "bsonType": "string" },
                        "frozen": { "bsonType": "bool" },
                        "limit": { "bsonType": "double" },
                        "type": { "bsonType": "string" }
                    }
                }
            },
            "contacts": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["name", "initials", "currency", "flag"],
                    "properties": {
                        "name": { "bsonType": "string" },
                        "initials": { "bsonType": "string" },
                        "avatarUrl": { "bsonType": ["string", "null"] },
                        "currency": { "bsonType": "string" },
                        "flag": { "bsonType": "string" }
                    }
                }
            },
            "transactions": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["id", "title", "subtitle", "amount", "currency", "flag", "time", "status"],
                    "properties": {
                        "id": { "bsonType": "double" },
                        "title": { "bsonType": "string" },
                        "subtitle": { "bsonType": "string" },
                        "amount": { "bsonType": "double" },
                        "currency": { "bsonType": "string" },
                        "flag": { "bsonType": "string" },
                        "time": { "bsonType": "string" },
                        "status": { "bsonType": "string" }
                    }
                }
            }
        }
    }
}

# 3. Schema Validation for 'auth_events' auditing collection
auth_events_validation = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["email", "record_type", "created_on"],
        "properties": {
            "email": {
                "bsonType": "string",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            },
            "record_type": {
                "bsonType": "string",
                "enum": ["login", "register"]
            },
            "created_on": {
                "bsonType": "date"
            },
            "source": {
                "bsonType": "string"
            }
        }
    }
}

# Create collections with validations
print("Creating collection 'users' with JSON Schema validation...")
db.create_collection("users", validator=users_validation)

print("Creating collection 'user_profiles' with JSON Schema validation...")
db.create_collection("user_profiles", validator=profiles_validation)

print("Creating collection 'auth_events' with JSON Schema validation...")
db.create_collection("auth_events", validator=auth_events_validation)

# Create unique indexes
print("Creating unique index on 'email' for 'users'...")
db["users"].create_index([("email", pymongo.ASCENDING)], unique=True)

print("Creating unique index on 'email' for 'user_profiles'...")
db["user_profiles"].create_index([("email", pymongo.ASCENDING)], unique=True)

print("Creating collection 'pending_registrations'...")
db.create_collection("pending_registrations")

print("Creating TTL index on 'created_at' for 'pending_registrations'...")
db["pending_registrations"].create_index([("created_at", pymongo.ASCENDING)], expireAfterSeconds=600)

# Seed Test Users Data
if not args.empty:
    print("Seeding default testing users...")
    seed_users = [
        {
            "email": "demo@example.com",
            "password": "password123",
            "firstName": "Demo",
            "lastName": "User",
            "balance": 5230.50,
            "cards": [
                {
                    "id": 1,
                    "number": "•••• •••• •••• 4821",
                    "holder": "Demo User",
                    "expiry": "12/30",
                    "cvv": "***",
                    "color": "blue",
                    "frozen": False,
                    "limit": 3000.0,
                    "type": "debit"
                },
                {
                    "id": 2,
                    "number": "•••• •••• •••• 8912",
                    "holder": "Demo User",
                    "expiry": "06/28",
                    "cvv": "***",
                    "color": "purple",
                    "frozen": False,
                    "limit": 1000.0,
                    "type": "credit"
                }
            ]
        },
        {
            "email": "jane.doe@example.com",
            "password": "password123",
            "firstName": "Jane",
            "lastName": "Doe",
            "balance": 8750.20,
            "cards": [
                {
                    "id": 1,
                    "number": "•••• •••• •••• 5532",
                    "holder": "Jane Doe",
                    "expiry": "08/31",
                    "cvv": "***",
                    "color": "green",
                    "frozen": False,
                    "limit": 4000.0,
                    "type": "debit"
                }
            ]
        },
        {
            "email": "john.doe@example.com",
            "password": "password123",
            "firstName": "John",
            "lastName": "Doe",
            "balance": 2450.00,
            "cards": [
                {
                    "id": 1,
                    "number": "•••• •••• •••• 9921",
                    "holder": "John Doe",
                    "expiry": "11/29",
                    "cvv": "***",
                    "color": "orange",
                    "frozen": True,
                    "limit": 1500.0,
                    "type": "debit"
                }
            ]
        },
        {
            "email": "shizensusmi@gmail.com",
            "password": "password123",
            "firstName": "Shizen",
            "lastName": "Susmi",
            "balance": 12400.75,
            "cards": [
                {
                    "id": 1,
                    "number": "•••• •••• •••• 7731",
                    "holder": "Shizen Susmi",
                    "expiry": "01/32",
                    "cvv": "***",
                    "color": "blue",
                    "frozen": False,
                    "limit": 5000.0,
                    "type": "debit"
                }
            ]
        }
    ]

    created_at = datetime.now(timezone.utc)

    for seed in seed_users:
        email = seed["email"]
        p_hash, p_salt = hash_password(str(seed["password"]))
        
        # 1. Insert User credentials
        user_doc = {
            "email": email,
            "password_hash": p_hash,
            "password_salt": p_salt,
            "firstName": seed["firstName"],
            "lastName": seed["lastName"],
            "user_name": f"{seed['firstName']} {seed['lastName']}",
            "account_no": f"SB{created_at.strftime('%Y%m%d%H%M%S')}",
            "csv_no": 0,
            "created_on": created_at,
            "modified_on": created_at.isoformat()
        }
        db["users"].insert_one(user_doc)
        print(f"✔ Seeded user account: {email}")

        # 2. Insert User profile
        profile_doc = {
            "email": email,
            "name": f"{seed['firstName']} {seed['lastName']}",
            "balance": seed["balance"],
            "currency": "GHS",
            "cards": seed["cards"],
            "contacts": [
                {
                    "name": "Contact Alpha",
                    "initials": "CA",
                    "avatarUrl": "assets/grace_avatar.png",
                    "currency": "GHS",
                    "flag": "🇬🇭"
                },
                {
                    "name": "Contact Beta",
                    "initials": "CB",
                    "avatarUrl": None,
                    "currency": "GHS",
                    "flag": "🇬🇭"
                }
            ],
            "transactions": [
                {
                    "id": datetime.now().timestamp() - 3600,
                    "title": "Transfer outbound",
                    "subtitle": "To Contact Alpha",
                    "amount": -250.00,
                    "currency": "GHS",
                    "flag": "🇬🇭",
                    "time": "Today, 11:42 AM",
                    "status": "success"
                },
                {
                    "id": datetime.now().timestamp() - 7200,
                    "title": "Salary credit",
                    "subtitle": "Employer deposit",
                    "amount": 3500.00,
                    "currency": "USD",
                    "flag": "🇺🇸",
                    "time": "Yesterday, 09:00 AM",
                    "status": "success"
                }
            ]
        }
        db["user_profiles"].insert_one(profile_doc)
        print(f"✔ Seeded bank profile: {email}")

print("\nDatabase initialization, schema validation setups, indexing, and data seeding completed successfully!")
