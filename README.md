# Hot Wallet App Microservices

## Overview

The Hot Wallet App is a microservice-based backend infrastructure for fast, secure blockchain transactions. It enables users to manage wallets and profiles, with private keys securely stored on the server (AES-256 encrypted). The system is designed for high-speed operations, JWT-based authentication, and robust event-driven communication via RabbitMQ.

---

## Architecture

- **Microservices:**
  - **Authentication Service:** Handles registration, login, JWT, password reset, and token management.
  - **User Service:** Manages user profiles and wallets (CRUD, AES-256 encryption for private keys).
  - **Transaction Service:** (not included here) Handles blockchain operations.
  - **Notification Service:** (not included here) Sends emails/notifications on events.
- **API Gateway:** (external) Validates JWT and routes requests.
- **RabbitMQ:** For async event-driven communication.
- **PostgreSQL:** Main database for users and wallets.
- **Redis:** For token blacklisting, rate limiting, and caching.

---

## Features

- OAuth2/JWT authentication with refresh/blacklist/logout
- Secure password hashing (bcrypt)
- AES-256 encryption for wallet private keys
- User profile and wallet CRUD endpoints
- Event-driven (RabbitMQ) for user/wallet actions
- Rate limiting (Redis)
- OpenAPI docs (FastAPI)
- Docker & Kubernetes ready

---

## Technology Stack

- Python 3.11, FastAPI, Pydantic
- SQLAlchemy, PostgreSQL
- Redis, RabbitMQ (aio_pika)
- PyJWT, bcrypt, cryptography
- Docker, Kubernetes

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- (Optional) Kubernetes & kubectl

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Hot-Wallet-App-
```

### 2. Environment Variables
All critical secrets/configs are set via environment variables (see `docker-compose.yml` and `k8s-manifests.yaml`).

- `JWT_SECRET`, `WALLET_AES_KEY`, `POSTGRES_PASSWORD`, etc.
- **Change all default secrets for production!**

### 3. Run with Docker Compose
```bash
docker-compose up --build
```
- Auth Service: http://localhost:8001
- User Service: http://localhost:8002
- RabbitMQ UI: http://localhost:15672 (user: rabbit, pass: rabbit)
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 4. Run on Kubernetes
```bash
kubectl apply -f k8s-manifests.yaml
```
- Update image names in the manifest to your pushed Docker images.

---

## API Usage Examples

### Auth Service
- **Register:**
  ```http
  POST /register
  { "username": "alice", "email": "alice@example.com", "password": "secret" }
  ```
- **Login:**
  ```http
  POST /login
  grant_type=password&username=alice&password=secret
  ```
- **Refresh Token:**
  ```http
  POST /refresh
  { "refresh_token": "..." }
  ```
- **Logout:**
  ```http
  POST /logout
  (Bearer token in Authorization header)
  ```
- **Password Reset:**
  ```http
  POST /password/reset
  { "email": "alice@example.com" }
  ```

### User Service
- **Get Profile:**
  ```http
  GET /users/me
  (Bearer token in Authorization header)
  ```
- **Update Profile:**
  ```http
  PATCH /users/me
  { "username": "newname" }
  ```
- **Add Wallet:**
  ```http
  POST /users/wallets
  { "wallet_name": "MyWallet", "public_key": "...", "encrypted_private_key": "...", "is_default": true }
  ```
- **List Wallets:**
  ```http
  GET /users/wallets
  ```
- **Get Wallet Details:**
  ```http
  GET /users/wallets/{wallet_id}/details
  ```

---

## Security Notes
- **All secrets must be set via environment variables or Kubernetes Secrets.**
- **Never commit real secrets to version control.**
- All API endpoints require JWT (except registration/login/password reset).
- Passwords are hashed with bcrypt; private keys are AES-256 encrypted.
- Use HTTPS in production (behind a reverse proxy or Ingress).

---

## Testing
- Unit tests: `pytest`
- Example: `pytest tests/`
- Add more tests for new endpoints and business logic.

---

## Contributing
- Fork the repo, create a feature branch, and submit a PR.
- Follow code style and add tests for new features.

---

## License
MIT (or your chosen license)