# Mamar Bank

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)

Mamar Bank is an online banking web application built with Django. Customers open an account, deposit and withdraw money, request loans, transfer money to other customers and view a filterable transaction history. Bank staff approve loans through the Django admin. The project demonstrates class-based views (`CreateView`, `ListView`, `FormView`, `LoginView`) with mixins, form validation rules, extending the built-in `User` with related models, PostgreSQL configuration through environment variables, and HTML email notifications.

## Features

- **Account opening**: registration collects personal and address details plus an account type (Savings or Current). It creates a bank account with a generated account number and logs the user in.
- **Profile**: users update their name, email, account and address details, and can change their password (confirmed by email).
- **Deposits**: a minimum of 100 per deposit.
- **Withdrawals**: between 500 and 20,000 per withdrawal, and never more than the current balance.
- **Loans**: users submit loan requests and see them on a loan list. Staff approve loans in the Django admin, which credits the amount and emails the customer. A user can hold at most three approved loans, and approved loans can be repaid from the loan list.
- **Transfers**: send money to another registered user. Both sender and receiver are notified by email. Transfers are blocked when the bank is marked as bankrupt (a flag the admin controls).
- **Transaction report**: all of a user's transactions, with a date-range filter and the current balance
- **Email notifications**: deposits, withdrawals, loan requests, loan approvals, transfers and password changes each send an HTML email

## Tech stack

| | |
| --- | --- |
| Language | Python 3 |
| Framework | Django 4.2 |
| Database | PostgreSQL (psycopg2) |
| Configuration | django-environ |
| Email | SMTP (Gmail) |
| Front end | Django templates, Tailwind CSS 1.x (CDN), `django.contrib.humanize` |

## Project structure

```
mamar-bank/
├── manage.py
├── requirements.txt
├── mamar_bank/      # settings and root URLconf
├── accounts/        # registration, login, profile; UserBankAccount and UserAddress models
├── transactions/    # deposit, withdraw, loans, transfers, report; admin loan approval
└── core/            # home page, base template, navbar, footer, static images
```

## Getting started

You need a running PostgreSQL server and an empty database for the app.

```bash
git clone https://github.com/ratulhasan001/mamar-bank.git
cd mamar-bank

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a file `mamar_bank/.env` (in the same folder as `settings.py`) with these variables. You can also export them in your shell.

```
SECRET_KEY=your-secret-key
DB_NAME=mamar_bank
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
EMAIL=your-address@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
```

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection settings |
| `EMAIL` | SMTP username (Gmail address) used to send notifications |
| `EMAIL_PASSWORD` | SMTP password (a Gmail app password) |

Then set up the database and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. Before using transfers, sign in to `/admin/` and add a **Bank** record named `mamar_bank`, because the transfer view looks it up by that name. Banking features need a bank account, so register customers through the site rather than using the superuser. Most actions send email, so valid SMTP credentials are required.

## Author

Ratul Hasan · [ratulhasan.dev](https://ratulhasan.dev)
