from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from applications.models import Application, Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Checks for applications approaching the 7-day SLA deadline and alerts admins.'

    def handle(self, *args, **kwargs):
        # Get all pending applications
        pending_apps = Application.objects.filter(
            status__in=['submitted', 'under_review', 'info_requested'],
            is_deleted=False
        )

        # Get all REMA Staff emails
        admins = User.objects.filter(role__in=['rema_officer', 'rema_admin'])
        admin_emails = [admin.email for admin in admins if admin.email]

        if not admin_emails:
            self.stdout.write(self.style.WARNING('No admin emails found. Skipping.'))
            return

        alert_count = 0

        for app in pending_apps:
            # Check if it's overdue or approaching
            if app.is_overdue:
                subject = f"URGENT SLA OVERDUE: APP-{app.id} has passed the 7-day deadline!"
                message = f"Warning: APP-{app.id} for {app.applicant.username} submitted on {app.submission_date} has passed the 7-day SLA deadline. Please review immediately."
            elif app.is_approaching_deadline:
                deadline = app.sla_deadline().date()
                subject = f"WARNING: APP-{app.id} is approaching the 7-day deadline!"
                message = f"Warning: APP-{app.id} for {app.applicant.username} submitted on {app.submission_date} is approaching the 7-day deadline. It must be reviewed by {deadline}."
            else:
                continue # Skip if not near deadline

            # Send the email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=True,
            )
            
            # Log the notification in the database
            for admin in admins:
                Notification.objects.create(
                    user=admin, 
                    application=app, 
                    type='sla_warning', 
                    status='sent'
                )
            
            alert_count += 1

        self.stdout.write(self.style.SUCCESS(f'SLA Check Complete: {alert_count} alerts sent.'))