# Mamar Bank

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)

One of my early Django projects, built in 2024 while I was learning the framework.

Mamar Bank is a small online banking web application. Customers open an account, deposit and withdraw money, request loans, transfer money to other customers and view a filterable transaction history. Bank staff approve loans through the Django admin. No real money is involved.

## What I practised

- Class-based views (`CreateView`, `ListView`, `FormView`, `LoginView`) and mixins
- Form validation rules (deposit and withdrawal limits, balance checks)
- Extending the built-in `User` with related models (bank account and address)
- Updating balances safely inside database transactions
- Customising the Django admin (loan approval)
- HTML email notifications and environment-based configuration

## Features

- **Account opening**: registration collects personal and address details plus an account type (Savings or Current). It creates a bank account with a generated account number and logs the user in.
- **Profile**: users update their name, email, account and address details, and can change their password (confirmed by email).
- **Deposits**: a minimum of 100 per deposit.
- **Withdrawals**: between 500 and 20,000 per withdrawal, and never more than the current balance.
- **Loans**: users submit loan requests and see them, with their status, on the loan list. Staff approve loans in the Django admin, which credits the amount once and emails the customer. A user can hold at most three approved loans, and approved loans can be repaid from the loan list.
- **Transfers**: send money to another customer, up to the current balance. Both sender and receiver are notified by email. Transfers are blocked when the bank is marked as bankrupt (a flag on the **Bank** record in the admin).
- **Transaction report**: all of a user's transactions, with a date-range filter and the current balance.
- **Email notifications**: deposits, withdrawals, loan requests, loan approvals, transfers and password changes each send an HTML email.

## Tech stack

| | |
| --- | --- |
| Language | Python 3 |
| Framework | Django 4.2 |
| Database | SQLite for local development, PostgreSQL (psycopg2) when configured |
| Configuration | django-environ, dj-database-url |
| Email | Console output locally, SMTP (Gmail) when configured |
| Front end | Django templates, Tailwind CSS 1.x (CDN), `django.contrib.humanize` |

## Project structure

```
mamar-bank/
├── manage.py
├── requirements.txt
├── .env.example
├── mamar_bank/      # settings and root URLconf
├── accounts/        # registration, login, profile; UserBankAccount and UserAddress models
├── transactions/    # deposit, withdraw, loans, transfers, report; admin loan approval
└── core/            # home page, base template, navbar, footer, static images
```

## Getting started

```bash
git clone https://github.com/ratulhasan001/mamar-bank.git
cd mamar-bank

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # optional, for the admin
python manage.py runserver
```

Open http://127.0.0.1:8000/. No configuration file is needed: without one the app uses a local SQLite database (`db.sqlite3`) and prints emails to the terminal. Register customers through the site, because banking features need a bank account (a superuser created with `createsuperuser` has none). To try a transfer, register two customers.

### Configuration (optional)

Settings are read from environment variables or from `mamar_bank/.env` (next to `settings.py`). Copy `.env.example` as a starting point.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key. A development key is used when unset. |
| `DEBUG` | `True` by default. Set to `False` in production. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection. PostgreSQL is used only when `DB_NAME` is set. |
| `EMAIL`, `EMAIL_PASSWORD` | Gmail address and app password for SMTP. Without `EMAIL`, emails are printed to the console. |

## Running the tests

```bash
python manage.py test
```

The tests cover registration, login and logout, deposit and withdrawal limits, loan requests, the loan limit, loan repayment, admin loan approval, transfers (including insufficient balance, transfers to yourself and a bankrupt bank) and a smoke test of the main pages.

## Later improvements

After the original coursework I went back and fixed the following:

- Repaying a loan no longer crashes on a wrong redirect, is POST-only and only works for your own approved loans.
- Transfers no longer crash when no **Bank** record exists (a migration creates it), and they reject zero or negative amounts, amounts above the balance and transfers to yourself.
- Approving a loan in the admin credits the customer once; editing other transactions no longer changes balances.
- Logout is a POST form, which keeps it working on Django 5.
- All banking pages require login (`LoginRequiredMixin` now comes first in the class bases), and users without a bank account get a message instead of an error page.
- The app runs locally with no `.env` (SQLite, console email).
- Small UI fixes: active navigation links, error and info message styles, empty states, page titles and form error display.
- Added an automated test suite.

## Author

Ratul Hasan · [ratulhasan.dev](https://ratulhasan.dev)
