from django.contrib import admin
from .models import Workplace, GeneralSpecialty, SubSpecialty, Employee, Leave, UserProfile, ActivityLog
from .models import Workplace, Department, GeneralSpecialty, SubSpecialty, Employee, Leave, UserProfile, ActivityLog
admin.site.register(Workplace)
admin.site.register(GeneralSpecialty)
admin.site.register(SubSpecialty)
admin.site.register(Employee)
admin.site.register(Leave)
admin.site.register(UserProfile)
admin.site.register(ActivityLog)
admin.site.register(Department)