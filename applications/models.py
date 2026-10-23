from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = [
        ('foreign_applicant', 'Foreign Applicant'),
        ('local_importer', 'Local Importer'),
        ('clearing_agent', 'Clearing Agent'),
        ('rema_officer', 'REMA Officer'),
        ('rema_admin', 'REMA Admin'),
    ]
    IDENTITY_TYPE_CHOICES = [('passport', 'Passport'), ('national_id', 'National ID')]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='local_importer')
    identity_type = models.CharField(max_length=20, choices=IDENTITY_TYPE_CHOICES, blank=True)
    identity_number = models.CharField(max_length=50, blank=True)
    issuing_country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('under_review', 'Under Review'),
        ('info_requested', 'Information Requested'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ]
    INTENDED_USE_CHOICES = [('sports', 'Sports'), ('disability', 'Person with Disability')]
    ENGINE_TYPE_CHOICES = [('two_stroke', 'Two-Stroke'), ('four_stroke', 'Four-Stroke')]

    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    on_behalf_of_name = models.CharField(max_length=200, blank=True)
    on_behalf_of_identity = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    intended_use = models.CharField(max_length=20, choices=INTENDED_USE_CHOICES)
    engine_type = models.CharField(max_length=20, choices=ENGINE_TYPE_CHOICES)
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    submission_date = models.DateField(null=True, blank=True, db_index=True)
    submission_month = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    submission_year = models.IntegerField(null=True, blank=True, db_index=True)
    reference_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False, help_text="If True, the application is in the Recycle Bin")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"APP-{self.id} — {self.applicant.username} ({self.status})"

    def sla_deadline(self):
        if not self.submitted_at:
            return None
        days_added = 0
        current = self.submitted_at
        while days_added < 7:
            current += timedelta(days=1)
            if current.weekday() < 5:
                days_added += 1
        return current

    def is_overdue(self):
        deadline = self.sla_deadline()
        if deadline and self.status not in ['approved', 'rejected']:
            return timezone.now() > deadline
        return False
        
    def is_approaching_deadline(self):
        """Returns True if the application is on day 6 (1 day left)"""
        deadline = self.sla_deadline()
        if deadline and self.status not in ['approved', 'rejected']:
            # Check if we are within 24-48 hours of the deadline
            time_left = deadline - timezone.now()
            return timedelta(hours=0) < time_left <= timedelta(hours=24)
        return False

    def save(self, *args, **kwargs):
        if self.submitted_at:
            self.submission_date = self.submitted_at.date()
            self.submission_month = self.submitted_at.strftime('%B %Y')
            self.submission_year = self.submitted_at.year
        super().save(*args, **kwargs)

class Motorcycle(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='motorcycle')
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    engine_capacity_cc = models.IntegerField()
    chassis_number = models.CharField(max_length=100, unique=True)
    emission_standard = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"

class Document(models.Model):
    DOC_TYPE_CHOICES = [('tech_data_sheet', 'Technical Data Sheet'), ('prev_registration', 'Previous Registration Documents'), ('passport_copy', 'Passport Copy'), ('national_id_copy', 'National ID Copy'), ('other', 'Other')]
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/%Y/%m/')
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Decision(models.Model):
    ACTION_CHOICES = [('approve', 'Approve'), ('reject', 'Reject'), ('request_info', 'Request More Information')]
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='decisions')
    officer = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-decided_at']

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=50)
    entity_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-timestamp']

class Notification(models.Model):
    # Added 'sla_warning' to the choices
    TYPE_CHOICES = [('submitted', 'Application Submitted'), ('approved', 'Application Approved'), ('rejected', 'Application Rejected'), ('info_requested', 'Information Requested'), ('sla_reminder', 'SLA Reminder'), ('sla_warning', 'SLA Warning')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')