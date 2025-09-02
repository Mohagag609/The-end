from django.contrib import admin
from .models import Currency, VoucherSequence, SystemSettings

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'is_default']
    list_filter = ['is_default']
    search_fields = ['code', 'name']

@admin.register(VoucherSequence)
class VoucherSequenceAdmin(admin.ModelAdmin):
    list_display = ['voucher_type', 'project', 'prefix', 'next_number', 'year']
    list_filter = ['voucher_type', 'year']
    search_fields = ['project__name', 'prefix']

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['allow_negative_wallet', 'default_credit_limit', 'auto_generate_voucher_numbers']