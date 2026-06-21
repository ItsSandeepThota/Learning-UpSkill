# Python Backend

FastAPI service for Shizen Bank.

## Endpoints

- `GET /health`
- `POST /api/auth/records`

## Database

The API is configured to write to the existing connected MongoDB database `BankApplication` and the `UserDetails` collection by default.

Set `MONGODB_URI` to the MongoDB connection you already use. Do not create a new cluster.

## Environment

```bash
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=BankApplication
MONGODB_COLLECTION=UserDetails
CORS_ORIGINS=http://localhost:4200
```
```bash
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=shizen_bank
CORS_ORIGINS=http://localhost:4200
```# Python Backend

This folder contains the Python API service.

Suggested structure:
- `app/api/v1/routes/` for HTTP route handlers
- `app/core/` for config and shared application settings
- `app/db/` for database connection helpers
- `app/models/` for persistence models
- `app/schemas/` for request and response schemas
- `app/services/` for business logic
- `app/utils/` for helper utilities
- `tests/` for automated tests
