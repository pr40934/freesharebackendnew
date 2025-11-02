# myapp/models.py
from django.db import models

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

  