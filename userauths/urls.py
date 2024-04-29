from django.urls import path
from userauths import views

app_name = "userauths"

urlpatterns = [
    path("sign-up/", views.register_view, name="sign-up"),
    path("sign-in/", views.login_view, name="sign-in"),
    path("sign-out/", views.logout_view, name="sign-out"),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path("profile/update/", views.profile_update, name="profile-update"),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('send_forgot_otp/', views.send_forgot_otp_view, name='send_forgot_otp'),
]