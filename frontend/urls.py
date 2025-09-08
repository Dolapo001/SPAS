# frontend/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/question/", views.PasswordResetQuestionView.as_view(), name="password_reset_question"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
