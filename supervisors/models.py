# supervisors/models.py
from django.db import models
from django.db.models import Count


class Supervisor(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=254, unique=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def current_students_count(self) -> int:
        # Use the reverse relationship from Student model
        return self.students.count()