import io
import json

from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST

from nacos_allocation import settings
from students.models import Student
from supervisors.models import Supervisor
from .models import Group, AllocationResult
from .forms import AllocationForm
import csv
import random
from collections import defaultdict
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import logging

logger = logging.getLogger(__name__)


@login_required(login_url='/login/')
def run_allocation(request):
    if request.method == 'POST':
        form = AllocationForm(request.POST)
        if form.is_valid():
            num_groups = form.cleaned_data['num_groups']
            method = form.cleaned_data['allocation_method']
            send_notifications = form.cleaned_data.get('send_notifications', False)
            department = request.user.department

            # Get only students from the user's department who are not already in any group
            unassigned_students = list(Student.objects.filter(
                department=department,
                groups__isnull=True
            ))
            supervisors = list(Supervisor.objects.all())

            if len(unassigned_students) == 0 or len(supervisors) == 0:
                messages.error(request, 'Need at least 1 unassigned student and 1 supervisor to run allocation.')
                return redirect('allocation:run')

            if num_groups > len(supervisors):
                messages.error(request, f'Number of groups cannot exceed number of supervisors ({len(supervisors)}).')
                return redirect('allocation:run')

            # Get supervisors without groups in previous allocations
            used_supervisor_ids = set(Group.objects.values_list('supervisor_id', flat=True))
            unused_supervisors = [s for s in supervisors if s.id not in used_supervisor_ids]

            # If we have unused supervisors, use them first
            if unused_supervisors:
                available_supervisors = unused_supervisors + [s for s in supervisors if s.id in used_supervisor_ids]
            else:
                available_supervisors = supervisors

            # Perform allocation based on method
            if method == 'grade_based':
                groups = grade_based_allocation(unassigned_students, available_supervisors, num_groups)
            elif method == 'random':
                groups = random_allocation(unassigned_students, available_supervisors, num_groups)
            else:  # balanced
                groups = balanced_allocation(unassigned_students, available_supervisors, num_groups)

            # Save allocation results
            allocation_result = AllocationResult.objects.create(
                method=method,
                num_groups=num_groups
            )

            created_groups = []
            for group_data in groups:
                group = Group.objects.create(
                    number=group_data['number'],
                    supervisor=group_data['supervisor'],
                    allocation_result=allocation_result,
                    department=department
                )
                group.students.set(group_data['students'])
                created_groups.append(group)

            # Send notifications if requested
            email_results = []
            if send_notifications:
                subject = "Project Group Allocation Notification"
                body = "You have been allocated to a project group. Please check the system for details."

                for group in created_groups:
                    result = send_emails_for_group(group, subject, body)
                    email_results.append(result)

                # Count successful emails
                successful_groups = sum(1 for r in email_results if r['success'])
                successful_students = sum(r['students_sent'] for r in email_results)

                messages.success(request,
                                 f'Successfully allocated {len(unassigned_students)} students into {num_groups} groups. '
                                 f'Email notifications sent for {successful_groups} groups ({successful_students} students).'
                                 )
            else:
                messages.success(request,
                                 f'Successfully allocated {len(unassigned_students)} students into {num_groups} groups.'
                                 )

            return redirect('allocation:results')
    else:
        form = AllocationForm()

    # Get counts for the template - filter by department
    department = request.user.department
    total_students = Student.objects.filter(department=department).count()
    unassigned_students_count = Student.objects.filter(
        department=department, groups__isnull=True
    ).count()
    total_supervisors = Supervisor.objects.count()
    previous_allocations = AllocationResult.objects.filter(
        groups__department=department
    ).distinct().order_by('-created_at')[:5]

    return render(request, 'allocation/run.html', {
        'form': form,
        'total_students': total_students,
        'unassigned_students_count': unassigned_students_count,
        'total_supervisors': total_supervisors,
        'previous_allocations': previous_allocations,
    })


def grade_based_allocation(students, supervisors, num_groups):
    # Sort students by cgpa (highest first)
    students_sorted = sorted(students, key=lambda s: s.cgpa, reverse=True)

    # Initialize groups
    groups = []
    for i in range(num_groups):
        groups.append({
            'number': i + 1,
            'supervisor': supervisors[i % len(supervisors)],
            'students': []
        })

    # First, assign at least 3 First-Class students to each group (if available)
    first_class_students = [s for s in students_sorted if s.cgpa >= 4.50]  # First class based on CGPA

    for i in range(min(3 * num_groups, len(first_class_students))):
        group_idx = i % num_groups
        groups[group_idx]['students'].append(first_class_students[i])

    # Remove assigned students
    assigned_students = set()
    for group in groups:
        assigned_students.update(group['students'])

    remaining_students = [s for s in students_sorted if s not in assigned_students]

    # Distribute remaining students round-robin
    for i, student in enumerate(remaining_students):
        group_idx = i % num_groups
        groups[group_idx]['students'].append(student)

    return groups


