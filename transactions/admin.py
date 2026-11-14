from django.contrib import admin

from .constants import LOAN
from .models import Transaction, Transfer, Bank
from .views import send_transaction_email


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'amount', 'balance_after_transaction', 'transaction_type', 'loan_approve']
    list_filter = ['transaction_type', 'loan_approve']

    def save_model(self, request, obj, form, change):
        # Credit the customer only when a loan is approved, and only once.
        newly_approved = (
            obj.transaction_type == LOAN
            and obj.loan_approve
            and (not change or 'loan_approve' in form.changed_data)
        )
        if newly_approved:
            obj.account.balance += obj.amount
            obj.balance_after_transaction = obj.account.balance
            obj.account.save(update_fields=['balance'])
        super().save_model(request, obj, form, change)
        if newly_approved:
            send_transaction_email(obj.account.user, obj.amount, "Loan Approval", "transactions/admin_email.html")


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_bankrupt']


admin.site.register(Transfer)
