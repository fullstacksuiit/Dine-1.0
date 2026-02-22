from django import template

register = template.Library()

@register.simple_tag
def user_in_group(user, *group_names):
    """
    Usage: {% user_in_group request.user 'manager' 'owner' as is_manager_or_owner %}
    Returns True if user is in any of the given groups.
    """
    return user.groups.filter(name__in=[g.upper() for g in group_names] if group_names else []).exists()
