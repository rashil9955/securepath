# SecurePath — Fraud Detection Platform

<img width="1443" height="763" alt="SecurePath Dashboard" src="https://github.com/user-attachments/assets/23e4f758-0023-492c-9ff7-c66966b0ec09" />

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **SecurePath** is a full-stack web application that detects fraudulent financial transactions using machine learning. Upload a CSV file of transactions, and the system automatically scores each one for risk and displays the results in an interactive dashboard — protected by mandatory two-factor authentication.

---

## Table of Contents

1. [What does this app do?](#what-does-this-app-do)
2. [How does it work?](#how-does-it-work)
3. [Tech stack](#tech-stack)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Running the app](#running-the-app)
7. [Using the app](#using-the-app)
8. [Security features](#security-features)
9. [API reference](#api-reference)
10. [Project structure](#project-structure)
11. [Common errors and fixes](#common-errors-and-fixes)
12. [Environment variables](#environment-variables)

---

## What does this app do?

Imagine a bank that needs to check thousands of transactions per day for fraud. SecurePath automates that process:

1. You upload a spreadsheet (CSV file) of transactions — things like amount, merchant name, date, and card number.
2. The app runs each transaction through a machine learning model trained to recognize suspicious patterns.
3. Every transaction gets a **risk score** from 0–100 and a label: Low / Medium / High risk.
4. You see everything laid out in a dashboard with charts, and you can approve or reject flagged transactions.
5. You can export a PDF or CSV report of your findings.

**Key features:**

| Feature | Description |
|---|---|
| CSV Upload | Upload a spreadsheet of transactions for bulk analysis |
| ML Fraud Detection | A trained model scores each transaction by risk level |
| Interactive Dashboard | Charts showing risk breakdown, totals, and trends |
| Audit Log | Every action is recorded with a timestamp |
| Report Export | Download results as CSV or PDF |
| User Accounts | Each user only sees their own data |
| Mandatory 2FA | Every account requires Google Authenticator — no exceptions |
| Forgot Password | Reset your password by verifying your authenticator code |
| Change Password | Update your password from within the app at any time |

---

## How does it work?

The app has two main parts that run separately and talk to each other:

```
┌─────────────────────────┐         HTTP requests          ┌──────────────────────────┐
│                         │ ──────────────────────────────► │                          │
│   FRONTEND (React)      │                                 │   BACKEND (Django)       │
│   localhost:3001        │ ◄────────────────────────────── │   localhost:8000         │
│                         │         JSON responses          │                          │
│  What you see in        │                                 │  The brain of the app:   │
│  the browser.           │                                 │  - handles logins        │
│  Buttons, charts,       │                                 │  - runs ML model         │
│  tables, forms.         │                                 │  - reads/writes database │
│                         │                                 │  - enforces 2FA          │
└─────────────────────────┘                                 └──────────────┬───────────┘
                                                                           │
                                                                           │ reads/writes
                                                                           ▼
                                                            ┌──────────────────────────┐
                                                            │   DATABASE (SQLite)      │
                                                            │                          │
                                                            │  Stores users,           │
                                                            │  transactions,           │
                                                            │  audit logs, etc.        │
                                                            └──────────────────────────┘
```

- The **frontend** is the website you look at. Built with React (a JavaScript library).
- The **backend** is the server running in the background. Built with Django (a Python framework). It handles authentication, machine learning, and database queries.
- The **database** stores all the data. In development we use SQLite — just a single file on your computer, no setup needed.

---

## Tech stack

| Technology | What it is | Why we use it |
|---|---|---|
| **Python 3.9+** | Programming language | Runs the backend server and ML model |
| **Django 4.2** | Python web framework | Handles routing, database, and auth |
| **django-ninja** | API library for Django | Lets the frontend talk to backend via HTTP |
| **scikit-learn** | Python ML library | Runs the fraud detection algorithm |
| **PyJWT + bcrypt** | Auth libraries | Secure login tokens and password hashing |
| **pyotp + cryptography** | 2FA libraries | TOTP code generation, Fernet secret encryption |
| **React 18** | JavaScript UI library | Builds the interactive frontend |
| **TailwindCSS** | CSS styling library | Styling without writing much CSS |
| **SQLite** | Lightweight database | Stores data locally (no server setup needed) |

---

## Prerequisites

Before running this project, install the following tools.

### 1. Python 3.9 or newer

```bash
python3 --version
```

If not installed, download from [python.org](https://www.python.org/downloads/).

### 2. Node.js and npm

```bash
node --version
npm --version
```

If not installed:

**Mac (using Homebrew):**
```bash
# Install Homebrew first if you don't have it:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install Node:
brew install node
```

**Windows:** Download the installer from [nodejs.org](https://nodejs.org/).

### 3. Git

```bash
git --version
```

Mac usually has it pre-installed. If not: `brew install git`.

### 4. Google Authenticator (on your phone)

Every account requires 2FA. Install one of these before signing up:
- [Google Authenticator](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2) — Android / iOS
- [Authy](https://authy.com/) — multi-device, backup support (recommended)

---

## Installation

### Step 1: Download the project

```bash
git clone https://github.com/your-username/securepath.git
cd securepath
```

### Step 2: Set up the backend

```bash
cd backend
```

**Create a virtual environment** (an isolated Python sandbox for this project):
```bash
python3 -m venv venv
```

**Activate it:**
```bash
# Mac / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

Your terminal prompt will show `(venv)` when it's active.

**Install Python packages:**
```bash
pip install -r requirements.txt
```

**Create the configuration file:**
```bash
cp MONOREPO_ENV_EXAMPLE .env
```

**Create the logs folder:**
```bash
mkdir -p logs
```

**Set up the database:**
```bash
python3 manage.py migrate
```

You'll see a list of `OK` messages — that means all the database tables were created successfully.

### Step 3: Set up the frontend

Open a **new terminal tab** (keep the backend terminal open).

```bash
cd securepath/frontend
npm install
```

---

## Running the app

You need **two terminals open at the same time** — one for the backend, one for the frontend.

### Terminal 1 — Backend

```bash
cd securepath/backend
source venv/bin/activate        # Windows: venv\Scripts\activate
python3 manage.py runserver
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

**Keep this terminal open.** If you close it, the backend stops.

### Terminal 2 — Frontend

```bash
cd securepath/frontend
npm start
```

Your browser will open automatically at `http://localhost:3001`.

> **Why port 3001?** If port 3000 is already in use, the frontend automatically picks the next available port. That's fine.

### URLs at a glance

| Service | URL | Description |
|---|---|---|
| App (frontend) | http://localhost:3001 | The website you interact with |
| Backend API | http://localhost:8000/api | The data server |
| API docs | http://localhost:8000/api/docs | Interactive API explorer |
| Django admin | http://localhost:8000/admin | Database admin panel |

---

## Using the app

### 1. Create an account (3-step process)

Go to `http://localhost:3001/register`.

**Step 1 — Account details:**
Enter your email and a password (at least 8 characters). Click **Continue**.

**Step 2 — Set up Authenticator:**
A QR code appears. Open Google Authenticator on your phone, tap the **+** button, and scan the code. Once scanned, your app will show a 6-digit code that refreshes every 30 seconds. Type that code into the box and click **Verify**.

> **Can't scan the QR code?** Tap "Enter a setup key" in Google Authenticator and type the manual key shown under the QR code.

**Step 3 — Save your backup codes:**
You receive 8 backup codes. **Write these down and store them somewhere safe** — they're the only way to access your account if you lose your phone. Check the box confirming you've saved them, then click **Go to Dashboard**.

### 2. Log in

Go to `http://localhost:3001/login`.

**Step 1:** Enter your email and password → click **Sign In**.

**Step 2:** Open Google Authenticator and enter the current 6-digit code → click **Verify & Sign In**.

### 3. Upload transactions

Click **Upload** in the left sidebar. Drag and drop a CSV file onto the upload area.

**What should the CSV look like?** Sample files are in the `test_data/` folder. Required columns:
```
transaction_id, amount, date, merchant, card_number
```

### 4. Run fraud detection

Click **Risk Scoring** in the sidebar. The ML model assigns each transaction a risk score (0–100) and flags suspicious ones.

### 5. Review the dashboard

Click **Dashboard** to see:
- Total transactions uploaded
- How many are high / medium / low risk
- Charts showing the risk breakdown
- A table of flagged transactions you can approve or reject

### 6. Export a report

Click **Report Export** and choose CSV or PDF to download your results.

---

## Security features

### Two-Factor Authentication (2FA)

2FA is **mandatory** — every account must set it up during registration. After entering your password at login, you enter a 6-digit code from Google Authenticator. Even if someone steals your password, they can't log in without your phone.

You can manage 2FA from the **profile dropdown** (click your avatar in the top-right corner):
- **Two-Factor Auth** → view status, disable/re-enable, regenerate backup codes
- **Change Password** → update your password without logging out

### Forgot your password?

Go to `http://localhost:3001/forgot-password` or click **Forgot your password?** on the login page.

**Step 1 — Verify your identity:**
Enter your email + the current 6-digit code from Google Authenticator. This proves you own the account without needing an email link.

**Step 2 — Set a new password:**
Enter and confirm your new password. All existing sessions are signed out for security.

**Step 3 — Done:**
Log in with your new password.

> **This requires 2FA to be active.** Since 2FA is mandatory for all accounts, everyone can use this feature.

### Change password while logged in

Open the profile dropdown (top-right avatar) → **Change Password**.

You'll need:
- Your current password
- Your 6-digit authenticator code
- The new password (typed twice)

Your current session stays active after the change.

### Backup codes

When you set up 2FA, you receive 8 backup codes in the format `XXXXX-XXXXX`. Each code can be used once to log in if you don't have your phone. Store them in a password manager or printed somewhere secure.

To get a fresh set, go to the profile dropdown → **Two-Factor Auth** → **Regenerate backup codes** (requires your current OTP).

### Session security

- Access tokens expire after 30 minutes; refresh tokens after 7 days.
- All tokens are invalidated when you change your password via the forgot-password flow.
- Brute-force protection: after 5 failed OTP attempts, the account is locked for 15 minutes.
- TOTP secrets are stored encrypted in the database using Fernet symmetric encryption.

---

## API reference

The backend exposes a REST API at `http://localhost:8000/api/`. You can explore it interactively at `http://localhost:8000/api/docs`.

Most endpoints require a `Bearer` token in the `Authorization` header:
```
Authorization: Bearer <your_access_token>
```

### Authentication

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | No | Create a new account |
| `POST` | `/api/auth/login` | No | Log in with email + password |
| `POST` | `/api/auth/logout` | No | Log out, revoke tokens |
| `GET` | `/api/auth/me` | Yes | Get current user info |
| `POST` | `/api/auth/refresh` | No | Get a new access token using refresh token |
| `POST` | `/api/auth/change-password` | Yes | Change password (current password + OTP required) |
| `POST` | `/api/auth/forgot-password/verify` | No | Verify identity via email + TOTP → returns reset token |
| `POST` | `/api/auth/forgot-password/reset` | No | Set new password using the reset token |

### Two-Factor Authentication

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| `POST` | `/api/2fa/setup` | Yes | Generate QR code + manual key for authenticator app |
| `POST` | `/api/2fa/enable` | Yes | Verify first OTP, activate 2FA, receive backup codes |
| `POST` | `/api/2fa/login-verify` | No | Submit OTP during login to get full access tokens |
| `GET` | `/api/2fa/status` | Yes | Check if 2FA is on and backup codes remaining |
| `POST` | `/api/2fa/disable` | Yes | Turn off 2FA (requires password + OTP) |
| `POST` | `/api/2fa/backup-codes/regenerate` | Yes | Generate a new set of backup codes (requires OTP) |

### Transactions & Analysis

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| `POST` | `/api/upload` | Yes | Upload a CSV file of transactions |
| `POST` | `/api/detect-fraud` | Yes | Run fraud detection on uploaded transactions |
| `GET` | `/api/dashboard/transactions` | Yes | List transactions with pagination |
| `POST` | `/api/decision` | Yes | Approve or reject a flagged transaction |
| `GET` | `/api/dashboard/stats` | Yes | Get summary statistics |
| `GET` | `/api/export/csv` | Yes | Download results as CSV |
| `GET` | `/api/export/pdf` | Yes | Download results as PDF |

---

## Project structure

```
securepath/
│
├── backend/                        ← Python / Django server
│   ├── manage.py                   ← Django's command-line tool
│   ├── requirements.txt            ← Python packages to install
│   ├── .env                        ← Your local config (never commit this)
│   ├── logs/                       ← Log files written by the server
│   │
│   ├── backend/                    ← Django project settings
│   │   ├── settings_base.py        ← Shared settings for all environments
│   │   ├── settings_dev.py         ← Development-only settings (DEBUG, hardcoded dev keys)
│   │   ├── settings_prod.py        ← Production settings
│   │   └── urls.py                 ← Maps URLs to the router
│   │
│   └── api/                        ← Main Django app (all logic lives here)
│       ├── models.py               ← Database tables (User, Transaction, RefreshToken, etc.)
│       ├── router_v1.py            ← All API endpoints
│       ├── schemas.py              ← Request/response data shapes (Pydantic)
│       ├── jwt_auth.py             ← JWT token creation, verification, password hashing
│       ├── totp_auth.py            ← 2FA logic: QR codes, OTP verification, backup codes
│       ├── auth.py                 ← Auth middleware (bearer token extraction)
│       ├── fraud_detection.py      ← Machine learning fraud scoring
│       ├── reports.py              ← CSV / PDF report generation
│       └── migrations/             ← Database migration files (auto-generated)
│
├── frontend/                       ← React / JavaScript website
│   ├── package.json                ← JavaScript packages to install
│   └── src/
│       ├── App.js                  ← Root component, routing, profile dropdown
│       ├── pages/
│       │   ├── LoginPage.jsx       ← Email+password → 2FA OTP two-step login
│       │   ├── RegisterPage.jsx    ← Three-step signup: account → QR code → backup codes
│       │   └── ForgotPasswordPage.jsx  ← Email + TOTP → new password flow
│       ├── components/
│       │   ├── TwoFAModal.jsx      ← Manage 2FA from profile dropdown
│       │   ├── ChangePasswordModal.jsx  ← Change password while logged in
│       │   ├── ProtectedRoute.jsx  ← Redirects unauthenticated users to login
│       │   ├── Dashboard/          ← Dashboard charts and stats
│       │   ├── Upload/             ← CSV upload view
│       │   ├── RiskScoring/        ← Fraud detection trigger view
│       │   ├── AuditLog/           ← Audit log view
│       │   ├── Reports/            ← Report export view
│       │   ├── DataCleansing/      ← Data cleansing view
│       │   └── Shared/Sidebar.js   ← Left navigation sidebar
│       ├── contexts/
│       │   └── AuthContext.jsx     ← Global auth state (login, logout, verify2FA)
│       ├── services/
│       │   └── authService.js      ← All API calls (auth, 2FA, password management)
│       └── config/
│           └── constants.js        ← Frontend config (API base URL)
│
└── test_data/                      ← Sample CSV files to test uploads
```

---

## Common errors and fixes

### "command not found: python"

On macOS, the command is `python3`, not `python`. Use `python3` everywhere.

### "source: no such file or directory: venv/bin/activate"

You're not in the `backend/` folder, or the virtual environment doesn't exist yet:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### "ModuleNotFoundError: No module named 'django'"

The virtual environment isn't activated:
```bash
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows
```

### "FileNotFoundError: logs/django.log"

The logs directory is missing. Create it:
```bash
mkdir -p backend/logs
```

### "Failed to fetch" on login or register page

The backend is not running. In a terminal:
```bash
cd backend
source venv/bin/activate
python3 manage.py runserver
```

### "Server Error (500): Failed to parse JSON response" on register

The Django server may need to be restarted after setup. Press `Ctrl+C` in the backend terminal and run `python3 manage.py runserver` again.

### "You have N unapplied migration(s)"

The database is out of date:
```bash
cd backend
source venv/bin/activate
python3 manage.py migrate
```

### Port 3000 is already in use

The frontend automatically tries port 3001. If the browser doesn't open, go to `http://localhost:3001` manually.

### "Verification failed" on forgot-password page

Make sure the account you're using completed the full 3-step registration (including scanning the QR code and saving backup codes). Accounts that were registered when 2FA setup was broken may not have a valid TOTP secret — create a new account in that case.

### "No account with 2FA found for that email"

The email doesn't match any account that has 2FA active. Double-check the email address.

---

## Environment variables

The `.env` file in `backend/` controls how the app is configured. Copy it from the example with `cp MONOREPO_ENV_EXAMPLE .env`.

```env
# ── Django core ──────────────────────────────────────────────────────────────

# SECRET_KEY: A long random string Django uses to sign cookies and tokens.
# Generate a new one for production:
#   python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=your-secret-key-change-this-to-a-random-string

# DEBUG: True in development (shows full error pages). Always False in production.
DEBUG=True

# ALLOWED_HOSTS: Which domain names Django will respond to.
ALLOWED_HOSTS=localhost,127.0.0.1


# ── Database ─────────────────────────────────────────────────────────────────

# SQLite is used by default (just a file — no database server needed):
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# For production, switch to PostgreSQL:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=securepath_db
# DB_USER=your_db_user
# DB_PASSWORD=your_db_password
# DB_HOST=localhost
# DB_PORT=5432


# ── JWT authentication ────────────────────────────────────────────────────────

# Secret used to sign login tokens. Keep this private.
JWT_SECRET_KEY=your-jwt-secret-key

# How long access tokens last (minutes). Default: 30.
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# How long refresh tokens last (days). Default: 7.
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7


# ── 2FA / TOTP ───────────────────────────────────────────────────────────────

# Fernet symmetric encryption key for storing TOTP secrets in the database.
# A development key is hardcoded in settings_dev.py so you don't need this for dev.
# For production, generate your own:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOTP_ENCRYPTION_KEY=


# ── Plaid (optional — bank account connection) ───────────────────────────────

# Get free sandbox keys at https://dashboard.plaid.com/
# Leave blank to skip (everything else still works without this).
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox


# ── API token ─────────────────────────────────────────────────────────────────

# Shared secret used by some internal endpoints.
API_TOKEN=your-secure-api-token-change-this


# ── Celery + Redis (optional — background tasks) ──────────────────────────────

# Celery runs ML jobs in the background so the UI doesn't freeze.
# Requires Redis. Skip for basic development usage.
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## About

Built as an academic capstone project at SDSU by a team of 6 students, bridging machine learning and full-stack web development. The project demonstrates end-to-end ML integration — from raw CSV ingestion through risk scoring to interactive visualization and secure authentication with mandatory TOTP-based two-factor auth.
