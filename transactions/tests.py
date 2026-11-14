from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.tests import create_customer
from .constants import DEPOSIT, LOAN, LOAN_PAID, WITHDRAWAL
from .models import Bank, Transaction, Transfer


class DepositWithdrawTests(TestCase):
    def setUp(self):
        self.user = create_customer(balance=1000)
        self.client.force_login(self.user)

    def balance(self):
        self.user.account.refresh_from_db()
        return self.user.account.balance

    def test_deposit_needs_login(self):
        self.client.logout()
        response = self.client.post(reverse('deposit_money'), {'amount': 500})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertEqual(self.balance(), 1000)

    def test_deposit_below_minimum_is_rejected(self):
        response = self.client.post(reverse('deposit_money'), {'amount': 99})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You need to deposit at least 100')
        self.assertEqual(self.balance(), 1000)
        self.assertFalse(Transaction.objects.exists())

    def test_deposit_updates_balance_and_records_transaction(self):
        response = self.client.post(reverse('deposit_money'), {'amount': 250})
        self.assertRedirects(response, reverse('transaction_report'))
        self.assertEqual(self.balance(), Decimal('1250'))
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.transaction_type, DEPOSIT)
        self.assertEqual(transaction.balance_after_transaction, Decimal('1250'))
        self.assertEqual(len(mail.outbox), 1)

    def test_withdraw_limits(self):
        for amount, error in [
            (499, 'You can withdraw at least 500'),
            (20001, 'You can withdraw at most 20000'),
            (1001, 'You can not withdraw more than your account balance'),
        ]:
            response = self.client.post(reverse('withdraw_money'), {'amount': amount})
            self.assertContains(response, error)
        self.assertEqual(self.balance(), 1000)
        self.assertFalse(Transaction.objects.exists())

    def test_withdraw_success(self):
        response = self.client.post(reverse('withdraw_money'), {'amount': 600})
        self.assertRedirects(response, reverse('transaction_report'))
        self.assertEqual(self.balance(), Decimal('400'))
        self.assertEqual(Transaction.objects.get().transaction_type, WITHDRAWAL)

    def test_report_lists_only_own_transactions_and_handles_bad_dates(self):
        other = create_customer('bob', balance=0)
        Transaction.objects.create(account=other.account, amount=5, balance_after_transaction=5, transaction_type=DEPOSIT)
        Transaction.objects.create(account=self.user.account, amount=7, balance_after_transaction=7, transaction_type=DEPOSIT)
        response = self.client.get(reverse('transaction_report'))
        self.assertEqual(len(response.context['object_list']), 1)
        response = self.client.get(reverse('transaction_report'), {'start_date': 'bad', 'end_date': 'dates'})
        self.assertEqual(response.status_code, 200)


