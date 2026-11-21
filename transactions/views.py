from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from transactions.constants import DEPOSIT, WITHDRAWAL, LOAN, LOAN_PAID
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm,
    MIN_DEPOSIT_AMOUNT,
    MIN_WITHDRAW_AMOUNT,
    MAX_WITHDRAW_AMOUNT,
)
from transactions.models import Bank, Transaction

MAX_APPROVED_LOANS = 3
BANK_NAME = 'mamar_bank'


def send_transaction_email(user, amount, subject, template):
    message = render_to_string(template, {
        'user': user,
        'amount': amount,
    })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()


def format_amount(amount):
    return "{:,.2f}".format(float(amount))


class AccountRequiredMixin(LoginRequiredMixin):
    """Login is required, and the user must have a bank account.

    Accounts are created at registration. Users created another way (for
    example with createsuperuser) have none, so they are sent back with a
    message instead of hitting an error page.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, 'account'):
            messages.error(
                request,
                'This user has no bank account. Register a customer account to use banking features.'
            )
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class TransactionCreateMixin(AccountRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    help_text = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title,
            'help_text': self.help_text,
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'
    help_text = f'Minimum deposit is {MIN_DEPOSIT_AMOUNT} $.'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        with transaction.atomic():
            account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
            account.save(update_fields=['balance'])
            response = super().form_valid(form)

        messages.success(
            self.request,
            f'{format_amount(amount)}$ was deposited to your account successfully'
        )
        send_transaction_email(self.request.user, amount, "Deposit Message", "transactions/deposit_email.html")
        return response


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'
    help_text = (
        f'You can withdraw between {MIN_WITHDRAW_AMOUNT} $ and '
        f'{MAX_WITHDRAW_AMOUNT:,} $, up to your current balance.'
    )

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        # WithdrawForm has already checked the limits and the balance.
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        with transaction.atomic():
            account.balance -= amount
            account.save(update_fields=['balance'])
            response = super().form_valid(form)

        messages.success(
            self.request,
            f'Successfully withdrawn {format_amount(amount)}$ from your account'
        )
        send_transaction_email(self.request.user, amount, "Withdrawal Message", "transactions/withdrawal_email.html")
        return response


class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'
    help_text = (
        f'Loans are approved by bank staff. You can hold at most '
        f'{MAX_APPROVED_LOANS} approved loans at a time.'
    )

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account, transaction_type=LOAN, loan_approve=True
        ).count()
        if current_loan_count >= MAX_APPROVED_LOANS:
            messages.error(
                self.request,
                f'You already have {MAX_APPROVED_LOANS} approved loans. Repay one before requesting another.'
            )
            return redirect('loan_list')
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Loan request for {format_amount(amount)}$ submitted successfully'
        )
        send_transaction_email(self.request.user, amount, "Loan Request Message", "transactions/loan_email.html")
        return response


class TransactionReportView(AccountRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(self.request, 'Please enter valid dates to filter the report.')
            else:
                queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)

        return queryset.distinct() # unique queryset hote hobe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account,
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
        })

        return context


class PayLoanView(AccountRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, loan_id):
        # Users can only repay their own loans.
        loan = get_object_or_404(
            Transaction, id=loan_id, account=request.user.account, transaction_type=LOAN
        )
        if not loan.loan_approve:
            messages.error(request, 'This loan has not been approved yet.')
            return redirect('loan_list')

        user_account = loan.account
        if loan.amount > user_account.balance:
            messages.error(request, 'Loan amount is greater than available balance')
            return redirect('loan_list')

        with transaction.atomic():
            user_account.balance -= loan.amount
            user_account.save(update_fields=['balance'])
            loan.balance_after_transaction = user_account.balance
            loan.transaction_type = LOAN_PAID
            loan.save()

        messages.success(request, f'Loan of {format_amount(loan.amount)}$ has been repaid.')
        return redirect('loan_list')


class LoanListView(AccountRequiredMixin, ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe

    def get_queryset(self):
        return Transaction.objects.filter(
            account=self.request.user.account,
            transaction_type__in=[LOAN, LOAN_PAID],
        )


class TransferMoneyView(AccountRequiredMixin, CreateView):
    form_class = TransferForm
    template_name = 'transactions/transfer.html'
    success_url = reverse_lazy("transfer")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def form_valid(self, form):
        # TransferForm has already checked the amount against the balance and
        # limited receivers to other customers with an account.
        amount = form.cleaned_data.get('amount')
        reciever = form.cleaned_data.get('reciever')
        account = self.request.user.account
        bank, _ = Bank.objects.get_or_create(name=BANK_NAME)

        if bank.is_bankrupt:
            messages.error(self.request, "The bank is bankrupt, so transfers are currently disabled.")
            return redirect("transfer")

        with transaction.atomic():
            account.balance -= amount
            account.save(update_fields=['balance'])
            reciever.account.balance += amount
            reciever.account.save(update_fields=['balance'])
            response = super().form_valid(form)

        messages.success(
            self.request,
            f'{format_amount(amount)}$ was transferred to {reciever.username} successfully'
        )
        send_transaction_email(self.request.user, amount, "Transfer Message", "transactions/transfer_email.html")
        send_transaction_email(reciever, amount, "Transfer Message", "transactions/transfer_email.html")
        return response
