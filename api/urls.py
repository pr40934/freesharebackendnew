
# api/urls.py
from django.urls import path
from .views import (
    # Auth Endpoints (NEW)
    OAuthCallbackView,
    ProfileView,
    SessionsView,
    LogoutView,
    LogoutAllView,
    # Video Endpoints (EXISTING)
    GetPresignedUrlsView,
    CompleteMultipartUploadView,
    PresignedThumbNailUploadView,
    TriggerDeleteQueueView,
    VideoDataSaveView,
    GetUserVideosView,
    GetVideoDetailsView,
    VideoViewCreateAPIView,
    Test
)

urlpatterns = [
    # ============ AUTH ENDPOINTS (NEW) ============
    path('auth/callback/', OAuthCallbackView.as_view(), name='oauth_callback'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('sessions/', SessionsView.as_view(), name='sessions'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout-all/', LogoutAllView.as_view(), name='logout_all'),
    
    # ============ VIDEO ENDPOINTS (EXISTING) ============
    path("get_video_presigned_urls/", GetPresignedUrlsView.as_view(), name="get_video_presigned_urls"),
    path('complete_multipart_upload/', CompleteMultipartUploadView.as_view(), name='complete_multipart_upload'),
    path('save_thumbnail_imagePath/', PresignedThumbNailUploadView.as_view(), name='save_thumbnail_imagePath'),
    path('trigger-delete-queue/', TriggerDeleteQueueView.as_view(), name='trigger-delete-queue'),
    path("video_data_save/", VideoDataSaveView.as_view(), name="video_data_save"),
    path('user-videos/', GetUserVideosView.as_view(), name='get_user_videos'),
    path('video-details/', GetVideoDetailsView.as_view(), name='video_details'),
    path('view/', VideoViewCreateAPIView.as_view(), name='view'),
    path('test/', Test.as_view(), name='view'),
]
