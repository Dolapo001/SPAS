from django import forms

from allocation.models import Group


class AllocationForm(forms.Form):
    ALLOCATION_METHODS = [
        ('grade_based', 'Grade-Based Allocation'),
        ('random', 'Random Allocation'),
        ('balanced', 'Balanced Allocation'),
    ]

    num_groups = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    allocation_method = forms.ChoiceField(
        choices=ALLOCATION_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    preserve_existing = forms.BooleanField(required=False, initial=False)
    send_notifications = forms.BooleanField(required=False, initial=True)

#
# class GroupForm(forms.ModelForm):
#     class Meta:
#         model = Group
#         fields = ["name", "supervisor", "department", "students"]
#
#     def clean(self):
#         cleaned = super().clean()
#         supervisor = cleaned.get("supervisor")
#         department = cleaned.get("department")
#
#         if supervisor and department:
#             qs = Group.objects.filter(supervisor=supervisor, department=department)
#             # When editing an existing group, exclude itself
#             if self.instance.pk:
#                 qs = qs.exclude(pk=self.instance.pk)
#             if qs.exists():
#                 raise forms.ValidationError(
#                     "This supervisor already has a group in that department."
#                 )
#         return cleaned
#
