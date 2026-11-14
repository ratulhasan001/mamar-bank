from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import UserBankAccount, UserAddress


def create_customer(username='alice', balance=0, password='s3cret-pass-123'):
    user = User.objects.create_user(
        username=username, password=password, email=f'{username}@example.com',
        first_name=username.title(),
    )
    UserBankAccount.objects.create(
        user=user, account_type='Savings', account_no=100000 + user.id,
        gender='Female', balance=balance,
    )
    UserAddress.objects.create(
        user=user, street_address='1 Main St', city='Dhaka', postal_code=1000, country='Bangladesh',
    )
    return user


class RegistrationTests(TestCase):
    def test_registration_creates_account_and_logs_in(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'a-strong-pass-987',
            'password2': 'a-strong-pass-987',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'account_type': 'Savings',
            'birth_date': '2000-01-01',
            'gender': 'Male',
            'postal_code': 1207,
            'city': 'Dhaka',
            'country': 'Bangladesh',
            'street_address': '12 Road',
        })
        self.assertRedirects(response, reverse('profile'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.account.account_no, 100000 + user.id)
        self.assertEqual(user.account.balance, 0)
        self.assertEqual(user.address.city, 'Dhaka')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_registration_requires_email(self):
        response = self.client.post(reverse('register'), {
            'username': 'noemail', 'password1': 'a-strong-pass-987', 'password2': 'a-strong-pass-987',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='noemail').exists())


class AuthTests(TestCase):
    def setUp(self):
        self.user = create_customer()

    def test_login_and_logout(self):
        response = self.client.post(reverse('login'), {'username': 'alice', 'password': 's3cret-pass-123'})
        self.assertRedirects(response, reverse('home'))
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_rejects_get(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_profile_and_password_pages_need_login(self):
        for name in ('profile', 'password'):
            response = self.client.get(reverse(name))
            self.assertRedirects(response, f"{reverse('login')}?next={reverse(name)}")

    def test_profile_update(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('profile'), {
            'first_name': 'Alicia', 'last_name': 'Smith', 'email': 'alicia@example.com',
            'account_type': 'Current', 'gender': 'Female', 'birth_date': '1999-05-05',
            'street_address': '2 Lake Rd', 'city': 'Khulna', 'postal_code': 9000, 'country': 'Bangladesh',
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alicia')
        self.assertEqual(self.user.account.account_type, 'Current')
        self.assertEqual(self.user.address.city, 'Khulna')

    def test_password_change_sends_email(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('password'), {
            'old_password': 's3cret-pass-123',
            'new_password1': 'another-pass-456',
            'new_password2': 'another-pass-456',
        })
        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(len(mail.outbox), 1)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('another-pass-456'))


class PageSmokeTests(TestCase):
    def test_public_pages(self):
        for name in ('home', 'login', 'register'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_customer_pages(self):
        self.client.force_login(create_customer())
        for name in ('home', 'profile', 'password', 'deposit_money', 'withdraw_money',
                     'loan_request', 'loan_list', 'transfer', 'transaction_report'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_user_without_bank_account_is_redirected(self):
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin-pass-123')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        response = self.client.get(reverse('deposit_money'))
        self.assertRedirects(response, reverse('home'))
