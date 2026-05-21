from django.contrib import admin
from .models import Category, Tag, Book, BookPurchase


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
