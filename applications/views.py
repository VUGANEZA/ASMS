import csv
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Max
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings

# ReportLab imports for PDF generation & font handling
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Application, Motorcycle, Document, AuditLog, Decision, Notification
from .forms import RegistrationForm, ApplicationForm
from .translations import TRANSLATIONS

def get_lang(request):
    lang = request.GET.get('lang', 'en')
    return lang if lang in TRANSLATIONS else 'en'

def _log(user, action, entity='', entity_id=None, request=None):
    ip = None
    if request:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(user=user if user and user.is_authenticated else None, action=action, entity=entity, entity_id=entity_id, ip_address=ip)

def is_rema_staff(request):
    return request.user.is_authenticated and getattr(request.user, 'role', '') in ['rema_officer', 'rema_admin']

def send_decision_email(application, action):
    user = application.applicant
    if not user.email: return
    ref_number = application.reference_number or "N/A"
    vehicle_name = f"{application.motorcycle.brand} {application.motorcycle.model}" if application.motorcycle else "N/A"
    subject, message, notif_type = "", "", ""
    
    if action == 'approve':
        subject = f"ASMS: Application {ref_number} Approved"
        message = (
            f"Dear {user.first_name or user.username},\n\n"
            f"We are pleased to inform you that your application to import a second-hand motorcycle "
            f"({vehicle_name}) has been APPROVED by the Rwanda Environment Management Authority (REMA).\n\n"
            f"Official Reference Number: {ref_number}\n\n"
            f"You may now proceed with the customs clearance process.\n\n"
            f"Best regards,\nREMA ASMS Team"
        )
        notif_type = 'approved'
    elif action == 'reject':
        reason = application.decisions.first().reason if application.decisions.exists() else "Not specified."
        subject = f"ASMS: Application {ref_number} Rejected"
        message = (
            f"Dear {user.first_name or user.username},\n\n"
            f"We regret to inform you that your application ({ref_number}) has been REJECTED.\n\n"
            f"Reason: \"{reason}\"\n\n"
            f"Best regards,\nREMA ASMS Team"
        )
        notif_type = 'rejected'
    elif action == 'request_info':
        reason = application.decisions.first().reason if application.decisions.exists() else "Not specified."
        subject = f"ASMS: Action Required for Application {ref_number}"
        message = (
            f"Dear {user.first_name or user.username},\n\n"
            f"REMA requires more information for your application ({ref_number}).\n\n"
            f"Message: \"{reason}\"\n\n"
            f"Please log in to update your application.\n\n"
            f"Best regards,\nREMA ASMS Team"
        )
        notif_type = 'info_requested'

    if subject:
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            status = 'sent'
        except Exception: 
            status = 'failed'
        Notification.objects.create(user=user, application=application, type=notif_type, status=status)

# ─────────────────────────────────────────────
# PUBLIC / AUTH
# ─────────────────────────────────────────────
def home(request):
    lang = get_lang(request)
    return render(request, 'applications/home.html', {'t': TRANSLATIONS[lang], 'current_lang': lang})

def about(request):
    lang = get_lang(request)
    return render(request, 'applications/about.html', {'t': TRANSLATIONS[lang], 'current_lang': lang})

def register(request):
    lang = get_lang(request)
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created.")
            return redirect(f"/login/?lang={lang}")
    else: form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form, 't': TRANSLATIONS[lang], 'current_lang': lang})

class ApplicantLoginView(LoginView):
    template_name = 'registration/login.html'
    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, 'role', '') in ['rema_officer', 'rema_admin']:
            messages.error(self.request, "Admins use Admin Login.")
            return redirect('login')
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy('dashboard')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = get_lang(self.request)
        context['t'] = TRANSLATIONS[lang]
        context['current_lang'] = lang
        return context

class OfficerLoginView(LoginView):
    template_name = 'registration/officer_login.html'
    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, 'role', '') not in ['rema_officer', 'rema_admin']:
            messages.error(self.request, "Access Denied.")
            return redirect('officer_login')
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy('officer_dashboard')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = get_lang(self.request)
        context['t'] = TRANSLATIONS[lang]
        context['current_lang'] = lang
        return context

# ─────────────────────────────────────────────
# PUBLIC VERIFICATION VIEW
# ─────────────────────────────────────────────
def verify_application(request, ref_number):
    app = Application.objects.filter(reference_number=ref_number).first()
    context = {
        'application': app,
        'ref_number': ref_number,
    }
    return render(request, 'applications/verify.html', context)

