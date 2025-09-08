# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password

from .models import User, Department


class RegistrationForm(UserCreationForm):
    school_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Add your school name'})
    )
    department_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Add your department name'})
    )
    admin_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter administrator\'s full name'})
    )
    secret_answer = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Your answer to the security question'}),
        help_text="You'll need this if you forget your password."
    )

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2', 'secret_question', 'secret_answer')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field as we're using email instead
        if 'username' in self.fields:
            del self.fields['username']

        # Set initial value for secret question
        self.fields['secret_question'].initial = User.get_random_secret_question()
        self.fields['secret_question'].widget.attrs['readonly'] = True


# forms.py
class DepartmentLoginForm(forms.Form):
    department_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your department name',
            'class': 'w-full px-4 py-3 border rounded-xl',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'w-full px-4 py-3 border rounded-xl',
        })
    )
    remember_me = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None  # Use user_cache instead of user

    def clean(self):
        cleaned_data = super().clean()
        dept_name = cleaned_data.get('department_name')
        password = cleaned_data.get('password')

        if dept_name and password:
            try:
                # Case-insensitive search for department
                department = Department.objects.get(name__iexact=dept_name)

                # Get the department admin user
                user = User.objects.get(
                    department=department,
                    is_department_admin=True
                )

                if not user.check_password(password):
                    raise forms.ValidationError("Incorrect password.")

                if not user.is_active:
                    raise forms.ValidationError("This account is inactive.")

                self.user_cache = user

            except Department.DoesNotExist:
                raise forms.ValidationError("Department not found.")
            except User.DoesNotExist:
                raise forms.ValidationError("No administrator account exists for this department.")

        return cleaned_data

    def get_user(self):
        return self.user_cache