class LoanTests(TestCase):
    def setUp(self):
        self.user = create_customer(balance=1000)
        self.client.force_login(self.user)

    def make_loan(self, account=None, amount=300, approved=True):
        return Transaction.objects.create(
            account=account or self.user.account, amount=amount, balance_after_transaction=0,
            transaction_type=LOAN, loan_approve=approved,
        )

    def test_loan_request_creates_pending_loan(self):
        response = self.client.post(reverse('loan_request'), {'amount': 5000})
        self.assertRedirects(response, reverse('transaction_report'))
        loan = Transaction.objects.get()
        self.assertEqual(loan.transaction_type, LOAN)
        self.assertFalse(loan.loan_approve)

    def test_loan_amount_must_be_positive(self):
        response = self.client.post(reverse('loan_request'), {'amount': -10})
        self.assertContains(response, 'Amount must be greater than zero')
        self.assertFalse(Transaction.objects.exists())

    def test_loan_limit(self):
        for _ in range(3):
            self.make_loan()
        response = self.client.post(reverse('loan_request'), {'amount': 100})
        self.assertRedirects(response, reverse('loan_list'))
        self.assertEqual(Transaction.objects.count(), 3)

    def test_pay_loan(self):
        loan = self.make_loan(amount=300)
        response = self.client.post(reverse('pay', args=[loan.id]))
        self.assertRedirects(response, reverse('loan_list'))
        loan.refresh_from_db()
        self.user.account.refresh_from_db()
        self.assertEqual(loan.transaction_type, LOAN_PAID)
        self.assertEqual(self.user.account.balance, Decimal('700'))
        # Repaid loans stay on the list and no longer count towards the limit.
        response = self.client.get(reverse('loan_list'))
        self.assertContains(response, 'Repaid')

    def test_pay_loan_rejects_get(self):
        loan = self.make_loan()
        self.assertEqual(self.client.get(reverse('pay', args=[loan.id])).status_code, 405)

    def test_cannot_pay_unapproved_loan_or_with_low_balance(self):
        pending = self.make_loan(approved=False)
        big = self.make_loan(amount=5000)
        for loan in (pending, big):
            self.client.post(reverse('pay', args=[loan.id]))
            loan.refresh_from_db()
            self.assertEqual(loan.transaction_type, LOAN)
        self.user.account.refresh_from_db()
        self.assertEqual(self.user.account.balance, 1000)

    def test_cannot_pay_someone_elses_loan(self):
        other = create_customer('bob', balance=1000)
        loan = self.make_loan(account=other.account)
        response = self.client.post(reverse('pay', args=[loan.id]))
        self.assertEqual(response.status_code, 404)

    def test_admin_approval_credits_once(self):
        loan = self.make_loan(amount=400, approved=False)
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin-pass-123')
        self.client.force_login(admin)
        url = reverse('admin:transactions_transaction_change', args=[loan.id])
        data = {
            'account': self.user.account.id, 'amount': '400', 'balance_after_transaction': '0',
            'transaction_type': LOAN, 'loan_approve': 'on',
        }
        self.client.post(url, data)
        self.user.account.refresh_from_db()
        self.assertEqual(self.user.account.balance, Decimal('1400'))
        self.assertEqual(len(mail.outbox), 1)
        # Saving the approved loan again must not credit it twice.
        self.client.post(url, data)
        self.user.account.refresh_from_db()
        self.assertEqual(self.user.account.balance, Decimal('1400'))


class TransferTests(TestCase):
    def setUp(self):
        self.sender = create_customer('alice', balance=1000)
        self.receiver = create_customer('bob', balance=50)
        self.client.force_login(self.sender)

    def balances(self):
        self.sender.account.refresh_from_db()
        self.receiver.account.refresh_from_db()
        return self.sender.account.balance, self.receiver.account.balance

    def test_transfer_works_without_bank_row(self):
        Bank.objects.all().delete()
        response = self.client.post(reverse('transfer'), {'reciever': self.receiver.id, 'amount': 300})
        self.assertRedirects(response, reverse('transfer'))
        self.assertEqual(self.balances(), (Decimal('700'), Decimal('350')))
        self.assertEqual(Transfer.objects.count(), 1)
        self.assertTrue(Bank.objects.filter(name='mamar_bank').exists())
        self.assertEqual(len(mail.outbox), 2)

    def test_transfer_entire_balance(self):
        self.client.post(reverse('transfer'), {'reciever': self.receiver.id, 'amount': 1000})
        self.assertEqual(self.balances(), (Decimal('0'), Decimal('1050')))

    def test_transfer_rejects_invalid_amounts(self):
        for amount in (1001, 0, -50):
            response = self.client.post(reverse('transfer'), {'reciever': self.receiver.id, 'amount': amount})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balances(), (Decimal('1000'), Decimal('50')))
        self.assertFalse(Transfer.objects.exists())

    def test_cannot_transfer_to_self(self):
        response = self.client.post(reverse('transfer'), {'reciever': self.sender.id, 'amount': 10})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['reciever'])
        self.assertEqual(self.balances(), (Decimal('1000'), Decimal('50')))

    def test_transfer_blocked_when_bankrupt(self):
        Bank.objects.update_or_create(name='mamar_bank', defaults={'is_bankrupt': True})
        response = self.client.post(reverse('transfer'), {'reciever': self.receiver.id, 'amount': 100})
        self.assertRedirects(response, reverse('transfer'))
        self.assertEqual(self.balances(), (Decimal('1000'), Decimal('50')))

    def test_transfer_needs_login(self):
        self.client.logout()
        response = self.client.post(reverse('transfer'), {'reciever': self.receiver.id, 'amount': 100})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.balances(), (Decimal('1000'), Decimal('50')))
