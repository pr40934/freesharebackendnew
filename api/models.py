# myapp/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from rest_framework.authtoken.models import Token


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    supabase_user_id = models.CharField(max_length=255, unique=True)
    avatar_url = models.URLField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    is_email_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile'


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    supabase_session_id = models.CharField(max_length=500, unique=True)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_activity']
        db_table = 'user_session'
    

class Video(models.Model):
    user_id = models.IntegerField(default=0)
    filename = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    videosize = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    price = models.FloatField(default=0)
    s3_key = models.CharField(max_length=500)
    thumbnail = models.CharField(max_length=200, blank=True, null=True)  # 👈 added
    created_at = models.DateTimeField(auto_now_add=True)
    media_type =  models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, default='I') # Publish-P or Private-I Deleted-D 
    
    class Meta:
        db_table = 'video'

 
# myapp/models.py
class DeleteQueue(models.Model):
    media_id = models.ForeignKey(Video, on_delete=models.CASCADE) # video table id
    s3_key = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    media_type =  models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, default='PENDING')  # PENDING / SUCCESS / FAILED

    class Meta:
        db_table = 'delete_queue'



class VideoView(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="views")
    viewer_id = models.UUIDField(default=uuid.uuid4)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    device_type = models.CharField(max_length=100, blank=True, null=True)
    os_info = models.CharField(max_length=100, blank=True, null=True)
    browser = models.CharField(max_length=100, blank=True, null=True)
    screen_resolution = models.CharField(max_length=50, blank=True, null=True)
    referrer = models.URLField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_watched_at = models.DateTimeField(auto_now=True)
    duration_watched = models.FloatField(default=0.0)
    counted = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["video_id", "viewer_id"]),
        ]
        db_table = 'video_views' 
