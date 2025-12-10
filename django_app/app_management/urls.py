from django.urls import path
from .views import ( SystemSettingsListView, FAQListView, ProductListView, FullStatisticsAPIView, 
                    BannerListView, MotivationAPIView, ElonListAPIView, UploadSingleFileAPIView, DeleteFileAPIView )
from .VIEW.elonapiviewcrud import ElonCRUDAPIView
from .VIEW.motivationapiviewcrud import  MotivationCRUDAPIView
from .VIEW.systemsettingsapiviewcrud import  SystemSettingsCRUDAPIView

urlpatterns = [
    path('system-settings/', SystemSettingsListView.as_view(), name='system-settings-list'),
    path('banner/', BannerListView.as_view(), name='system-settings-list'),
    path('faqs/', FAQListView.as_view(), name='faq-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('statistics/', FullStatisticsAPIView.as_view(), name='statistics'),


    ######################  MOBILE APP ####################################
    path('app/motivation-list/', MotivationAPIView.as_view(), name='statistics'),
    path('app/elon-list/', ElonListAPIView.as_view(), name='statistics'),
    path("upload-file/", UploadSingleFileAPIView.as_view(), name="upload-file"),
    path("upload-file-delete/<int:id>/", DeleteFileAPIView.as_view(), name="upload-file"),


    ##########################  SUPERADMIN ###############################################
    path("superadmin/elon/", ElonCRUDAPIView.as_view()),          # GET (list) | POST (create)
    path("superadmin/elon/<int:pk>/", ElonCRUDAPIView.as_view()),
    path("superadmin/motivation/", MotivationCRUDAPIView.as_view()),          # GET (list) | POST (create)
    path("superadmin/motivation/<int:pk>/", MotivationCRUDAPIView.as_view()), # GET | PUT | DELETE
    path("system-settings/", SystemSettingsCRUDAPIView.as_view()),          # GET list, POST create
    path("system-settings/<int:pk>/", SystemSettingsCRUDAPIView.as_view()), # GET detail, PUT, DELETE

]
