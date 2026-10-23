from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import OfficerLoginView, ApplicantLoginView

urlpatterns = [
    # Home & About
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),

    # PUBLIC VERIFICATION PAGE (FOR QR CODE)
    path('verify/<str:ref_number>/', views.verify_application, name='verify_application'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', ApplicantLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # ── NEW: PASSWORD RESET ROUTES ──
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Admin/Officer Only Login
    path('officer/login/', OfficerLoginView.as_view(), name='officer_login'),

    # Applicant portal
    path('dashboard/', views.dashboard, name='dashboard'),
    path('apply/', views.application_create, name='application_create'),
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    path('application/<int:pk>/edit/', views.application_edit, name='application_edit'),
    path('application/<int:pk>/delete/', views.application_delete, name='application_delete'),

    # REMA officer portal
    path('officer/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/recycle-bin/', views.officer_recycle_bin, name='officer_recycle_bin'),
    path('officer/application/<int:pk>/', views.officer_application_view, name='officer_application_view'),
    path('officer/application/<int:pk>/delete/', views.officer_delete_application, name='officer_delete_application'),
    path('officer/application/<int:pk>/restore/', views.officer_restore_application, name='officer_restore_application'),
    path('officer/application/<int:pk>/pdf/', views.application_download_pdf, name='application_download_pdf'),
    path('officer/application/<int:pk>/csv/', views.application_download_csv, name='application_download_csv'),
    path('officer/export/all-pdf/', views.officer_export_all_pdf, name='officer_export_all_pdf'),
    path('officer/export/all-csv/', views.officer_export_all_csv, name='officer_export_all_csv'),
]