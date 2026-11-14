from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from .forms import UserRegistrationForm, UserUpdateForm


class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            f'Welcome to Mamar Bank! Your account number is {user.account.account_no}.'
        )
        return super().form_valid(form)


class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('home')


@require_POST
def user_logout(request):
    # Logout is POST-only (as required by Django 5's LogoutView); the navbar
    # submits a small form with a CSRF token.
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


class UserBankAccountUpdateView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
        return render(request, self.template_name, {'form': form})


def send_transaction_email(user, subject, template):
    message = render_to_string(template, {
        'user': user,
    })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()


@login_required
def password_change(request):
    form = PasswordChangeForm(user=request.user)
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            send_transaction_email(request.user, "Password Change Message", "accounts/password_email.html")
            messages.success(request, 'Your password has been changed.')
            return redirect("profile")

    return render(request, 'accounts/password_change.html', {"form": form})
