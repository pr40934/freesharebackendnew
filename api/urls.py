# myapp/urls.py
from django.urls import path
from .views import GetPresignedUrlsView, CompleteMultipartUploadView, \
      PresignedThumbNailUploadView, TriggerDeleteQueueView, VideoDataSaveView, \
      GetUserVideosView


urlpatterns = [
    # path('products/', ProductListCreateAPIView.as_view(), name='product-list-create'),  # List and Create Products
    # path('products/<int:pk>/', ProductDetailAPIView.as_view(), name='product-detail'),  # Retrieve, Update, Delete Product
    path("get_video_presigned_urls/", GetPresignedUrlsView.as_view(), name="get_video_presigned_urls"),
    path('complete_multipart_upload/', CompleteMultipartUploadView.as_view(), name='complete_multipart_upload'),
    path('save_thumbnail_imagePath/', PresignedThumbNailUploadView.as_view(), name='save_thumbnail_imagePath'),
    path('trigger-delete-queue/', TriggerDeleteQueueView.as_view(), name='trigger-delete-queue'),
    path("video_data_save/", VideoDataSaveView.as_view(), name="video_data_save"),
    path('user-videos/<int:user_id>/', GetUserVideosView.as_view(), name='get_user_videos')
]  