from django import forms
from .models import ServiceRequest
from services.models import Service

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['service', 'address', 'preferred_date', 'preferred_time', 'notes', 'issue_image']
        widgets = {
            'address': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Enter your complete address',
                'class': 'form-control'
            }),
            'preferred_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'preferred_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Any special instructions or notes',
                'class': 'form-control'
            }),
            'issue_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        labels = {
            'service': 'Select Service',
            'address': 'Service Address',
            'preferred_date': 'Preferred Date',
            'preferred_time': 'Preferred Time',
            'notes': 'Additional Notes',
            'issue_image': 'Upload Issue Image',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show only active services
        self.fields['service'].queryset = Service.objects.filter(is_active=True)
        self.fields['service'].empty_label = "-- Select a Service --"
        self.fields['service'].widget.attrs.update({
            'class': 'form-control',
            'required': True
        })
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'required': True
        })
        self.fields['preferred_date'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['preferred_time'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['notes'].widget.attrs.update({
            'class': 'form-control',
            'rows': 3
        })