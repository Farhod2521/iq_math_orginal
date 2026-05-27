from django.urls import path
from .views import (
    CategoryCRUDAPIView, TagCRUDAPIView, BookCRUDAPIView,
    BookListForUserAPIView, BookPurchaseAPIView,
    MyPurchasedBooksAPIView, AdminOfflineOrderAPIView,
)

urlpatterns = [
    # Categories
    path('categories/', CategoryCRUDAPIView.as_view(), name='book-category-list'),
    path('categories/<int:pk>/', CategoryCRUDAPIView.as_view(), name='book-category-detail'),

    # Tags
    path('tags/', TagCRUDAPIView.as_view(), name='book-tag-list'),
    path('tags/<int:pk>/', TagCRUDAPIView.as_view(), name='book-tag-detail'),

    # Books CRUD (superadmin)
    path('books/', BookCRUDAPIView.as_view(), name='book-list'),
    path('books/<int:pk>/', BookCRUDAPIView.as_view(), name='book-detail'),

    # Foydalanuvchi uchun kitoblar (role asosida)
    path('my-books/', BookListForUserAPIView.as_view(), name='book-my-list'),
    path('my-books/<int:pk>/', BookListForUserAPIView.as_view(), name='book-my-detail'),

    # Sotib olish va xaridlar tarixi (admin + user)
    path('purchase/', BookPurchaseAPIView.as_view(), name='book-purchase'),

    # Foydalanuvchi o'zi sotib olgan kitoblar (online/offline ajratilgan)
    path('my-purchases/', MyPurchasedBooksAPIView.as_view(), name='book-my-purchases'),

    # Admin: offline buyurtmalarni boshqarish
    path('offline-orders/', AdminOfflineOrderAPIView.as_view(), name='book-offline-orders'),
    path('offline-orders/<int:pk>/', AdminOfflineOrderAPIView.as_view(), name='book-offline-order-detail'),
]
