from django import forms
from .models import WorkerProfile

class WorkerProfileForm(forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = [
            'service_type',
            'experience',
            'skills',
            'service_area',
            'pincodes',
            'preferred_contact_method',
            'photo',
            'id_proof',
            'address_proof',
            'certificate',
        ]
       
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for now
        for field in self.fields:
            self.fields[field].required = False