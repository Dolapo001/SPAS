# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, get_user_model
from django.contrib import messages
from django.views import View
from django.views.decorators.csrf import csrf_protect

from allocation.models import AllocationResult, Group
from students.models import Student
from supervisors.models import Supervisor
from .models import User, School, Department
from .forms import RegistrationForm, DepartmentLoginForm

User = get_user_model()


def register(request):
    print("Registration view called")
    print("Method:", request.method)

    if request.method == 'POST':
        form = RegistrationForm(request.POST)  # Create form instance from POST data
        print("POST data:", request.POST)
        print("Form is valid:", form.is_valid())

        if form.is_valid():
            print("Cleaned data:", form.cleaned_data)

            # Get the school and department names from the form
            school_name = form.cleaned_data.get('school_name')
            department_name = form.cleaned_data.get('department_name')
            admin_name = form.cleaned_data.get('admin_name')

            # Create or get the school
            school, school_created = School.objects.get_or_create(
                name=school_name,
                defaults={'code': school_name[:10].upper()}
            )

            # Create or get the department
            department, department_created = Department.objects.get_or_create(
                school=school,
                name=department_name,
                defaults={'code': department_name[:10].upper()}
            )

            # Check if department already has an admin
            if User.objects.filter(department=department, is_department_admin=True).exists():
                messages.error(request, 'This department already has an administrator.')
                return render(request, 'registration/register.html', {
                    'form': form,
                    'secret_question': User.get_random_secret_question()
                })

            try:
                # Create the user
                user = form.save(commit=False)
                user.department = department

                # Split admin name into first and last name
                name_parts = admin_name.split()
                user.first_name = name_parts[0] if name_parts else ''
                user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                # Set secret question and answer
                user.secret_question = form.cleaned_data['secret_question']
                user.secret_answer = form.cleaned_data['secret_answer']  # Will be hashed in model's save method

                user.is_department_admin = True
                user.save()

                # Log the user in
                auth_login(request, user)

                messages.success(request, 'Registration successful!')
                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
                # Add debug print
                print(f"Error during registration: {str(e)}")
                return render(request, 'registration/register.html', {
                    'form': form,
                    'secret_question': User.get_random_secret_question()
                })
        else:
            # Form is not valid, show errors
            print("Form errors:", form.errors)
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {
        'form': form,
        'secret_question': User.get_random_secret_question()
    })


class PasswordResetRequestView(View):
    def get(self, request):
        return render(request, 'registration/password_reset_request.html')

    def post(self, request):
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            request.session['reset_user_id'] = user.id
            return redirect('password_reset_question')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')
            return redirect('password_reset_request')


class PasswordResetQuestionView(View):
    def get(self, request):
        user_id = request.session.get('reset_user_id')
        if not user_id:
            return redirect('password_reset_request')

        try:
            user = User.objects.get(id=user_id)
            return render(request, 'registration/password_reset_question.html',
                          {'secret_question': user.secret_question})
        except User.DoesNotExist:
            return redirect('password_reset_request')

    def post(self, request):
        user_id = request.session.get('reset_user_id')
        secret_answer = request.POST.get('secret_answer')

        try:
            user = User.objects.get(id=user_id)
            if user.check_secret_answer(secret_answer):
                request.session['reset_verified'] = True
                return redirect('password_reset_confirm')
            else:
                messages.error(request, 'Incorrect answer. Please try again.')
                return render(request, 'registration/password_reset_question.html',
                              {'secret_question': user.secret_question})
        except User.DoesNotExist:
            return redirect('password_reset_request')


class PasswordResetConfirmView(View):
    def get(self, request):
        if not request.session.get('reset_verified'):
            return redirect('password_reset_request')
        return render(request, 'registration/password_reset_confirm.html')

    def post(self, request):
        if not request.session.get('reset_verified'):
            return redirect('password_reset_request')

        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'registration/password_reset_confirm.html')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'registration/password_reset_confirm.html')

        user_id = request.session.get('reset_user_id')
        try:
            user = User.objects.get(id=user_id)
            user.set_password(password)
            user.save()

            # Clean up session
            del request.session['reset_user_id']
            del request.session['reset_verified']

            messages.success(request, 'Password reset successfully. You can now login with your new password.')
            return redirect('login')
        except User.DoesNotExist:
            return redirect('password_reset_request')


# views.py
@login_required(login_url='/login/')
def dashboard(request):
    department = request.user.department

    # Count students in the current department
    total_students = Student.objects.filter(department=department).count()

    # Count supervisors (if they're department-specific, add filter)
    total_supervisors = Supervisor.objects.count()

    # Count groups in the current department
    total_groups = Group.objects.filter(department=department).count()

    # Count completed allocations for the department
    completed_allocations = AllocationResult.objects.filter(
        groups__department=department
    ).distinct().count()

    # Get recent allocations for the department
    allocations = AllocationResult.objects.filter(
        groups__department=department
    ).distinct().order_by('-created_at')[:5]

    context = {
        'total_students': total_students,
        'total_supervisors': total_supervisors,
        'total_groups': total_groups,
        'completed_allocations': completed_allocations,
        'allocations': allocations,
    }
    return render(request, 'dashboard.html', context)

# views.py
@csrf_protect
def department_login(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = DepartmentLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()

            # Use Django's auth_login function with both request and user
            auth_login(request, user)

            # Handle "remember me"
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)  # Session expires on browser close

            # Redirect to next page if provided, else dashboard
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            # Form is invalid, show errors
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = DepartmentLoginForm()

    # GET request or invalid POST
    return render(request, 'registration/login.html', {'form': form})