from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['matric_no', 'full_name', 'email', 'cgpa', 'supervisor']
        widgets = {
            'matric_no': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 placeholder-gray-500',
                'placeholder': 'e.g. BU22CSC1001'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 placeholder-gray-500',
                'placeholder': 'Full name (optional)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 placeholder-gray-500',
                'placeholder': 'student@example.com'
            }),
            'cgpa': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200 placeholder-gray-500',
                'step': '0.01',
                'min': '0',
                'max': '5',
                'placeholder': 'e.g. 4.50'
            }),
            'supervisor': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-white/40 rounded-xl bg-white/60 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-secondary-start focus:border-transparent transition-all duration-200'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add empty option for supervisor
        self.fields['supervisor'].empty_label = "Select a supervisor (optional)"
        # Make supervisor not required
        self.fields['supervisor'].required = False


class StudentUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file with student data (matric_no,cgpa[,full_name,email,supervisor_id])",
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
        label="Update existing students if matric number matches",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-secondary-start focus:ring-secondary-start border-gray-300 rounded'
        })
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            if not csv_file.name.lower().endswith('.csv'):
                raise forms.ValidationError("File must be a CSV file (.csv)")
            if csv_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 5MB")
        return csv_file