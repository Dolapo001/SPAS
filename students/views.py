from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse

from supervisors.models import Supervisor
from .models import Student
from .forms import StudentForm, StudentUploadForm
import csv
import io

PER_PAGE = 20  # rows per page for pagination


@login_required(login_url='/login/')
def student_list(request):
    # Filter students by the current user's department
    department = request.user.department
    qs = Student.objects.filter(department=department).order_by('-cgpa', 'matric_no')

    # Prefetch related groups to optimize queries
    qs = qs.prefetch_related('groups')

    paginator = Paginator(qs, PER_PAGE)
    page_number = request.GET.get('page', 1)
    students = paginator.get_page(page_number)

    has_students = qs.exists()

    return render(request, 'students/list.html', {
        'students': students,
        'has_students': has_students,
    })


# views.py
@login_required(login_url='/login/')
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.department = request.user.department  # Set the department
            student.save()
            messages.success(request, 'Student created successfully!')
            return redirect('students:list')
    else:
        form = StudentForm()
    return render(request, 'students/create.html', {'form': form})


# views.py
# views.py
@login_required(login_url='/login/')
def student_upload(request):
    if request.method == 'POST':
        form = StudentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            skip_header = form.cleaned_data['skip_header']
            update_existing = form.cleaned_data['update_existing']

            # Get current user's department
            current_department = request.user.department

            # Process CSV file
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)

                if skip_header:
                    next(reader)  # Skip header row

                success_count = 0
                error_count = 0
                errors = []

                for row_num, row in enumerate(reader, 1):
                    if len(row) < 2:  # Ensure at least matric_no, gpa
                        error_count += 1
                        errors.append(f"Row {row_num}: Not enough columns")
                        continue

                    matric_no = row[0].strip()
                    cgpa_str = row[1].strip()

                    # Skip empty rows
                    if not matric_no and not cgpa_str:
                        continue

                    try:
                        cgpa = float(cgpa_str)
                    except ValueError:
                        error_count += 1
                        errors.append(f"Row {row_num}: Invalid CGPA format '{cgpa_str}'")
                        continue

                    if not (0.0 <= cgpa <= 5.0):  # validate Nigerian GPA range
                        error_count += 1
                        errors.append(f"Row {row_num}: CGPA {cgpa} out of range (0.0-5.0)")
                        continue

                    try:
                        if update_existing:
                            student, created = Student.objects.update_or_create(
                                matric_no=matric_no,
                                defaults={'cgpa': cgpa, 'department': current_department}
                            )
                        else:
                            # Only create if doesn't exist
                            student, created = Student.objects.get_or_create(
                                matric_no=matric_no,
                                defaults={'cgpa': cgpa, 'department': current_department}
                            )

                        if created:
                            success_count += 1
                        else:
                            # Student already exists and we're not updating
                            error_count += 1
                            errors.append(f"Row {row_num}: Student {matric_no} already exists")

                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {row_num}: Error saving student - {str(e)}")
                        continue

                messages.success(request,
                                 f'Successfully processed {success_count} students. {error_count} errors occurred.')

                # Store errors in session for detailed view if needed
                if errors:
                    request.session['upload_errors'] = errors[:10]  # Show first 10 errors

            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')

            return redirect('students:list')
    else:
        form = StudentUploadForm()

    # Retrieve any errors from session
    errors = request.session.pop('upload_errors', [])

    return render(request, 'students/upload.html', {
        'form': form,
        'errors': errors
    })


@login_required(login_url='/login/')
def download_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_allocation_template.csv"'

    writer = csv.writer(response)

    # Check the correct related_name in your model and adjust accordingly
    supervisors = Supervisor.objects.prefetch_related("students").all()  # Use the correct related_name
    if not supervisors:
        writer.writerow(['matric_no', 'cgpa', 'email', 'full_name'])
        writer.writerow(['BU22CSC1001', '4.80', 'johndoe@gmail.com', 'John Doe'])
    else:
        for supervisor in supervisors:
            writer.writerow(['Supervisor', supervisor.name])
            # Use the correct related_name here as well
            students = supervisor.students.all().order_by('-cgpa')  # Adjust related_name
            for student in students:
                writer.writerow([f"  Matric Number {student.matric_no} | Grade {student.cgpa}"])
            writer.writerow([])

    return response


@login_required(login_url='/login/')
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('students:list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/edit.html', {'form': form, 'student': student})


@login_required(login_url='/login/')
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully!')
        return redirect('students:list')
    return redirect('students:list')
