from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Company, User, Village


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "standard_bag_weight_kg", "created_at")


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "prefecture", "status")
    list_filter = ("company", "status")
    search_fields = ("name", "prefecture")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("code",)
    list_display = ("code", "name", "company", "role", "is_active")
    list_filter = ("company", "role", "is_active")
    search_fields = ("code", "name", "phone")
    fieldsets = (
        (None, {"fields": ("code", "password")}),
        ("Informations", {"fields": ("name", "phone", "company", "role")}),
        (
            "Droits",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Sécurité", {"fields": ("failed_login_attempts", "locked_until")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("code", "name", "company", "role", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("failed_login_attempts", "locked_until")
