import logging
# from celery import shared_task
from .models import DeleteQueue, Video
# from keys import BUCKET_NAME
from decouple import config
logger = logging.getLogger(__name__)

# @shared_task
# def process_video_delete_queue(batch_size=50):
#     from .views import get_s3
#     s3 = get_s3()
#     pending = DeleteQueue.objects.filter(status='PENDING')[:batch_size]

#     for item in pending:
#         try:
#             s3.delete_object(Bucket=BUCKET_NAME, Key=item.s3_key)
#             item.status = 'SUCCESS'
#             item.save()
#         except Exception as e:
#             item.status = 'FAILED'
#             item.save()
#             logger.exception(f"Failed to delete S3 object {item.s3_key}")



from django.utils import timezone

# Check if traffic is low (based on your request timestamp or system load)
def is_low_traffic():
    last_request_time = timezone.now()  # This would normally be dynamically tracked in your system.
    return (timezone.now() - last_request_time).total_seconds() > 60  # Adjust this threshold as needed

# def process_video_delete_queue(batch_size=50):
#     from .views import get_s3
#     # If traffic is low, start deletion process
#     # if is_low_traffic():
#     if True:
#         s3 = get_s3()
#         pending = DeleteQueue.objects.filter(status='PENDING')[:batch_size]
        
#         for item in pending:
#             try:
#                 # Call AWS API to delete the file
#                 resp = s3.delete_object(Bucket=BUCKET_NAME, Key=item.s3_key)
#                 if item.media_type == 'VIDEO':
#                     # If this is a video, delete the associated thumbnail
#                     vide_obj = Video.objects.filter(id = item.media_id).last() # Check if a thumbnail exists
#                     if vide_obj and vide_obj.thumbnail:
#                         s3.delete_object(Bucket=BUCKET_NAME, Key=vide_obj.thumbnail)
#                         print(f"Deleted thumbnail: {vide_obj.thumbnail}")

#                 item.status = 'SUCCESS'
#                 item.save()
#             except Exception as e:
#                 # Mark as failed in case of an error
#                 item.status = 'FAILED'
#                 item.save()
#                 logger.exception(f"Failed to delete S3 object {item.s3_key}: {e}")

#         print(f"Processed {len(pending)} delete tasks.")
#     else:
#         print("Traffic is high. Skipping video delete.")




# def process_video_delete_queue(batch_size=50):
#     from .views import get_s3
#     # If traffic is low, start deletion process
#     # if is_low_traffic():
#     if True:
#         s3 = get_s3()
#         pending = DeleteQueue.objects.filter(status='PENDING')[:batch_size]
        
#         for item in pending:
#             try:
#                 # Call AWS API to delete the file (video or other media)
#                 resp = s3.delete_object(Bucket=BUCKET_NAME, Key=item.s3_key)
                
#                 # If media type is 'VIDEO', delete the associated thumbnail
#                 if item.media_type == 'VIDEO':
#                     try:
#                         # Fetch the related video object
#                         video_obj = Video.objects.get(id=item)  # Using .get() here for efficiency

#                         # Check if the video has a thumbnail, then delete it from S3
#                         if video_obj.thumbnail:
#                             s3.delete_object(Bucket=BUCKET_NAME, Key=video_obj.thumbnail)
#                             print(f"Deleted thumbnail: {video_obj.thumbnail}")
#                     except Video.DoesNotExist:
#                         print(f"Video not found for media_id {item.media_id}")
                
#                 # Update status to 'SUCCESS' after successful deletion
#                 item.status = 'SUCCESS'
#                 item.save()

#             except Exception as e:
#                 # In case of an error, mark the status as 'FAILED'
#                 item.status = 'FAILED'
#                 item.save()
#                 logger.exception(f"Failed to delete S3 object {item.s3_key}: {e}")

#         print(f"Processed {len(pending)} delete tasks.")
#     else:
#         print("Traffic is high. Skipping video delete.")



def process_video_delete_queue(batch_size=50):
    from .views import get_s3
    # If traffic is low, start deletion process
    # if is_low_traffic():
    if True:
        s3 = get_s3()
        pending = DeleteQueue.objects.filter(status='PENDING')[:batch_size]
        
        for item in pending:
            try:
                # Call AWS API to delete the file (video or other media)
                resp = s3.delete_object(Bucket=config("BUCKET_NAME"), Key=item.s3_key)
                item.status = 'SUCCESS'
                item.save()

            except Exception as e:
                # In case of an error, mark the status as 'FAILED'
                item.status = 'FAILED'
                item.save()
                logger.exception(f"Failed to delete S3 object {item.s3_key}: {e}")

        print(f"Processed {len(pending)} delete tasks.")
    else:
        print("Traffic is high. Skipping video delete.")
   