# Smart-Contract-Style Conditional Transaction Engine inside an RDBMS

> **Academic Project** — B.Tech Computer Science Engineering | Database Management Systems Course
> VIT University | November 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Technology Stack](#4-technology-stack)
5. [Project Architecture](#5-project-architecture)
6. [Database Schema](#6-database-schema)
7. [ER Diagram](#7-er-diagram)
8. [Transaction Execution Flow](#8-transaction-execution-flow)
9. [ACID Properties Implementation](#9-acid-properties-implementation)
10. [Project Structure](#10-project-structure)
11. [Setup Instructions (Windows)](#11-setup-instructions-windows)
12. [How to Run](#12-how-to-run)
13. [API Documentation](#13-api-documentation)
14. [Test Cases & Expected Results](#14-test-cases--expected-results)
15. [Limitations](#15-limitations)
16. [Future Scope](#16-future-scope)

---

## 1. Introduction

This project implements a **smart-contract-inspired conditional transaction engine** using a traditional Relational Database Management System (RDBMS). Unlike blockchain smart contracts — which require a distributed ledger, gas fees, and consensus mechanisms — this system leverages MySQL's native capabilities:

- **Stored rules (contracts)** that govern when a financial transfer may proceed
- **CHECK constraints** to enforce non-negativity and validity at the schema level
- **`SELECT FOR UPDATE`** pessimistic row-locking to prevent concurrent double-spending
- **ACID-compliant transactions** (`START TRANSACTION` / `COMMIT` / `ROLLBACK`) to guarantee atomicity

The goal is to demonstrate that relational databases can enforce **parametric, auditable, conditional business logic** without any blockchain infrastructure. All contract evaluation happens inside a single Python-managed MySQL transaction, making the system deterministic, testable, and academically rigorous.

---

## 2. Problem Statement

Traditional database transactions execute unconditionally once an authorised user submits them. Real-world financial systems, however, require **parametric rules**:

- A transfer should only proceed if the sender retains a **minimum balance** after the transfer.
- The transfer amount must not exceed a **contract-defined ceiling**.
- The governing contract must be **active** at the time of execution.
- Every outcome — success or rejection — must be **recorded with a reason** for auditability.

These rules must be stored in the database, evaluated atomically within a transaction, and enforced even under concurrent access. This project addresses that gap by building a _contract-aware_ transaction engine on top of MySQL InnoDB.

---

## 3. Objectives

- Store account balances in MySQL with non-negativity constraints (`CHECK (balance >= 0)`)
- Define transfer contracts with parameterised conditions (minimum sender balance, maximum transfer amount, active status)
- Validate transfers against contract rules **inside** a MySQL transaction before any money moves
- Atomically debit the sender and credit the receiver only on successful validation
- Record every outcome (`SUCCESS` or `REJECTED`) with a human-readable reason in the `transactions` table
- Maintain an `audit_logs` table capturing all significant engine events
- Demonstrate all four ACID properties with concrete code references

---

## 4. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | HTML5, CSS3, Vanilla JavaScript, Fetch API | — |
| Backend | Python, Flask | 3.10+, 3.0.3 |
| Database | MySQL (InnoDB storage engine) | 8.0.46 |
| DB Driver | mysql-connector-python | 8.4.0 |
| Config | python-dotenv | latest |
| Testing | Python unittest, pytest | — |

---

## 5. Project Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (HTML/JS)                     │
│    Dashboard | Accounts | Contracts | Transfer | History │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/JSON (Fetch API)
┌───────────────────────▼─────────────────────────────────┐
│                   Flask (app.py)                         │
│         Routes: /api/dashboard, /api/accounts,           │
│                 /api/contracts, /api/transactions        │
└───────────────────────┬─────────────────────────────────┘
                        │ Python function call
┌───────────────────────▼─────────────────────────────────┐
│          Transaction Engine (transaction_engine.py)      │
│   • Input validation                                     │
│   • SELECT FOR UPDATE (row locking)                      │
│   • Contract condition evaluation                        │
│   • Atomic debit + credit + history log                  │
│   • COMMIT or ROLLBACK                                   │
└───────────────────────┬─────────────────────────────────┘
                        │ mysql-connector-python
┌───────────────────────▼─────────────────────────────────┐
│              MySQL 8.0 InnoDB                            │
│   accounts | contracts | contract_conditions             │
│   transactions | audit_logs                              │
└─────────────────────────────────────────────────────────┘
```

**Data flow summary:**
1. The browser sends a JSON `POST /api/transactions` request via the Fetch API.
2. Flask validates the request shape and delegates to `transaction_engine.execute_transfer()`.
3. The engine opens a MySQL transaction, locks the relevant rows, evaluates contract conditions, and either commits (SUCCESS) or rolls back and logs (REJECTED).
4. The JSON result propagates back up to the browser.

---

## 6. Database Schema

### `accounts`

Stores individual account holders and their current balance.

| Column | Type | Constraints |
|--------|------|-------------|
| `account_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` |
| `account_name` | `VARCHAR(100)` | `NOT NULL`, `CHECK (TRIM(account_name) != '')` |
| `balance` | `DECIMAL(12,2)` | `NOT NULL`, `DEFAULT 0.00`, `CHECK (balance >= 0)` |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |

---

### `contracts`

Defines the governing rules for a category of transfers.

| Column | Type | Constraints |
|--------|------|-------------|
| `contract_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` |
| `contract_name` | `VARCHAR(100)` | `NOT NULL` |
| `description` | `TEXT` | nullable |
| `min_sender_balance` | `DECIMAL(12,2)` | `DEFAULT 0.00` |
| `max_transfer_amount` | `DECIMAL(12,2)` | `NOT NULL` |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |

---

### `contract_conditions`

Extensible table for named, typed conditions attached to a contract.

| Column | Type | Constraints |
|--------|------|-------------|
| `condition_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` |
| `contract_id` | `INT` | `NOT NULL`, `FK → contracts(contract_id) ON DELETE CASCADE` |
| `condition_type` | `VARCHAR(50)` | `NOT NULL` (e.g. `MIN_SENDER_BALANCE`, `MAX_TRANSFER_AMOUNT`) |
| `condition_value` | `DECIMAL(12,2)` | nullable |
| `description` | `VARCHAR(255)` | nullable |

---

### `transactions`

Immutable record of every transfer attempt with its outcome.

| Column | Type | Constraints |
|--------|------|-------------|
| `transaction_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` |
| `sender_id` | `INT` | `NOT NULL`, `FK → accounts(account_id)` |
| `receiver_id` | `INT` | `NOT NULL`, `FK → accounts(account_id)` |
| `contract_id` | `INT` | `NOT NULL`, `FK → contracts(contract_id)` |
| `amount` | `DECIMAL(12,2)` | `NOT NULL`, `CHECK (amount > 0)` |
| `status` | `ENUM('PENDING','SUCCESS','REJECTED')` | `NOT NULL`, `DEFAULT 'PENDING'` |
| `message` | `VARCHAR(255)` | nullable — human-readable outcome reason |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |

Additional constraint: `CHECK (sender_id != receiver_id)`

---

### `audit_logs`

Append-only log of all significant engine actions.

| Column | Type | Constraints |
|--------|------|-------------|
| `log_id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` |
| `transaction_id` | `INT` | nullable, `FK → transactions(transaction_id) ON DELETE SET NULL` |
| `action` | `VARCHAR(100)` | `NOT NULL` |
| `details` | `TEXT` | nullable |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |

---

## 7. ER Diagram

```
                        ┌──────────────────────┐
                        │       contracts       │
                        │──────────────────────│
                        │ PK contract_id        │
                        │    contract_name      │
                        │    min_sender_balance │
                        │    max_transfer_amount│
                        │    is_active          │
                        └────────┬─────────────┘
                                 │ 1
                    ┌────────────┤
                    │            │ 1
                    ▼            ▼
      ┌─────────────────┐  ┌──────────────────────┐
      │contract_conditions│  │     transactions      │
      │─────────────────│  │──────────────────────│
      │ PK condition_id │  │ PK transaction_id     │
      │ FK contract_id  │  │ FK sender_id  ──────┐ │
      │    condition_type│  │ FK receiver_id ───┐ │ │
      │    condition_value│  │ FK contract_id    │ │ │
      └─────────────────┘  │    amount           │ │ │
                            │    status           │ │ │
                            │    message          │ │ │
                            └────────┬────────────┘ │ │
                                     │ 1            │ │
                                     ▼              │ │
                        ┌──────────────────────┐   │ │
                        │      audit_logs       │   │ │
                        │──────────────────────│   │ │
                        │ PK log_id             │   │ │
                        │ FK transaction_id     │   │ │
                        │    action             │   │ │
                        │    details            │   │ │
                        └──────────────────────┘   │ │
                                                    │ │
                        ┌──────────────────────┐   │ │
                        │       accounts        │   │ │
                        │──────────────────────│   │ │
                        │ PK account_id  ◄──────────┘ │
                        │    account_name        │ ◄───┘
                        │    balance             │
                        │    created_at          │
                        └──────────────────────┘

Relationships:
  accounts    (1) ──────────< transactions (many)  [via sender_id]
  accounts    (1) ──────────< transactions (many)  [via receiver_id]
  contracts   (1) ──────────< transactions (many)  [via contract_id]
  contracts   (1) ──────────< contract_conditions  (many)
  transactions(1) ──────────< audit_logs           (many)
```

---

## 8. Transaction Execution Flow

```
Client submits transfer request (POST /api/transactions)
        │
        ▼
Flask route receives JSON → validates required fields present
        │
        ▼
transaction_engine.execute_transfer(sender_id, receiver_id,
                                    contract_id, amount) called
        │
        ├── Basic validation (amount > 0, sender_id ≠ receiver_id)
        │         └── Fail → return error immediately (no DB hit)
        │
        ├── START TRANSACTION
        │
        ├── SELECT accounts FOR UPDATE
        │       (locked in ascending account_id order to prevent deadlock)
        │         └── Account not found → ROLLBACK, return error
        │
        ├── SELECT contracts FOR UPDATE
        │         └── Contract not found → ROLLBACK, return error
        │
        ├── Contract condition checks:
        │   ├── is_active = TRUE?         ──► REJECTED if FALSE
        │   ├── amount ≤ max_transfer?    ──► REJECTED if exceeded
        │   ├── sender.balance ≥ amount?  ──► REJECTED if insufficient
        │   └── balance - amount ≥ min_sender_balance?  ──► REJECTED if violated
        │
        ├── [All conditions pass]          [Any condition fails]
        │            │                              │
        ▼            ▼                              ▼
     UPDATE accounts  SET balance -= amount   ROLLBACK
     UPDATE accounts  SET balance += amount   New transaction:
     INSERT transactions (status='SUCCESS')   INSERT transactions (status='REJECTED')
     INSERT audit_logs ('TRANSFER_SUCCESS')   INSERT audit_logs ('TRANSFER_REJECTED')
     COMMIT                                   COMMIT
        │                                              │
        └──────────────────┬───────────────────────────┘
                           ▼
              Return result dict to Flask route
                           │
                           ▼
              JSON response → Browser
```

**Key design decisions:**

| Decision | Reason |
|----------|--------|
| Lock rows in `account_id` order | Prevents deadlock between two concurrent transfers going in opposite directions |
| REJECTED transfers still committed | Provides a complete audit trail without polluting successful-transfer counts |
| Conditions evaluated in Python, not SQL triggers | Easier to test, debug, and extend without stored procedure complexity |

---

## 9. ACID Properties Implementation

### Atomicity

- **What it means**: The sender debit, receiver credit, `transactions` row insert, and `audit_logs` row insert all succeed together — or none of them do.
- **How it is implemented**: All four database writes execute within a single `conn.start_transaction()` … `conn.commit()` block in `transaction_engine.py`. Any exception triggers `conn.rollback()`, leaving the database unchanged.
- **Code reference**: `transaction_engine.py`, `execute_transfer()` function

### Consistency

- **What it means**: The database always transitions from one valid state to another. No account balance goes negative. Foreign key relationships are always satisfied.
- **How it is implemented**:
  - `CHECK (balance >= 0)` on the `accounts` table — enforced by MySQL InnoDB.
  - `CHECK (amount > 0)` and `CHECK (sender_id != receiver_id)` on the `transactions` table.
  - Foreign keys on `transactions.sender_id`, `transactions.receiver_id`, `transactions.contract_id` enforced by InnoDB.
  - Contract conditions evaluated **before** any `UPDATE`, so a rejected transfer never touches balances.
- **Code reference**: `database/schema.sql`

### Isolation

- **What it means**: Two concurrent transfers cannot observe each other's intermediate states, preventing double-spending (e.g. two threads simultaneously draining the same account).
- **How it is implemented**:
  - `SELECT … FOR UPDATE` acquires a pessimistic exclusive lock on the sender and receiver rows at the start of every transfer.
  - Locks are acquired in ascending `account_id` order, eliminating the classic deadlock scenario.
  - MySQL InnoDB default isolation level: **REPEATABLE READ**.
- **Code reference**: `transaction_engine.py`, `SELECT … FOR UPDATE` statements

### Durability

- **What it means**: Once a `COMMIT` returns, the transfer is permanent — even if the MySQL server crashes immediately afterwards.
- **How it is implemented**:
  - MySQL InnoDB writes the redo log synchronously to disk on each `COMMIT` (controlled by `innodb_flush_log_at_trx_commit=1`, the default).
  - No application-level caching layer sits between the engine and the database.
- **Code reference**: MySQL InnoDB default configuration

---

## 10. Project Structure

```
conditional-transaction-engine/
│
├── app.py                      # Flask application factory & route registration
├── transaction_engine.py       # Core conditional transfer logic (ACID)
├── database.py                 # MySQL connection helper (get_connection)
├── config.py                   # Loads .env → Python constants
│
├── routes/
│   ├── accounts.py             # GET/POST /api/accounts
│   ├── contracts.py            # GET/POST /api/contracts, PATCH status
│   └── transactions.py         # POST/GET /api/transactions, stats
│
├── database/
│   ├── schema.sql              # DDL: CREATE TABLE statements + indexes
│   ├── seed.sql                # DML: demo accounts, contracts, conditions
│   └── reset.sql               # Truncate tables and re-seed for demos
│
├── static/
│   ├── css/
│   │   └── style.css           # Dashboard styling
│   └── js/
│       └── app.js              # Fetch API calls, DOM updates
│
├── templates/
│   └── index.html              # Single-page application shell
│
├── tests/
│   ├── test_engine.py          # Unit + integration tests (pytest)
│   └── test_api.py             # Flask test client endpoint tests
│
├── .env.example                # Template — copy to .env and fill in credentials
├── .env                        # Local credentials (git-ignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 11. Setup Instructions (Windows)

### Prerequisites

- Python 3.10 or later (verify: `python --version`)
- MySQL 8.0 Server running locally (verify: `mysql --version`)
- MySQL Workbench _(optional — for visual schema inspection)_
- Git _(optional)_

---

### Step 1: Clone or download the project

```bash
# If using git:
git clone <repo-url>
cd conditional-transaction-engine
```

---

### Step 2: Create and activate the Python virtual environment

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> [!TIP]
> You should see `(venv)` prepended to your prompt once activated.

---

### Step 3: Configure environment variables

```bash
copy .env.example .env
```

Open `.env` in any text editor and set your MySQL credentials:

```dotenv
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=conditional_engine
DB_TEST_NAME=conditional_engine_test
FLASK_SECRET_KEY=academic-project-secret-2024
FLASK_DEBUG=True
```

---

### Step 4: Set up the MySQL database

```bash
# Create database and all tables
mysql -u root -p < database\schema.sql

# Populate with demo accounts and contracts
mysql -u root -p conditional_engine < database\seed.sql
```

After running `seed.sql` the following demo data will exist:

| Account | Balance |
|---------|---------|
| Alice | ₹5,000.00 |
| Bob | ₹2,000.00 |

| Contract | Max Transfer | Min Sender Balance | Status |
|----------|-------------|-------------------|--------|
| Basic Transfer | ₹5,000.00 | ₹500.00 | Active |
| Premium Transfer | ₹50,000.00 | ₹1,000.00 | Active |

---

### Step 5: Verify database connectivity

```bash
python database.py
```

Expected output:
```
Connected to MySQL 8.0.46 — database: conditional_engine
```

---

## 12. How to Run

```bash
# 1. Activate the virtual environment (if not already active)
venv\Scripts\activate

# 2. Start the Flask development server
python app.py

# 3. Open a browser and navigate to:
#    http://localhost:5000
```

The dashboard provides five views:

| View | Purpose |
|------|---------|
| **Dashboard** | Live summary: total accounts, contracts, transfers today |
| **Accounts** | View balances; create new accounts |
| **Contracts** | View, create, and toggle contract status |
| **Transfer** | Submit a conditional transfer |
| **History** | Browse all transaction records with status and reason |

### Reset demo data

```bash
mysql -u root -p conditional_engine < database\reset.sql
```

This truncates all tables (preserving schema) and re-inserts the original seed data.

---

## 13. API Documentation

All endpoints return JSON. Error responses include an `"error"` key.

---

### `GET /api/dashboard`

Returns summary statistics for the dashboard overview.

**Response:**
```json
{
  "total_accounts": 2,
  "total_contracts": 2,
  "transactions_today": 3,
  "successful_today": 2,
  "rejected_today": 1,
  "total_volume_today": "₹2500.00"
}
```

---

### `GET /api/accounts`

Returns all accounts with current balances.

**Response:**
```json
[
  { "account_id": 1, "account_name": "Alice", "balance": "5000.00", "created_at": "2026-11-20T08:00:00" },
  { "account_id": 2, "account_name": "Bob",   "balance": "2000.00", "created_at": "2026-11-20T08:00:00" }
]
```

---

### `POST /api/accounts`

Creates a new account.

**Request body:**
```json
{ "account_name": "Charlie", "initial_balance": 1000.00 }
```

**Response:**
```json
{ "account_id": 3, "account_name": "Charlie", "balance": "1000.00" }
```

---

### `GET /api/accounts/<id>`

Returns a single account by ID.

**Response:** Same shape as a single element from `GET /api/accounts`.

---

### `GET /api/contracts`

Returns all contracts.

**Response:**
```json
[
  {
    "contract_id": 1,
    "contract_name": "Basic Transfer",
    "min_sender_balance": "500.00",
    "max_transfer_amount": "5000.00",
    "is_active": true
  }
]
```

---

### `POST /api/contracts`

Creates a new contract.

**Request body:**
```json
{
  "contract_name": "High Value",
  "description": "For transfers above ₹10,000",
  "min_sender_balance": 2000.00,
  "max_transfer_amount": 100000.00
}
```

**Response:** The newly created contract object including its `contract_id`.

---

### `PATCH /api/contracts/<id>/status`

Activates or deactivates a contract.

**Request body:**
```json
{ "is_active": false }
```

**Response:**
```json
{ "contract_id": 1, "is_active": false }
```

---

### `POST /api/transactions`

Submits a conditional transfer for evaluation and execution.

**Request body:**
```json
{
  "sender_id": 1,
  "receiver_id": 2,
  "contract_id": 1,
  "amount": 1000.00
}
```

**Success response:**
```json
{
  "transaction_id": 5,
  "status": "SUCCESS",
  "message": "Transfer of ₹1000.00 completed successfully",
  "sender_balance_after": "4000.00",
  "receiver_balance_after": "3000.00"
}
```

**Rejected response:**
```json
{
  "transaction_id": 6,
  "status": "REJECTED",
  "message": "Transfer amount exceeds contract limit"
}
```

---

### `GET /api/transactions`

Returns transaction history (most recent first). Supports optional query params: `?limit=50&status=SUCCESS`.

---

### `GET /api/transactions/<id>`

Returns a single transaction with full details including audit log entries.

---

### `GET /api/transactions/stats`

Returns aggregated statistics:

```json
{
  "total": 10,
  "successful": 7,
  "rejected": 3,
  "total_volume": "12500.00",
  "success_rate": 70.0
}
```

---

## 14. Test Cases & Expected Results

> [!NOTE]
> Run with `pytest tests/` after setting up the database. The test suite uses a separate `conditional_engine_test` database defined by `DB_TEST_NAME` in `.env`.

| # | Test | Input | Expected Result |
|---|------|-------|-----------------|
| 1 | Valid transfer | Alice → Bob, ₹1,000 | `SUCCESS`; Alice = ₹4,000; Bob = ₹3,000 |
| 2 | Exceeds contract limit | Alice → Bob, ₹10,000 (limit ₹5,000) | `REJECTED`: Transfer amount exceeds contract limit |
| 3 | Min balance violated | Alice → Bob, ₹4,600 (min balance ₹500) | `REJECTED`: Minimum sender balance condition violated |
| 4 | Insufficient funds | Bob → Alice, ₹3,000 (Bob has ₹2,000) | `REJECTED`: Insufficient balance |
| 5 | Inactive contract | Any transfer, contract `is_active = FALSE` | `REJECTED`: Contract is not active |
| 6 | Same account | Alice → Alice | `REJECTED`: Sender and receiver must differ |
| 7 | Zero amount | amount = 0 | `REJECTED`: Amount must be greater than zero |
| 8 | Negative amount | amount = -500 | `REJECTED`: Amount must be greater than zero |
| 9 | Invalid account | `sender_id = 9999` | `ERROR`: Account does not exist |
| 10 | Invalid contract | `contract_id = 9999` | `ERROR`: Contract does not exist |
| 11 | Atomicity check | Submit a transfer that gets REJECTED | Sender and receiver balances are **unchanged** |
| 12 | Concurrency | 2 threads simultaneously Alice → Bob ₹3,000 | At most 1 `SUCCESS`; balance never goes negative |

---

## 15. Limitations

- **Academic demonstration only** — not suitable for production financial use.
- **Single MySQL instance** — no replication, clustering, or automatic failover.
- **No authentication or authorisation** — any client can read or modify any account.
- **No real-time updates** — the dashboard requires manual page refresh; no WebSockets.
- **Contract condition types are limited** — only `MIN_SENDER_BALANCE` and `MAX_TRANSFER_AMOUNT` are evaluated; no time-based, approval-chain, or multi-party conditions.
- **No multi-currency support** — all amounts are in Indian Rupees (₹).
- **No rate limiting** — the API accepts unlimited requests per second.
- **No connection pooling** — each request opens and closes its own MySQL connection.

---

## 16. Future Scope

| Enhancement | Description |
|-------------|-------------|
| **JWT Authentication** | Add per-account login so only account owners can initiate transfers |
| **Complex contract conditions** | Support time-based windows, multi-party approval, and conditional chains |
| **Database replication** | MySQL read replicas for high availability and horizontal read scaling |
| **WebSocket notifications** | Push real-time transaction status updates to connected browsers |
| **Payment gateway simulation** | Integrate mock gateway APIs for realistic end-to-end academic demos |
| **Query optimisation lab** | Add `EXPLAIN` plan viewer and index recommendation tools |
| **Stored procedure evaluation** | Move contract evaluation into MySQL stored procedures for benchmarking |
| **Contract template library** | Pre-built contract templates for common financial rules |
| **Multi-currency support** | Store currency codes and exchange rates; convert amounts at transfer time |
| **Rate limiting** | Flask-Limiter integration to demonstrate DoS protection |

---

*This project was developed as part of the DBMS course at VIT University. All financial amounts are in Indian Rupees (₹) and are purely illustrative.*