@login_required(login_url='/login/')
def allocation_results(request):
    department = request.user.department

    groups_qs = (
        Group.objects
        .filter(department=department)
        .select_related('supervisor', 'allocation_result')
        .prefetch_related('students')
        .annotate(
            total_students=Count('students', distinct=True),
            average_cgpa=Avg('students__cgpa'),
        )
        .order_by('-allocation_result__created_at', 'number')
    )

    paginator = Paginator(groups_qs, 20)
    page = request.GET.get('page')

    try:
        groups = paginator.page(page)
    except PageNotAnInteger:
        groups = paginator.page(1)
    except EmptyPage:
        groups = paginator.page(paginator.num_pages)

    return render(request, 'allocation/results.html', {
        'groups': groups,
        'total_groups': groups_qs.count(),
        'total_students': Student.objects.filter(department=department).count(),
        'total_supervisors': Supervisor.objects.count(),
    })


# allocation/views.py
def download_csv(request, pk=None):
    """
    If pk is provided, download that AllocationResult's CSV.
    If pk is None, download the latest AllocationResult.
    """
    department = request.user.department

    if pk is not None:
        # Fix: Use distinct() to avoid duplicate AllocationResult objects
        allocation = get_object_or_404(
            AllocationResult.objects.filter(
                groups__department=department
            ).distinct(),
            pk=pk
        )
    else:
        allocation = AllocationResult.objects.filter(
            groups__department=department
        ).distinct().order_by('-created_at').first()
        if allocation is None:
            # no allocation to download
            return HttpResponse("No allocations found.", status=404)

    # Filename with id and date for clarity
    created_str = allocation.created_at.strftime("%Y%m%d_%H%M")
    filename = f"allocation_{allocation.id}_{created_str}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    # header
    writer.writerow(['Group', 'Supervisor', 'Matric No', 'Student Name'])

    groups = allocation.groups.filter(department=department).prefetch_related('students', 'supervisor')
    for group in groups:
        supervisor_name = group.supervisor.name if getattr(group, 'supervisor', None) else ''
        for student in group.students.all():
            writer.writerow([f'Group {group.number}', supervisor_name, student.matric_no,
                             getattr(student, 'get_full_name', lambda: '')() or getattr(student, 'name', '')])

    return response

def random_allocation(students, supervisors, num_groups):
    students_copy = students[:]  # avoid mutating original
    random.shuffle(students_copy)

    groups = []
    for i in range(num_groups):
        groups.append({
            'number': i + 1,
            'supervisor': supervisors[i % len(supervisors)],
            'students': []
        })

    for i, student in enumerate(students_copy):
        group_idx = i % num_groups
        groups[group_idx]['students'].append(student)

    return groups


def balanced_allocation(students, supervisors, num_groups):
    # Group students by classification
    classified_students = defaultdict(list)
    for student in students:
        classified_students[student.classification()].append(student)

    # Sort each classification group randomly (to avoid bias)
    for classification in classified_students:
        random.shuffle(classified_students[classification])

    groups = []
    for i in range(num_groups):
        groups.append({
            'number': i + 1,
            'supervisor': supervisors[i % len(supervisors)],
            'students': []
        })

    # Distribute classification groups round-robin
    for class_group in classified_students.values():
        for i, student in enumerate(class_group):
            group_idx = i % num_groups
            groups[group_idx]['students'].append(student)

    return groups


