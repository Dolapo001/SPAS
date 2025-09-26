from django.db import models
from students.models import Student
from supervisors.models import Supervisor


class Group(models.Model):
    number = models.PositiveIntegerField()
    supervisor = models.OneToOneField(
        "supervisors.Supervisor",
        on_delete=models.CASCADE,
        related_name="group",
        blank=True,
        null=True
    )
    department = models.ForeignKey(
        "frontend.Department",
        on_delete=models.CASCADE,
        related_name="groups",
        blank=True,
        null=True
    )
    students = models.ManyToManyField(Student, related_name="groups", blank=True)
    allocation_result = models.ForeignKey(
        "AllocationResult",
        on_delete=models.CASCADE,
        related_name="groups",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['number']
        unique_together = ['number', 'supervisor', 'allocation_result']

    def __str__(self):
        return f"Group {self.number} - {self.supervisor.name if self.supervisor else 'No Supervisor'} - {self.department.name if self.department else 'No Department'}"

    @property
    def average_grade(self):
        if self.students.exists():
            total = sum(float(student.cgpa) for student in self.students.all())
            return total / self.students.count()
        return 0.0

    def student_count(self):
        return self.students.count()
    student_count.short_description = 'Student Count'


class AllocationResult(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=50)
    num_groups = models.PositiveIntegerField()

    def __str__(self):
        return f"Allocation {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def departments(self):
        return ", ".join(set(group.department.name for group in self.groups.all() if group.department))
    departments.short_description = 'Departments'

    def total_students(self):
        return sum(group.students.count() for group in self.groups.all())
    total_students.short_description = 'Total Students'