from django.urls import path

from .views import (
    UserBankAccountUpdateView,
    UserLoginView,
    UserRegistrationView,
    password_change,
    user_logout,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),
    path('profile/', UserBankAccountUpdateView.as_view(), name='profile'),
    path('password_change/', password_change, name='password'),
]
