from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from sale.models.course import Course
from sale.models.menu import Menu
from sale.models.kot import KOT
from sale.models.bill import Bill


@receiver(post_save, sender=Course)
def add_course_to_menu_ordering(sender, instance, created, **kwargs):
    if created:
        menu = Menu.get_or_create_menu_by_restaurant(instance.restaurant)
        if menu:
            # Add the new course's id to the ordering if not already present
            course_id = str(instance.id)
            if course_id not in menu.ordering:
                menu.ordering.append(course_id)
                menu.save()


@receiver(post_delete, sender=Course)
def remove_course_from_menu_ordering(sender, instance, **kwargs):
    menu = Menu.get_menu_by_restaurant(instance.restaurant)
    if menu:
        course_id = str(instance.id)
        if course_id in menu.ordering:
            menu.ordering.remove(course_id)
            menu.save()


@receiver(post_save, sender=Bill)
def complete_kots_on_bill_completed(sender, instance, **kwargs):
    """
    If a bill is completed (active=True), mark all non-deleted/non-cancelled KOTs as completed.
    """
    if instance.active:
        return
    kots = instance.kots.filter(is_deleted=False).exclude(
        status=KOT.Status.CANCELLED.value
    )
    kots.update(status=KOT.Status.COMPLETED.value, updated_by=instance.updated_by)
