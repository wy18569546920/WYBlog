from django.contrib import admin
from users.models import User


# Register your models here.
# 注册模型
class UserAdmin(admin.ModelAdmin):
    list_display = 'username', 'mobile', 'is_superuser', 'last_login'
    search_fields = 'username', 'mobile'
    list_filter = 'is_superuser',
    list_per_page = 20


admin.site.register(User, UserAdmin)
