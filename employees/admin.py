from django.contrib import admin

from .models import (
    ActivityLog,
    Department,
    Employee,
    GeneralSpecialty,
    Leave,
    SubSpecialty,
    UserProfile,
    Workplace,
)

admin.site.register(Workplace)
admin.site.register(Department)
admin.site.register(GeneralSpecialty)
admin.site.register(SubSpecialty)
admin.site.register(Employee)
admin.site.register(Leave)
admin.site.register(UserProfile)
admin.site.register(ActivityLog)