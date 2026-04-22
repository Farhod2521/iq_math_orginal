from django.urls import path
from .views import ( FAQListView, ProductListView, FullStatisticsAPIView,
                    BannerListView, MotivationAPIView, ElonListAPIView, ElonDetailAPIView,
                    UploadSingleFileAPIView, DeleteFileAPIView, UploadedFileListAPIView,
                    MathematicianListAPIView, MathematicianDetailAPIView)
from .VIEW.elonapiviewcrud import ElonCRUDAPIView
from .VIEW.motivationapiviewcrud import  MotivationCRUDAPIView
from .VIEW.systemsettingsapiviewcrud import  SystemSettingsCRUDAPIView
from .VIEW.andriod_version import AndroidVersionAPIView
from .VIEW.dailycoinsettingscrud import DailyCoinSettingsCRUDAPIView
from .VIEW.mathematiciancrud import MathematicianCRUDAPIView
from .VIEW.referral_coupon_settings_crud import ReferralCouponSettingsCRUDAPIView
from .VIEW.banner_crud import BannerCRUDAPIView
from .VIEW.tag_crud import TagCRUDAPIView
from .VIEW.faq_crud import FAQCRUDAPIView
from .VIEW.category_supermentor_crud import CategoryCRUDAPIView
from .VIEW.product_supermentor_crud import ProductCRUDAPIView
from .VIEW.conversion_rate_crud import ConversionRateCRUDAPIView
from .VIEW.solution_status_crud import SolutionStatusCRUDAPIView
from .VIEW.upload_setting_crud import UploadSettingCRUDAPIView
urlpatterns = [
    path('banner/', BannerListView.as_view(), name='system-settings-list'),
    path('faqs/', FAQListView.as_view(), name='faq-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('statistics/', FullStatisticsAPIView.as_view(), name='statistics'),


    ######################  MOBILE APP ####################################
    path('app/motivation-list/', MotivationAPIView.as_view(), name='statistics'),
    path('app/elon-list/', ElonListAPIView.as_view(), name='statistics'),
    path('app/elon-list/<int:id>/', ElonDetailAPIView.as_view(), name='elon-detail'),
    path("upload-file/", UploadSingleFileAPIView.as_view(), name="upload-file"),
    path("upload-file-delete/<int:file_id>/", DeleteFileAPIView.as_view(), name="upload-file-delete"),
    path("upload-file-list/", UploadedFileListAPIView.as_view(), name="upload-file-list"),
    path("upload-file-list/<int:file_id>/", UploadedFileListAPIView.as_view(), name="upload-file-detail"),
    path("mobile/version/", AndroidVersionAPIView.as_view()),
    path("mobile/mathematicians/", MathematicianListAPIView.as_view(), name="mathematician-list"),
    path("mobile/mathematicians/<int:id>/", MathematicianDetailAPIView.as_view(), name="mathematician-detail"),



    ##########################  SUPERADMIN ###############################################
    path("superadmin/elon/", ElonCRUDAPIView.as_view()),          # GET (list) | POST (create)
    path("superadmin/elon/<int:pk>/", ElonCRUDAPIView.as_view()),
    path("superadmin/motivation/", MotivationCRUDAPIView.as_view()),          # GET (list) | POST (create)
    path("superadmin/motivation/<int:pk>/", MotivationCRUDAPIView.as_view()), # GET | PUT | DELETE
    path("system-settings/", SystemSettingsCRUDAPIView.as_view(), name="system-settings-crud"),

    path("daily-coin-settings/", DailyCoinSettingsCRUDAPIView.as_view()),
    path("daily-coin-settings/<int:pk>/", DailyCoinSettingsCRUDAPIView.as_view()),

    path("superadmin/category/", CategoryCRUDAPIView.as_view()),           # GET list | POST create
    path("superadmin/category/<int:pk>/", CategoryCRUDAPIView.as_view()),  # GET detail | PUT | DELETE

    path("superadmin/product/", ProductCRUDAPIView.as_view()),
    path("superadmin/product/<int:pk>/", ProductCRUDAPIView.as_view()),

    path("superadmin/conversion-rate/", ConversionRateCRUDAPIView.as_view()),

    path("superadmin/mathematician/", MathematicianCRUDAPIView.as_view()),
    path("superadmin/mathematician/<int:pk>/", MathematicianCRUDAPIView.as_view()),

    path("superadmin/referral-coupon-settings/", ReferralCouponSettingsCRUDAPIView.as_view()),

    path("superadmin/banner/", BannerCRUDAPIView.as_view()),
    path("superadmin/banner/<int:pk>/", BannerCRUDAPIView.as_view()),

    path("superadmin/tag/", TagCRUDAPIView.as_view()),
    path("superadmin/tag/<int:pk>/", TagCRUDAPIView.as_view()),

    path("superadmin/faq/", FAQCRUDAPIView.as_view()),
    path("superadmin/faq/<int:pk>/", FAQCRUDAPIView.as_view()),

    path("superadmin/solution-status/", SolutionStatusCRUDAPIView.as_view()),
    path("superadmin/solution-status/<int:pk>/", SolutionStatusCRUDAPIView.as_view()),

    path("superadmin/upload-setting/", UploadSettingCRUDAPIView.as_view()),
    path("superadmin/upload-setting/<int:pk>/", UploadSettingCRUDAPIView.as_view()),
]
