# supervisors/forms.py
from django import forms
from .models import Supervisor


class SupervisorForm(forms.ModelForm):
    class Meta:
        model = Supervisor
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 placeholder-gray-500',
                'placeholder': 'Enter supervisor name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 placeholder-gray-500',
                'placeholder': 'supervisor@example.com'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email not required
        self.fields['email'].required = False


class SupervisorUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file with supervisor data (name[,email])",
        widget=forms.FileInput(attrs={
            'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-secondary-start file:text-white hover:file:bg-secondary-mid file:transition-all file:duration-200',
            'accept': '.csv'
        })
    )
    skip_header = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Skip header row",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-secondary-start focus:ring-secondary-start border-gray-300 rounded'
        })
    )
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        label="Update existing supervisors",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-secondary-start focus:ring-secondary-start border-gray-300 rounded'
        })
    )