from django.db import models
from students.models import Student
from supervisors.models import Supervisor


class Group(models.Model):
    number = models.PositiveIntegerField()
    supervisor = models.OneToOneField(  # each supervisor has only one group
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
        return f"Group {self.number} - {self.supervisor.name if self.supervisor else 'No Supervisor'}"

    @property
    def average_grade(self):
        if self.students.exists():
            # Calculate average CGPA of all students in this group
            total = sum(float(student.cgpa) for student in self.students.all())
            return total / self.students.count()
        return 0.0


class AllocationResult(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=50)
    num_groups = models.PositiveIntegerField()

    def __str__(self):
        return f"Allocation {self.created_at.strftime('%Y-%m-%d %H:%M')}"
