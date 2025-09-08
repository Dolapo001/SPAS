from django.db import models
from frontend.models import Department


class Supervisor(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="supervisors",
        null=True, blank=True
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_supervisor_name_per_department"
            ),
            models.UniqueConstraint(
                fields=["department", "email"],
                name="unique_supervisor_email_per_department"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.department.name})"

    @property
    def current_students_count(self) -> int:
        return self.students.count()
