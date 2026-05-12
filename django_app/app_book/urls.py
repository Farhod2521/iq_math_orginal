from django.urls import path
from .views import CategoryCRUDAPIView, TagCRUDAPIView, BookCRUDAPIView

urlpatterns = [
    # Categories
    path('categories/', CategoryCRUDAPIView.as_view(), name='book-category-list'),
    path('categories/<int:pk>/', CategoryCRUDAPIView.as_view(), name='book-category-detail'),

    # Tags
    path('tags/', TagCRUDAPIView.as_view(), name='book-tag-list'),
    path('tags/<int:pk>/', TagCRUDAPIView.as_view(), name='book-tag-detail'),

    # Books
    path('books/', BookCRUDAPIView.as_view(), name='book-list'),
    path('books/<int:pk>/', BookCRUDAPIView.as_view(), name='book-detail'),
]
