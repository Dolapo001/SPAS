from django import template

register = template.Library()


@register.filter
def avg_field(queryset, field_name):
    """Calculate the average of a specific field in a queryset"""
    valid_values = [getattr(obj, field_name) for obj in queryset
                   if getattr(obj, field_name) is not None]
    if valid_values:
        return sum(valid_values) / len(valid_values)
    return 0


register = template.Library()


@register.filter
def get_supervisor_name(group):
    return group.supervisor.name if group.supervisor else "Not assigned"


@register.filter
def get_supervisor_email(group):
    return group.supervisor.email if group.supervisor and group.supervisor.email else ""