# views.py
@login_required(login_url='/login/')
def allocation_detail(request, pk):
    try:
        department = request.user.department

        # Fix: Use distinct() to avoid duplicate AllocationResult objects
        allocation = get_object_or_404(
            AllocationResult.objects.filter(
                groups__department=department
            ).distinct(),
            id=pk
        )

        # Get all groups for this allocation
        all_groups = Group.objects.filter(
            allocation_result=allocation,
            department=department
        ).prefetch_related('students', 'supervisor').order_by('number')

        # Calculate statistics
        total_students = sum(group.students.count() for group in all_groups)
        average_group_size = total_students / len(all_groups) if all_groups else 0

        # Calculate average grade for each group
        for group in all_groups:
            group.avg_cgpa = group.students.aggregate(Avg('cgpa'))['cgpa__avg'] or 0

        # Paginate groups
        paginator = Paginator(all_groups, 10)
        page = request.GET.get('page')

        try:
            groups = paginator.page(page)
        except PageNotAnInteger:
            groups = paginator.page(1)
        except EmptyPage:
            groups = paginator.page(paginator.num_pages)

        context = {
            'allocation': allocation,
            'groups': groups,
            'total_students': total_students,
            'average_group_size': round(average_group_size, 1),
        }

        return render(request, 'allocation/detail.html', context)

    except Exception as e:
        messages.error(request, f"An error occurred while retrieving allocation details: {str(e)}")
        return redirect('allocation:results')


def send_emails_for_group(group, subject, body):
    """
    Send emails to supervisor (with CSV attachment) and to students.
    Returns a dictionary with summary and per-student errors.
    """
    supervisor = getattr(group, "supervisor", None)
    students = group.students.all()

    result = {
        "group_id": group.id,
        "success": False,
        "supervisor_email_sent": False,
        "students_sent": 0,
        "students_failed": [],   # list of {"student_id", "email", "error"}
        "errors": [],            # general errors
    }

    # Optional: quick sanity check for student emails (log)
    student_emails = [s.email for s in students]
    logger.debug("Preparing to send emails for group %s. Student emails: %s", group.id, student_emails)

    try:
        # open a single SMTP connection and reuse it
        connection = get_connection(fail_silently=False)
        connection.open()

        # Send supervisor email if present
        if supervisor and getattr(supervisor, "email", None):
            try:
                supervisor_ctx = {
                    "group": group,
                    "supervisor": supervisor,
                    "students": students,
                    "body": body,
                }
                html_content = render_to_string("emails/supervisor_email.html", supervisor_ctx)
                text_content = strip_tags(html_content) or body

                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[supervisor.email],
                    connection=connection
                )
                email.attach_alternative(html_content, "text/html")

                # CSV attachment for supervisor
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["Matric No", "Full Name", "CGPA", "Email"])
                for s in students:
                    writer.writerow([s.matric_no, s.full_name or "", str(s.cgpa), s.email or ""])
                csv_data = csv_buffer.getvalue()
                csv_buffer.close()
                filename = f"group_{group.number}_students.csv"
                email.attach(filename, csv_data, "text/csv")

                email.send()
                result["supervisor_email_sent"] = True
            except Exception as sup_exc:
                logger.exception("Supervisor email send failed for group %s", group.id)
                result["errors"].append(f"Supervisor send error: {str(sup_exc)}")

        # Send individual student emails (each has its own try/except)
        for student in students:
            if not getattr(student, "email", None):
                # No email address — record as failed/skip
                result["students_failed"].append({
                    "student_id": getattr(student, "id", None),
                    "email": None,
                    "error": "missing email"
                })
                continue

            try:
                student_ctx = {
                    "student": student,
                    "supervisor": supervisor,
                    "group": group,
                    "body": body,
                }
                html_content = render_to_string("emails/student_email.html", student_ctx)
                text_content = strip_tags(html_content) or body

                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[student.email],
                    connection=connection
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                result["students_sent"] += 1
            except Exception as stud_exc:
                logger.exception("Failed to send to student %s (group %s)", getattr(student, "id", None), group.id)
                result["students_failed"].append({
                    "student_id": getattr(student, "id", None),
                    "email": getattr(student, "email", None),
                    "error": str(stud_exc)
                })

        # close connection
        try:
            connection.close()
        except Exception:
            logger.debug("Connection close failed (ignored)")

        result["success"] = True
    except Exception as e:
        # global failure (e.g., cannot open connection at all)
        logger.exception("Global email send failure for group %s", group.id)
        result["errors"].append(str(e))

    return result


@login_required
@require_POST
def send_group_email(request):
    """
    Expects JSON payload: { groupId, subject, body }
    Sends the supervisor email (with attachment CSV) and individual student emails.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    group_id = payload.get("groupId")
    subject = payload.get("subject", "Group Allocation Info")
    body = payload.get("body", "").strip()

    if not group_id:
        return HttpResponseBadRequest("Missing groupId.")

    group = get_object_or_404(Group, pk=group_id)
    result = send_emails_for_group(group, subject, body)

    return JsonResponse({"status": "ok", "results": result})
