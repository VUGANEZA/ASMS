from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Application, Motorcycle, Document, Decision, AuditLog, Notification

admin.site.site_header = "ASMS Administration"

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'is_verified']

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'applicant', 'status', 'intended_use', 'engine_type', 'submitted_at', 'reference_number']
    list_filter = ['status', 'intended_use', 'engine_type']

admin.site.register(Motorcycle)
admin.site.register(Document)
admin.site.register(Decision)
admin.site.register(AuditLog)
admin.site.register(Notification)