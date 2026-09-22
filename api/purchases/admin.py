from django.contrib import admin

from .models import Purchase, PurchaseHistory, PurchaseSequence


class PurchaseHistoryInline(admin.TabularInline):
    model = PurchaseHistory
    extra = 0
    readonly_fields = ("action", "user", "reason", "changes", "at")
    can_delete = False


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "number", "company", "village", "collector", "seller_name",
        "bags", "amount", "status", "needs_review", "purchased_at",
    )
    list_filter = ("company", "status", "needs_review", "village")
    search_fields = ("number", "seller_name", "id")
    inlines = [PurchaseHistoryInline]
    readonly_fields = ("id", "amount", "version", "created_at", "updated_at")


@admin.register(PurchaseSequence)
class PurchaseSequenceAdmin(admin.ModelAdmin):
    list_display = ("company", "year", "last_number")
