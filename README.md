# SecurePath — Fraud Detection Platform

<img width="1443" height="763" alt="SecurePath Dashboard" src="https://github.com/user-attachments/assets/23e4f758-0023-492c-9ff7-c66966b0ec09" />

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **SecurePath** is a full-stack web application that detects fraudulent financial transactions using machine learning. Upload a CSV file of transactions, and the system automatically scores each one for risk and displays the results in an interactive dashboard.

---

## Table of Contents

1. [What does this app do?](#what-does-this-app-do)
2. [How does it work? (Big picture)](#how-does-it-work-big-picture)
3. [Tech stack explained](#tech-stack-explained)
4. [Prerequisites — things to install first](#prerequisites--things-to-install-first)
5. [Installation — step by step](#installation--step-by-step)
6. [Running the app](#running-the-app)
7. [Using the app](#using-the-app)
8. [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
9. [API reference](#api-reference)
10. [Project structure](#project-structure)
11. [Common errors and fixes](#common-errors-and-fixes)
12. [Environment variables explained](#environment-variables-explained)

---

## What does this app do?

Imagine a bank that needs to check thousands of transactions per day for fraud. SecurePath automates that process:

1. You upload a spreadsheet (CSV file) of transactions — things like the amount, merchant name, date, and card number.
2. The app runs each transaction through a machine learning model that was trained to recognize suspicious patterns.
3. Every transaction gets a **risk score** from 0–100 and a label: Low / Medium / High risk.
4. You see everything laid out in a dashboard with charts, and you can approve or reject flagged transactions.
5. You can export a PDF or CSV report of your findings.

**Key features:**

| Feature | What it does |
|---|---|
| CSV Upload | Upload a spreadsheet of transactions for bulk analysis |
| ML Fraud Detection | A trained model scores each transaction by risk level |
| Interactive Dashboard | Charts showing risk breakdown, totals, and trends |
| Audit Log | Every action is recorded with a timestamp |
| Report Export | Download results as CSV or PDF |
| User Accounts | Each user only sees their own data |
| Two-Factor Auth (2FA) | Optional extra login security via Google Authenticator |
| Bank Connection | Connect a real bank account via Plaid (requires API keys) |

---

## How does it work? (Big picture)

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
│                         │                                 │  - sends back results    │
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

**In plain English:**
- The **frontend** is the website you look at. It's built with React (a JavaScript library).
- The **backend** is the server running in the background. It's built with Django (a Python framework). It does all the heavy lifting — authentication, machine learning, database queries.
- The **database** stores all the data. In development we use SQLite, which is just a single file on your computer — no setup needed.

---

## Tech stack explained

You don't need to be an expert in any of these, but it helps to know what they are:

| Technology | What it is | Why we use it |
|---|---|---|
| **Python** | Programming language | Runs the backend server and ML model |
| **Django** | Python web framework | Handles URL routing, database, and authentication |
| **django-ninja** | API library for Django | Lets the frontend talk to the backend via HTTP |
| **scikit-learn** | Python ML library | Runs the fraud detection algorithm |
| **React** | JavaScript UI library | Builds the interactive frontend |
| **TailwindCSS** | CSS styling library | Makes things look nice without writing much CSS |
| **SQLite** | Lightweight database | Stores data locally (no server setup needed for dev) |
| **JWT** | JSON Web Tokens | Keeps users logged in securely |

---

## Prerequisites — things to install first

Before you can run this project, you need to install a few programs. Think of these as tools you need before you can build something.

### 1. Python 3.9 or newer

Python runs the backend. Check if you have it:

```bash
python3 --version
```

If you see `Python 3.9.x` or higher, you're good. If not, download it from [python.org](https://www.python.org/downloads/).

### 2. Node.js and npm

Node.js runs the frontend. npm is its package manager (like pip, but for JavaScript).

Check if you have them:

```bash
node --version
npm --version
```

If either command says "command not found", install them:

**Mac (using Homebrew):**
```bash
# First install Homebrew if you don't have it:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then add it to your PATH (copy the eval line Homebrew prints at the end):
eval "$(/opt/homebrew/bin/brew shellenv zsh)"

# Then install Node:
brew install node
```

**Windows:** Download the installer from [nodejs.org](https://nodejs.org/).

### 3. Git

Git lets you download (clone) this project. Check:

```bash
git --version
```

Mac usually has it pre-installed. If not, install it with `brew install git`.

---

## Installation — step by step

### Step 1: Download the project

Open your terminal and run:

```bash
git clone https://github.com/your-username/securepath.git
cd securepath
```

> **What is a terminal?** On Mac, press `Cmd + Space`, type "Terminal", and press Enter. On Windows, search for "Command Prompt" or "PowerShell".

### Step 2: Set up the backend

The backend is a Python project. We'll create an isolated environment for it (called a virtual environment) so its packages don't conflict with anything else on your computer.

```bash
cd backend
```

**Create a virtual environment:**
```bash
python3 -m venv venv
```
> This creates a folder called `venv` inside `backend/`. Think of it as a clean Python sandbox just for this project.

**Activate it:**
```bash
# Mac / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```
> Your terminal prompt will change to show `(venv)` at the start. That means it worked.

**Install Python packages:**
```bash
pip install -r requirements.txt
```
> This reads `requirements.txt` and installs everything the project needs. It will take a few minutes.

**Create the configuration file:**
```bash
cp MONOREPO_ENV_EXAMPLE .env
```
> This copies the example configuration file to `.env`. The app reads settings from this file.

**Create the logs folder** (the app writes logs here):
```bash
mkdir -p logs
```

**Set up the database:**
```bash
python manage.py migrate
```
> This creates all the database tables the app needs. You'll see a list of "OK" messages.

### Step 3: Set up the frontend

Open a **new terminal tab/window** (keep the backend terminal open).

```bash
cd securepath/frontend   # navigate back to the frontend folder
npm install
```
> This downloads all the JavaScript packages the frontend needs. It may take a minute.

---

## Running the app

You need **two terminals open at the same time** — one for the backend, one for the frontend.

### Terminal 1 — Start the backend

```bash
cd securepath/backend
source venv/bin/activate    # Windows: venv\Scripts\activate
python manage.py runserver
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

**Keep this terminal open.** If you close it, the backend stops and the app breaks.

### Terminal 2 — Start the frontend

```bash
cd securepath/frontend
npm start
```

Your browser will open automatically at `http://localhost:3001`.

> **Why 3001 instead of 3000?** If port 3000 is already used by something else, the frontend picks the next available port (3001). That's fine.

### What you should see

| Service | URL | What it is |
|---|---|---|
| Frontend (the website) | http://localhost:3001 | The app you interact with |
| Backend API | http://localhost:8000/api | The data server (you don't visit this directly) |
| Django admin panel | http://localhost:8000/admin | Database admin interface |

---

## Using the app

### 1. Create an account

Go to `http://localhost:3001/register` and sign up with any email and password (minimum 8 characters). This creates an account stored in your local database.

### 2. Log in

Go to `http://localhost:3001/login` and sign in with the account you just created.

### 3. Upload transactions

Click **Upload** in the left sidebar. Drag and drop a CSV file onto the upload area, or click to browse.

**What should the CSV look like?** Each row is one transaction. Sample files are in the `test_data/` folder at the root of the project. Use one of those to try it out.

Required columns:
```
transaction_id, amount, date, merchant, card_number
```

### 4. Run fraud detection

After uploading, click **Risk Scoring** in the sidebar to score your transactions. The ML model will assign each transaction a risk score and flag suspicious ones.

### 5. Review the dashboard

Click **Dashboard** to see:
- Total transactions
- How many are high / medium / low risk
- Charts showing the breakdown
- A table of flagged transactions you can approve or reject

### 6. Export a report

Click **Report Export** and choose CSV or PDF to download your results.

---

## Two-Factor Authentication (2FA)

2FA adds a second layer of security to your login. After entering your password, you also enter a 6-digit code from an app on your phone (like Google Authenticator). Even if someone steals your password, they can't log in without your phone.

### How to enable 2FA

**Step 1:** Install an authenticator app on your phone:
- [Google Authenticator](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2) (Android / iOS)
- [Authy](https://authy.com/) (more features, recommended)

**Step 2:** Call the setup endpoint to get a QR code:
```bash
curl -X POST http://localhost:8000/api/2fa/setup \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
The response includes a `qr_code` (base64 image) and a `manual_key`.

**Step 3:** Scan the QR code in your authenticator app. Or, if scanning doesn't work, tap "Enter code manually" in the app and type the `manual_key`.

**Step 4:** Enable 2FA by verifying the first code:
```bash
curl -X POST http://localhost:8000/api/2fa/enable \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'    # replace with the 6-digit code from your app
```
The response gives you **8 backup codes**. Write these down and store them somewhere safe. If you lose your phone, these are the only way to get back into your account.

### Logging in with 2FA enabled

```
Step 1: POST /auth/login with email + password
        → server responds with {"requires_2fa": true, "two_fa_token": "..."}

Step 2: POST /2fa/login-verify with the two_fa_token + your 6-digit OTP
        → server responds with your normal access token
```

### 2FA endpoint reference

| Endpoint | Method | What it does |
|---|---|---|
| `/api/2fa/setup` | POST | Get QR code to scan with authenticator app |
| `/api/2fa/enable` | POST | Confirm setup with first OTP, receive backup codes |
| `/api/2fa/login-verify` | POST | Submit OTP during login to get full access |
| `/api/2fa/status` | GET | Check if 2FA is on and how many backup codes remain |
| `/api/2fa/disable` | POST | Turn off 2FA (requires password + OTP) |
| `/api/2fa/backup-codes/regenerate` | POST | Get a fresh set of backup codes (requires OTP) |

---

## API reference

The backend exposes a REST API at `http://localhost:8000/api/`. You can explore it interactively at `http://localhost:8000/api/docs`.

Most endpoints require a `Bearer` token in the `Authorization` header:
```
Authorization: Bearer <your_access_token>
```
You get this token when you log in.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create a new account |
| `POST` | `/api/auth/login` | Log in, receive tokens |
| `POST` | `/api/auth/logout` | Log out, revoke tokens |
| `GET` | `/api/auth/me` | Get current user info |
| `POST` | `/api/auth/refresh` | Get a new access token using refresh token |

### Transactions & Analysis

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a CSV file of transactions |
| `POST` | `/api/detect-fraud` | Run fraud detection on uploaded transactions |
| `GET` | `/api/transactions` | List all transactions |
| `POST` | `/api/decision` | Approve or reject a flagged transaction |
| `GET` | `/api/dashboard/stats` | Get summary statistics |
| `GET` | `/api/export/{csv\|pdf}` | Download a report |

---

## Project structure

```
securepath/
│
├── backend/                   ← Python / Django server
│   ├── manage.py              ← Django's command-line tool (run migrations, start server, etc.)
│   ├── requirements.txt       ← List of Python packages to install
│   ├── .env                   ← Your local config (never commit this to git)
│   ├── logs/                  ← Log files written by the server
│   │
│   ├── backend/               ← Django project settings
│   │   ├── settings_base.py   ← Base settings shared across environments
│   │   ├── settings_dev.py    ← Extra settings for development
│   │   ├── settings_prod.py   ← Extra settings for production
│   │   └── urls.py            ← Maps URLs to the router
│   │
│   └── api/                   ← The main Django app (all the logic lives here)
│       ├── models.py          ← Database table definitions (User, Transaction, etc.)
│       ├── router_v1.py       ← All API endpoints (register, login, upload, 2FA, etc.)
│       ├── schemas.py         ← Defines the shape of request/response data
│       ├── jwt_auth.py        ← JWT token creation and verification
│       ├── totp_auth.py       ← 2FA / TOTP logic (QR codes, OTP verification, backup codes)
│       ├── auth.py            ← Authentication middleware
│       ├── fraud_detection.py ← Machine learning fraud scoring
│       ├── reports.py         ← CSV / PDF report generation
│       └── migrations/        ← Database migration files (auto-generated, don't edit manually)
│
├── frontend/                  ← React / JavaScript website
│   ├── package.json           ← List of JavaScript packages to install
│   ├── src/
│   │   ├── App.js             ← Root component, sets up page routing
│   │   ├── api.js             ← Functions that talk to the backend
│   │   ├── services/          ← Authentication and API service helpers
│   │   ├── components/        ← Reusable UI pieces (Dashboard, Upload, AuditLog, etc.)
│   │   └── config/
│   │       └── constants.js   ← Frontend config (API base URL, etc.)
│   └── public/                ← Static files (favicon, index.html)
│
├── test_data/                 ← Sample CSV files you can upload to test the app
├── setup.sh                   ← Automated setup script (alternative to manual steps)
└── QUICK_START.md             ← Very short version of this guide
```

---

## Common errors and fixes

### "command not found: python"

On macOS, the command is `python3`, not `python`. Either type `python3` instead, or add this to your shell config:
```bash
alias python=python3
```

### "source: no such file or directory: venv/bin/activate"

You're not in the `backend/` folder, or you haven't created the virtual environment yet. Run:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### "ModuleNotFoundError: No module named 'django'"

The virtual environment isn't activated. Run:
```bash
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows
```
Then try your command again.

### "FileNotFoundError: logs/django.log"

The logs directory doesn't exist yet. Create it:
```bash
mkdir -p backend/logs
```

### "Failed to fetch" on the login or register page

The backend is not running. Open a terminal, navigate to the `backend/` folder, activate the virtual environment, and run:
```bash
python manage.py runserver
```

### "Module not found: Error: Can't resolve 'lucide-react'"

A frontend dependency is missing. Run:
```bash
cd frontend
npm install lucide-react
```

### "You have N unapplied migration(s)"

The database is out of date. Run:
```bash
cd backend
source venv/bin/activate
python manage.py migrate
```

### Port 3000 is already in use

The frontend will automatically try port 3001. If the browser doesn't open, go to `http://localhost:3001` manually.

### "ValueError: Unable to configure handler 'file'"

The `logs/` directory doesn't exist. Fix:
```bash
mkdir -p backend/logs
```

---

## Environment variables explained

The `.env` file controls how the app is configured. Here is what each variable does:

```env
# ── Django core ────────────────────────────────────────────────────────────

# SECRET_KEY: A long random string Django uses to sign cookies and tokens.
# In development the default value is fine. In production, generate a new one:
#   python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=your-secret-key-change-this-to-a-random-string

# DEBUG: Set to True in development so you see full error pages.
# ALWAYS set to False in production.
DEBUG=True

# DJANGO_ENV: Controls which settings file is loaded (development or production).
DJANGO_ENV=development

# ALLOWED_HOSTS: Which domain names Django will respond to.
ALLOWED_HOSTS=localhost,127.0.0.1


# ── Database ───────────────────────────────────────────────────────────────

# For local development, use SQLite (a single file — no server needed):
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# For production, switch to PostgreSQL (uncomment and fill in):
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=securepath_db
# DB_USER=your_db_user
# DB_PASSWORD=your_db_password
# DB_HOST=localhost
# DB_PORT=5432


# ── API token ──────────────────────────────────────────────────────────────

# A shared secret used by some legacy endpoints. Change it to something random.
API_TOKEN=your-secure-api-token-change-this


# ── JWT authentication ─────────────────────────────────────────────────────

# Secret used to sign login tokens. Must stay private.
JWT_SECRET_KEY=your-jwt-secret-key

# How long access tokens last (minutes). Default: 30 minutes.
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# How long refresh tokens last (days). Default: 7 days.
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7


# ── 2FA / TOTP ─────────────────────────────────────────────────────────────

# Encryption key for storing TOTP secrets securely.
# Generate one with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOTP_ENCRYPTION_KEY=your-generated-fernet-key


# ── Plaid (optional — for bank account connection) ─────────────────────────

# Get free sandbox keys at https://dashboard.plaid.com/
# Leave blank to skip bank connection (everything else still works).
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox


# ── Celery + Redis (optional — for background tasks) ──────────────────────

# Celery runs ML jobs in the background so the UI doesn't freeze.
# Requires Redis to be installed and running. Skip for basic usage.
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## About

Built as an academic capstone project at SDSU by a team of 6 students, bridging machine learning and full-stack web development. The project demonstrates end-to-end ML integration — from raw CSV ingestion through risk scoring to interactive visualization and secure authentication.




8f46f-a8ae7
07ad3-1f13d
d8ad9-f7a33
65c34-c7133
8b029-7dda1
9644c-88235
7116c-a805c
3a4d1-b9285
