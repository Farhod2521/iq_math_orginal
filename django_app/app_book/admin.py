from django.contrib import admin
from .models import Category, Tag, Book, BookPurchase, OfflineBookOrder


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price', 'status', 'date', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['name']
    filter_horizontal = ['tags']


@admin.register(BookPurchase)
class BookPurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'payment_method', 'paid_amount', 'purchased_at']
    list_filter = ['payment_method']
    search_fields = ['user__phone', 'book__name']
    readonly_fields = ['purchased_at']


@admin.register(OfflineBookOrder)
class OfflineBookOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user', 'get_book', 'delivery_status', 'phone', 'created_at', 'updated_at']
    list_filter = ['delivery_status']
    search_fields = ['purchase__user__phone', 'purchase__book__name', 'phone']
    readonly_fields = ['created_at', 'updated_at']

    def get_user(self, obj):
        return obj.purchase.user.phone
    get_user.short_description = "Foydalanuvchi"

    def get_book(self, obj):
        return obj.purchase.book.name
    get_book.short_description = "Kitob"