# ─────────────────────────────────────────────
# APPLICANT VIEWS
# ─────────────────────────────────────────────
@login_required
def dashboard(request):
    lang = get_lang(request)
    apps = Application.objects.filter(applicant=request.user, is_deleted=False).order_by('-created_at')
    return render(request, 'applications/dashboard.html', {'applications': apps, 'total': apps.count(), 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def application_create(request):
    lang = get_lang(request)
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.applicant = request.user
            app.status = 'submitted'
            app.submitted_at = timezone.now()
            app.save()
            Motorcycle.objects.create(application=app, brand=form.cleaned_data['brand'], model=form.cleaned_data['model'], year=form.cleaned_data['year'], engine_capacity_cc=form.cleaned_data['engine_capacity_cc'], chassis_number=form.cleaned_data['chassis_number'], emission_standard=form.cleaned_data.get('emission_standard', ''))
            if form.cleaned_data.get('tech_data_sheet'): Document.objects.create(application=app, doc_type='tech_data_sheet', file=form.cleaned_data['tech_data_sheet'], original_filename=form.cleaned_data['tech_data_sheet'].name)
            if form.cleaned_data.get('prev_registration'): Document.objects.create(application=app, doc_type='prev_registration', file=form.cleaned_data['prev_registration'], original_filename=form.cleaned_data['prev_registration'].name)
            messages.success(request, "Application received.")
            return redirect(f"/application/{app.id}/?lang={lang}")
    else: form = ApplicationForm()
    return render(request, 'applications/application_form.html', {'form': form, 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def application_detail(request, pk):
    lang = get_lang(request)
    app = get_object_or_404(Application, pk=pk)
    if app.applicant != request.user and not is_rema_staff(request): return redirect('dashboard')
    return render(request, 'applications/application_detail.html', {'application': app, 'documents': app.documents.all(), 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def application_edit(request, pk):
    lang = get_lang(request)
    app = get_object_or_404(Application, pk=pk)
    if app.applicant != request.user or app.status not in ['submitted', 'info_requested']: return redirect('dashboard')
    mc = app.motorcycle
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, instance=app)
        if form.is_valid():
            app = form.save()
            mc.brand=form.cleaned_data['brand']; mc.model=form.cleaned_data['model']; mc.year=form.cleaned_data['year']; mc.engine_capacity_cc=form.cleaned_data['engine_capacity_cc']; mc.chassis_number=form.cleaned_data['chassis_number']; mc.save()
            messages.success(request, "Updated.")
            return redirect(f"/application/{app.id}/?lang={lang}")
    else:
        form = ApplicationForm(instance=app, initial={'brand': mc.brand, 'model': mc.model, 'year': mc.year, 'engine_capacity_cc': mc.engine_capacity_cc, 'chassis_number': mc.chassis_number})
    return render(request, 'applications/application_form.html', {'form': form, 'is_edit': True, 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def application_delete(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if app.applicant != request.user: return redirect('dashboard')
    app.is_deleted = True
    app.save()
    messages.success(request, "Application deleted successfully.")
    return redirect(f"/dashboard/?lang={get_lang(request)}")

# ─────────────────────────────────────────────
# REMA OFFICER VIEWS
# ─────────────────────────────────────────────
@login_required
def officer_dashboard(request):
    lang = get_lang(request)
    if not is_rema_staff(request): return redirect('home')
    apps = Application.objects.filter(is_deleted=False).select_related('applicant', 'motorcycle').order_by('-submitted_at')
    return render(request, 'applications/officer_dashboard.html', {'applications': apps, 'total': apps.count(), 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def officer_application_view(request, pk):
    lang = get_lang(request)
    app = get_object_or_404(Application, pk=pk)
    is_staff = is_rema_staff(request)

    if not is_staff:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        if action in ['approve', 'reject', 'request_info']:
            Decision.objects.create(application=app, officer=request.user, action=action, reason=reason)
            app.decision_at = timezone.now()
            if action == 'approve':
                app.status = 'approved'
                last_app = Application.objects.filter(reference_number__startswith=f'ASMS-MOTO-{app.decision_at.year}-').aggregate(Max('id'))
                app.reference_number = f"ASMS-MOTO-{app.decision_at.year}-{(last_app['id__max'] or 0) + 1:05d}"
            elif action == 'reject': app.status = 'rejected'
            elif action == 'request_info': app.status = 'info_requested'
            app.save()
            send_decision_email(app, action)
            return redirect(f"/officer/application/{app.id}/?lang={lang}")
            
    return render(request, 'applications/officer_application_view.html', {'application': app, 'documents': app.documents.all(), 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def officer_delete_application(request, pk):
    app = get_object_or_404(Application, pk=pk)
    app.is_deleted = True
    app.save()
    return redirect(f"/officer/?lang={get_lang(request)}")

@login_required
def officer_recycle_bin(request):
    lang = get_lang(request)
    apps = Application.objects.filter(is_deleted=True)
    return render(request, 'applications/officer_recycle_bin.html', {'applications': apps, 't': TRANSLATIONS[lang], 'current_lang': lang})

@login_required
def officer_restore_application(request, pk):
    app = get_object_or_404(Application, pk=pk)
    app.is_deleted = False
    app.save()
    return redirect(f"/officer/recycle-bin/?lang={get_lang(request)}")

# ─────────────────────────────────────────────
# PDF & CSV EXPORTS (MULTILINGUAL WITH FONT FIX)
# ─────────────────────────────────────────────
@login_required
def application_download_pdf(request, pk):
    if not is_rema_staff(request): return redirect('home')
    
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    import qrcode

    # Register Fonts for Multi-language support
    font_name = 'Helvetica'
    bold_font_name = 'Helvetica-Bold'
    try:
        if os.name == 'nt': # Windows
            pdfmetrics.registerFont(TTFont('CustomUnicode', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('CustomUnicode-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
        else: # Linux/Mac
            pdfmetrics.registerFont(TTFont('CustomUnicode', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('CustomUnicode-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        font_name = 'CustomUnicode'
        bold_font_name = 'CustomUnicode-Bold'
    except Exception:
        pass

    lang = get_lang(request)
    t = TRANSLATIONS[lang]

    application = get_object_or_404(Application, pk=pk)
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontName=bold_font_name, textColor=colors.HexColor('#1b5e5a'), fontSize=18, spaceAfter=6, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontName=font_name, textColor=colors.black, fontSize=11, alignment=TA_CENTER, spaceAfter=20)
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontName=bold_font_name, textColor=colors.HexColor('#1b5e5a'), fontSize=14, spaceBefore=15, spaceAfter=10)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName=font_name)

    elements = []
    
    # HEADER
    elements.append(Paragraph(t.get('pdf_title', "REPUBLIC OF RWANDA"), title_style))
    elements.append(Paragraph(t.get('pdf_subtitle', "Rwanda Environment Management Authority (REMA)"), subtitle_style))
    elements.append(Paragraph(t.get('pdf_system', "Authorization of Second-Hand Motorcycles System (ASMS)"), subtitle_style))
    
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Table([['']], colWidths=[17*cm], style=[('LINEABOVE', (0,0), (-1,-1), 2, colors.HexColor('#1b5e5a'))]))
    elements.append(Spacer(1, 0.5*cm))

    # APPLICATION INFO
    elements.append(Paragraph(f"<b>{t.get('application_id', 'Application ID')}:</b> APP-{application.id}", normal_style))
    elements.append(Paragraph(f"<b>{t.get('status', 'Status')}:</b> {application.get_status_display()}", normal_style))
    elements.append(Paragraph(f"<b>{t.get('date_applied', 'Date Applied')}:</b> {application.submission_date or '—'}", normal_style))
    elements.append(Paragraph(f"<b>{t.get('applicant', 'Applicant')}:</b> {application.applicant.username}", normal_style))
    
    elements.append(Spacer(1, 0.5*cm))

    # MOTORCYCLE DETAILS
    elements.append(Paragraph(t.get('pdf_mc_details', "Motorcycle Details"), h2_style))
    mc = application.motorcycle
    
    if mc:
        mc_data = [
            [t.get('brand', 'Brand'), mc.brand],
            [t.get('model', 'Model'), mc.model],
            [t.get('year', 'Year'), str(mc.year)],
            [t.get('engine_cc', 'Engine Capacity'), f"{mc.engine_capacity_cc} cc"],
            [t.get('chassis', 'Chassis Number (VIN)'), mc.chassis_number]
        ]
        mc_table = Table(mc_data, colWidths=[5*cm, 12*cm])
        mc_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f4f8f8')),
            ('FONTNAME', (0, 0), (-1, -1), font_name), 
            ('FONTNAME', (0, 0), (0, -1), bold_font_name), 
            ('PADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(mc_table)

    # QR CODE (Dynamic URL for Render & Localhost)
    if application.reference_number:
        elements.append(Spacer(1, 1.5*cm))
        
        # Get the domain dynamically
        domain = request.build_absolute_uri('/')[:-1]
        verify_url = f"{domain}/verify/{application.reference_number}/"
        
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1b5e5a", back_color="white")
        
        qr_buffer = BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        qr_image = Image(qr_buffer, width=4*cm, height=4*cm)
        qr_table = Table([[qr_image]], colWidths=[17*cm])
        qr_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        elements.append(qr_table)
        
        qr_text_style = ParagraphStyle('QRText', parent=normal_style, fontName=font_name, alignment=TA_CENTER, fontSize=10, textColor=colors.grey)
        elements.append(Paragraph(t.get('pdf_qr_text', "Scan the QR code above to verify the authenticity of this document."), qr_text_style))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ASMS-APP-{application.id}-{lang}.pdf"'
    return response

@login_required
def application_download_csv(request, pk):
    if not is_rema_staff(request): return redirect('home')
    application = get_object_or_404(Application, pk=pk)
    mc = application.motorcycle
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ASMS-APP-{application.id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Field', 'Value'])
    writer.writerow(['Application ID', f'APP-{application.id}'])
    writer.writerow(['Status', application.get_status_display()])
    writer.writerow(['Reference Number', application.reference_number or '—'])
    writer.writerow(['Date Applied', application.submission_date])
    writer.writerow(['Applicant', application.applicant.username])
    if mc:
        writer.writerow(['Brand', mc.brand])
        writer.writerow(['Model', mc.model])
        writer.writerow(['Chassis', mc.chassis_number])
    return response

@login_required
def officer_export_all_csv(request):
    if not is_rema_staff(request): return redirect('home')
    applications = Application.objects.filter(is_deleted=False).select_related('applicant', 'motorcycle').order_by('-submitted_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ASMS-Applications.csv"'
    writer = csv.writer(response)
    writer.writerow(['App ID', 'Date', 'Status', 'Reference', 'Applicant', 'Brand', 'Model', 'Chassis'])
    for app in applications:
        writer.writerow([
            f'APP-{app.id}', app.submission_date, app.get_status_display(), 
            app.reference_number or '', app.applicant.username, 
            app.motorcycle.brand if app.motorcycle else '', 
            app.motorcycle.model if app.motorcycle else '', 
            app.motorcycle.chassis_number if app.motorcycle else ''
        ])
    return response

@login_required
def officer_export_all_pdf(request):
    if not is_rema_staff(request): return redirect('home')
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO

    # Register Fonts
    font_name = 'Helvetica'
    bold_font_name = 'Helvetica-Bold'
    try:
        if os.name == 'nt':
            pdfmetrics.registerFont(TTFont('CustomUnicodeBulk', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('CustomUnicodeBulk-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
        else:
            pdfmetrics.registerFont(TTFont('CustomUnicodeBulk', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('CustomUnicodeBulk-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        font_name = 'CustomUnicodeBulk'
        bold_font_name = 'CustomUnicodeBulk-Bold'
    except Exception:
        pass

    lang = get_lang(request)
    t = TRANSLATIONS[lang]

    applications = Application.objects.filter(is_deleted=False).select_related('applicant', 'motorcycle').order_by('-submitted_at')
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontName=bold_font_name, textColor=colors.HexColor('#1b5e5a'), fontSize=18, spaceAfter=6)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName=font_name)
    
    elements = []
    elements.append(Paragraph(t.get('bulk_pdf_title', "REMA ASMS - Officer Dashboard Report"), title_style))
    elements.append(Paragraph(f"{t.get('total_applications', 'Total Applications')}: {applications.count()}", normal_style))
    elements.append(Spacer(1, 0.5*cm))

    data = [[
        '#', 
        t.get('applicant', 'Applicant'), 
        t.get('motorcycle_details', 'Motorcycle Details'), 
        t.get('status', 'Status')
    ]]
    
    for app in applications:
        if app.motorcycle:
            mc_name = f"{app.motorcycle.brand} {app.motorcycle.model}"
        else:
            mc_name = "—"
            
        data.append([
            f"APP-{app.id}", 
            app.applicant.username, 
            mc_name, 
            app.get_status_display()
        ])

    table = Table(data, colWidths=[3*cm, 6*cm, 10*cm, 5*cm])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b5e5a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), font_name), 
        ('FONTNAME', (0, 0), (-1, 0), bold_font_name), 
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ASMS-Dashboard-Report-{lang}.pdf"'
    return response