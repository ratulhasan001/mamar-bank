from django import forms
from django.contrib.auth.models import User

from .models import Transaction, Transfer

MIN_DEPOSIT_AMOUNT = 100
MIN_WITHDRAW_AMOUNT = 500
MAX_WITHDRAW_AMOUNT = 20000


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'amount',
            'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account') # account value ke pop kore anlam
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].disabled = True # ei field disable thakbe
        self.fields['transaction_type'].widget = forms.HiddenInput() # user er theke hide kora thakbe

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()


class DepositForm(TransactionForm):
    def clean_amount(self): # amount field ke filter korbo
        amount = super().clean_amount()
        if amount < MIN_DEPOSIT_AMOUNT:
            raise forms.ValidationError(
                f'You need to deposit at least {MIN_DEPOSIT_AMOUNT} $'
            )

        return amount


class WithdrawForm(TransactionForm):

    def clean_amount(self):
        balance = self.account.balance
        amount = super().clean_amount()
        if amount < MIN_WITHDRAW_AMOUNT:
            raise forms.ValidationError(
                f'You can withdraw at least {MIN_WITHDRAW_AMOUNT} $'
            )

        if amount > MAX_WITHDRAW_AMOUNT:
            raise forms.ValidationError(
                f'You can withdraw at most {MAX_WITHDRAW_AMOUNT} $'
            )

        if amount > balance: # amount = 5000, tar balance ache 200
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not withdraw more than your account balance'
            )

        return amount


class LoanRequestForm(TransactionForm):
    pass


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = ["reciever", "amount"]
        labels = {"reciever": "Receiver"}

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        # Only other customers with a bank account can receive money.
        self.fields['reciever'].queryset = (
            User.objects.filter(account__isnull=False)
            .exclude(pk=self.account.user_id)
            .order_by('username')
        )
        self.fields['reciever'].empty_label = 'Select a receiver'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        if amount is not None and amount > self.account.balance:
            raise forms.ValidationError(
                f'You have {self.account.balance} $ in your account. '
                'You can not transfer more than your account balance'
            )
        return amount

    def save(self, commit=True):
        self.instance.sender = self.account
        return super().save()
