from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from frontend.models import Department


class Student(models.Model):
    matric_no = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=254, unique=False, null=True, blank=True)
    cgpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="students",
        null=True,
        blank=True
    )
    # Optional supervisor relation to allow download_template to list supervisor students.
    supervisor = models.ForeignKey(
        'supervisors.Supervisor',
        on_delete=models.SET_NULL,
        related_name='students',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-cgpa']

    def __str__(self):
        return f"{self.full_name or self.matric_no} ({self.matric_no})"

    def grade_points(self):
        """
        Convert CGPA to grade points for sorting
        """
        return self.cgpa

    def classification(self):
        if 4.50 <= float(self.cgpa) <= 5.00:
            return "First Class"
        elif 3.50 <= float(self.cgpa) <= 4.49:
            return "Second Class Upper"
        elif 2.40 <= float(self.cgpa) <= 3.49:
            return "Second Class Lower"
        elif 1.50 <= float(self.cgpa) <= 2.39:
            return "Third Class"
        elif 1.00 <= float(self.cgpa) <= 1.49:
            return "Pass"
        else:
            return "Fail"
