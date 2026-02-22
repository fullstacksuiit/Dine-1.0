from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register([Restaurant, Table])

class StaffAdmin(admin.ModelAdmin):
    list_display = ('user_username', 'get_role', 'restaurant')
    search_fields = ('user__username', 'restaurant__name')
    list_filter = ('restaurant',)
    ordering = ('restaurant', 'user__username')

    def user_username(self, obj):
        """Username"""
        return obj.user.username

    def get_role(self, obj):
        """Role"""
        # Returns the highest role for display (OWNER > MANAGER > WAITER)
        if obj.is_owner:
            return 'OWNER'
        elif obj.is_manager:
            return 'MANAGER'
        elif obj.is_waiter:
            return 'WAITER'
        return '-'

admin.site.register(Staff, StaffAdmin)

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'plan_name', 'start_date', 'end_date')
    search_fields = ('restaurant__name', 'plan_name')
    list_filter = ('plan_name', 'restaurant')
    ordering = ('-start_date',)

admin.site.register(Subscription, SubscriptionAdmin)
