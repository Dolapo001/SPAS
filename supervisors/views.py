# supervisors/views.py
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse

from students.models import Student
from .models import Supervisor
from .forms import SupervisorForm, SupervisorUploadForm
import csv
import io

PER_PAGE = 20  # rows per page for pagination


@login_required(login_url='/login/')
def supervisor_list(request):
    department = getattr(request.user, "department", None)

    # If user has no department, return empty results
    if not department:
        return render(request, 'supervisors/list.html', {
            'supervisors': Paginator(Supervisor.objects.none(), PER_PAGE).get_page(1),
            'has_supervisors': False,
        })

    # 1) Build base qs scoped to the user's department
    base_qs = Supervisor.objects.filter(department=department).select_related('department').order_by('name')

    # 2) Try to detect the reverse accessor name for Student -> Supervisor
    student_accessor = None
    for rel in Supervisor._meta.get_fields():
        # one_to_many covers ForeignKey from Student -> Supervisor
        if getattr(rel, "one_to_many", False) and getattr(rel, "related_model", None):
            if rel.related_model.__name__ == "Student":
                student_accessor = rel.get_accessor_name()
                break

    if student_accessor:
        # Annotate count directly in the Supervisor queryset (single DB hit)
        # If you want only active students counted, use Count(student_accessor, filter=Q(...))
        qs = base_qs.annotate(current_students_count=Count(student_accessor))
        # If you want to sort by busiest supervisors, you could add:
        # qs = qs.order_by('-current_students_count', 'name')
    else:
        # Fallback: no direct Student reverse relation detected—use base queryset
        qs = base_qs

    # 3) Paginate
    paginator = Paginator(qs, PER_PAGE)
    page_number = request.GET.get('page', 1)
    supervisors_page = paginator.get_page(page_number)

    # 4) If we couldn't annotate above, compute per-page counts efficiently
    if not student_accessor and supervisors_page.object_list:
        supervisor_ids = [s.id for s in supervisors_page.object_list]
        counts = (
            Student.objects
            .filter(supervisor_id__in=supervisor_ids)  # uses lower-level FK id lookup; change if your FK name differs
            .values('supervisor_id')
            .annotate(cnt=Count('id'))
        )
        counts_map = {c['supervisor_id']: c['cnt'] for c in counts}
        for s in supervisors_page.object_list:
            s.current_students_count = counts_map.get(s.id, 0)
    else:
        # If annotated, each supervisor already has current_students_count (or we ensure attribute exists)
        for s in supervisors_page.object_list:
            if not hasattr(s, 'current_students_count'):
                s.current_students_count = 0

    has_supervisors = paginator.count > 0

    return render(request, 'supervisors/list.html', {
        'supervisors': supervisors_page,
        'has_supervisors': has_supervisors,
    })

@login_required(login_url='/login/')
def supervisor_create(request):
    if request.method == 'POST':
        form = SupervisorForm(request.POST)
        if form.is_valid():
            supervisor = form.save(commit=False)
            supervisor.department = request.user.department   # 🔑 tie to user’s department
            supervisor.save()
            messages.success(request, 'Supervisor created successfully!')
            return redirect('supervisors:list')
    else:
        form = SupervisorForm()
    return render(request, 'supervisors/create.html', {'form': form})


@login_required(login_url='/login/')
def upload_supervisors(request):
    if request.method == "POST":
        form = SupervisorUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']

            # Check file type
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "File must be a CSV")
                return redirect("supervisors:upload")

            # Read file
            data = csv_file.read().decode("utf-8")
            io_string = io.StringIO(data)

            skip_header = form.cleaned_data.get("skip_header", True)
            update_existing = form.cleaned_data.get("update_existing", False)

            reader = csv.reader(io_string)
            if skip_header:
                next(reader, None)  # skip the header row

            created_count = 0
            updated_count = 0
            errors = []

            for row_num, row in enumerate(reader, 1 if skip_header else 0):
                if not row:  # Skip empty rows
                    continue

                name = row[0].strip()
                if not name:
                    errors.append(f"Row {row_num}: Name is required")
                    continue

                email = row[1].strip() if len(row) > 1 else None
                if email == '':
                    email = None

                try:
                    if update_existing:
                        supervisor, created = Supervisor.objects.update_or_create(
                            name=name,
                            department=request.user.department,
                            defaults={'email': email}
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # FIXED: Include department in both lookup and defaults
                        supervisor, created = Supervisor.objects.get_or_create(
                            name=name,
                            department=request.user.department,  # Added this line
                            defaults={'email': email}
                        )
                        if created:
                            created_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    messages.error(request, error)
                if len(errors) > 5:
                    messages.error(request, f"... and {len(errors) - 5} more errors")

            if created_count or updated_count:
                success_msg = f"Successfully processed {created_count + updated_count} supervisors"
                if created_count:
                    success_msg += f" ({created_count} created"
                    if updated_count:
                        success_msg += f", {updated_count} updated)"
                    else:
                        success_msg += ")"
                elif updated_count:
                    success_msg += f" ({updated_count} updated)"

                messages.success(request, success_msg)

            return redirect("supervisors:list")
    else:
        form = SupervisorUploadForm()

    return render(request, "supervisors/upload.html", {"form": form})

@login_required(login_url='/login/')
def download_supervisor_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="supervisor_template.csv"'

    writer = csv.writer(response)
    writer.writerow(['name', 'email'])
    writer.writerow(['Dr. John Smith', 'john.smith@university.edu'])
    writer.writerow(['Prof. Jane Doe', 'jane.doe@university.edu'])
    writer.writerow(['Dr. Michael Brown', ''])  # Example without email

    return response


@login_required(login_url='/login/')
def supervisor_edit(request, pk):
    supervisor = get_object_or_404(Supervisor, pk=pk)
    if request.method == 'POST':
        form = SupervisorForm(request.POST, instance=supervisor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supervisor updated successfully!')
            return redirect('supervisors:list')
    else:
        form = SupervisorForm(instance=supervisor)
    return render(request, 'supervisors/edit.html', {'form': form, 'supervisor': supervisor})


@login_required(login_url='/login/')
def supervisor_delete(request, pk):
    supervisor = get_object_or_404(Supervisor, pk=pk, department=request.user.department)
    if request.method == 'POST':
        supervisor.delete()
        messages.success(request, 'Supervisor deleted successfully!')
        return redirect('supervisors:list')
    return redirect('supervisors:list')