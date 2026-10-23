from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Application, Motorcycle, Document
from .eligibility import check_eligibility

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=[('foreign_applicant', 'Foreign Applicant'), ('local_importer', 'Local Importer'), ('clearing_agent', 'Clearing Agent')], required=True)
    identity_type = forms.ChoiceField(choices=[('passport', 'Passport'), ('national_id', 'National ID')], required=True)
    identity_number = forms.CharField(max_length=50, required=True)
    issuing_country = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'identity_type', 'identity_number', 'issuing_country', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        identity_type = cleaned_data.get('identity_type')
        issuing_country = cleaned_data.get('issuing_country')
        if role == 'foreign_applicant':
            if identity_type != 'passport': self.add_error('identity_type', 'Foreign applicants must use a passport.')
            if not issuing_country: self.add_error('issuing_country', 'Country required for foreigners.')
        if role in ['local_importer', 'clearing_agent'] and identity_type != 'national_id':
            self.add_error('identity_type', 'Locals must use a National ID.')
        return cleaned_data

class ApplicationForm(forms.ModelForm):
    brand = forms.CharField(max_length=100, required=True)
    model = forms.CharField(max_length=100, required=True)
    year = forms.IntegerField(required=True)
    engine_capacity_cc = forms.IntegerField(required=True, label="Engine capacity (cc)")
    chassis_number = forms.CharField(max_length=100, required=True, label="Chassis number (VIN)")
    emission_standard = forms.CharField(max_length=20, required=False, label="Emission standard (e.g., Euro 4)")
    on_behalf_of_name = forms.CharField(max_length=200, required=False)
    on_behalf_of_identity = forms.CharField(max_length=50, required=False)

    # File uploads
    tech_data_sheet = forms.FileField(required=False, label="Technical Data Sheet (PDF)")
    prev_registration = forms.FileField(required=False, label="Previous Registration Documents (PDF)")

    class Meta:
        model = Application
        fields = ['intended_use', 'engine_type', 'on_behalf_of_name', 'on_behalf_of_identity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.update({'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean_chassis_number(self):
        """Check if the chassis number already exists in the database."""
        chassis = self.cleaned_data.get('chassis_number')
        # If editing an existing application, we need to ignore its own current chassis number
        if self.instance and self.instance.pk:
            existing_moto = Motorcycle.objects.filter(chassis_number=chassis).exclude(application=self.instance).exists()
            if existing_moto:
                raise forms.ValidationError("A motorcycle with this chassis number already exists in the system.")
        else:
            if Motorcycle.objects.filter(chassis_number=chassis).exists():
                raise forms.ValidationError("A motorcycle with this chassis number already exists in the system.")
        return chassis

    def clean(self):
        cleaned_data = super().clean()
        result = check_eligibility(cleaned_data.get('intended_use'), cleaned_data.get('engine_type'), cleaned_data.get('emission_standard'))
        if not result.allowed:
            raise forms.ValidationError(result.blocked_reason)
        self.eligibility_flags = result.flags
        return cleaned_data