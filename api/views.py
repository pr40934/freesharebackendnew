from .models import Video, DeleteQueue
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import boto3
import logging
# from celery import shared_task
from keys import AWS_ACCESS_KEY, AWS_SECRET_KEY , AWS_REGION ,BUCKET_NAME 
from .task import process_video_delete_queue

logger = logging.getLogger(__name__)

# ============ CELERY TASKS ============

# @shared_task
# def delete_old_s3_file_task(bucket_name, old_s3_key):
#     try:
#         s3 = boto3.client(
#             "s3",
#             aws_access_key_id=AWS_ACCESS_KEY,
#             aws_secret_access_key=AWS_SECRET_KEY,
#             region_name=AWS_REGION,
#         )
        
#         print('='*50)
#         print('old_s3_key :: ', old_s3_key)
#         print('='*50)

#         s3.delete_object(Bucket=bucket_name, Key=old_s3_key)
#         return {"status":"success","key":old_s3_key}
#     except Exception as e:
#         return {"status":"failed","error":str(e)}

# ============ HELPERS ============

def get_s3():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )

# ============ Genrate multipart presgined url's or video upload ============

@method_decorator(csrf_exempt, name='dispatch')
class GetPresignedUrlsView(APIView):
    def post(self, request):
        try:
            videoId = request.data.get("video_Id")
            filename = request.data.get("filename")
            filetype = request.data.get("filetype")
            filesize = int(request.data.get("filesize"))
            user_id = 234
            if not user_id:
                return Response({"error": "user_id required"}, status=400)

            s3 = get_s3()
            s3_key = f"uploadedVideos/{user_id}/{filename}"

            old = Video.objects.filter(id=videoId).last()
            if old and old.s3_key:
                # Create delete queue for the video file if it exists
                DeleteQueue.objects.create(media_id=old, s3_key=old.s3_key, media_type=old.media_type)
                
                # Only create delete queue for thumbnail if it exists
                if old.thumbnail:
                    DeleteQueue.objects.create(media_id=old, s3_key=old.thumbnail, media_type='THUMBNAIL')


            upload = s3.create_multipart_upload(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                ContentType=filetype
            )
            upload_id = upload["UploadId"]

            chunk = 5 * 1024 * 1024
            total_parts = (filesize + chunk - 1) // chunk

            urls = [
                {
                    "partNumber": i,
                    "url": s3.generate_presigned_url(
                        "upload_part",
                        Params={
                            "Bucket": BUCKET_NAME,
                            "Key": s3_key,
                            "UploadId": upload_id,
                            "PartNumber": i
                        },
                        ExpiresIn=3600,
                        HttpMethod="PUT"
                    )
                }
                for i in range(1, total_parts + 1)
            ]

            video = Video.objects.get(id=videoId) if videoId else Video.objects.create(
                user_id=user_id,
                filename=filename,
                title=filename,
                videosize=str(filesize),
                s3_key=s3_key,
                media_type = 'VIDEO'
            )
            video.s3_key = s3_key
            video.save()

            return Response({"uploadId": upload_id, "parts": urls, "videoId": video.id}) # type: ignore
        
        except Exception as e:
            print("Error in GetPresignedUrlsView:", e)
            return Response({"error": str(e)}, status=500)


# ============ COMPLETE MULTIPART ============

@method_decorator(csrf_exempt, name='dispatch')
class CompleteMultipartUploadView(APIView):
    def post(self, request): # type: ignore
        try:
            upload_id = request.data.get("uploadId")
            parts = request.data.get("parts")
            video_id = request.data.get("uploadedVideoId")

            video = Video.objects.get(id=video_id)
            s3 = get_s3()

            s3.complete_multipart_upload(
                Bucket=BUCKET_NAME,
                Key=video.s3_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts}
            )
            video.status = 'PRIVATE'
            video.save()
            
            return Response({"status":"success","videoId":video_id})
        except Exception as e:
            print("Error in complete the video upload:", e)
            return Response({"error": str(e)}, status=500)

# ============ Thumbnail url genrate ============


@method_decorator(csrf_exempt, name='dispatch')
class PresignedThumbNailUploadView(APIView):
    def _go(self, file_name, file_type, video_id):
        if not video_id: return Response({"error":"video_id required"},status=400)
        if not file_name or not file_type: return Response({"error":"file_name & file_type required"},status=400)

        video = Video.objects.get(id=video_id)
        s3 = get_s3()

        key = f"uploadedThumbnails/{video.user_id}/{file_name}"

        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket":BUCKET_NAME,"Key":key,"ContentType":file_type},
            ExpiresIn=3600,
        )
        video.thumbnail = key
        video.save()
        return Response({"url":url,"thumbnail_id":video_id})

    def get(self, request):
        return self._go(request.GET.get("file_name"), request.GET.get("file_type"), request.GET.get("video_id"))
    def post(self, request):
        return self._go(request.data.get("file_name"), request.data.get("file_type"), request.data.get("video_id"))



class TriggerDeleteQueueView(APIView):
    def post(self, request):
        process_video_delete_queue(batch_size=50)  # Run it directly, no Celery
        return Response({"status": "Deletion task triggered"})
    

class VideoDataSaveView(APIView):
    def post(self, request, *args, **kwargs):
        # request.data contains the JSON payload sent from the frontend
        payload = request.data  
        video_id = request.data.get("video_id")
        video_file_name = request.data.get("orginial_file_titile")
        video_title = request.data.get("video_title")
        video_desc = request.data.get("description") 
        # content_categoty = request.data.get("eighteenPlus") 

        # Example: print or process the payload
        print('='*50)
        print("Received video metadata:", payload)
        print('='*50)
        print("Received video_id:", video_id)
        print('='*50)

        if video_id:
            vid_obj = Video.objects.filter(id = video_id).last()
            vid_obj.filename = video_file_name # type: ignore
            vid_obj.title = video_title # type: ignore
            vid_obj.description = video_desc # type: ignore
            vid_obj.save() # type: ignore
        else:
            return Response(
                {"message": "Video Id missed while saving the video data !", "data": payload},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: Save to DB (example below)
        # video = Video.objects.create(**payload)

        return Response(
            {"message": "Video data saved successfully!", "data": payload},
            status=status.HTTP_201_CREATED
        )
    


# ========== BACKEND (views.py) ==========

@method_decorator(csrf_exempt, name='dispatch')
class GetUserVideosView(APIView):
    """Get all videos for a user"""
    
    def get(self, request, user_id):
        try:
            # Validation
            if not user_id:
                return Response(
                    {"error": "user_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Filter videos by user_id
            videos = Video.objects.filter(
                user_id=user_id,
                # status='P'  # Only published videos
            ).order_by('-created_at').values()
            
            # Convert to list
            videos_list = list(videos)
            
            logger.info(f"✅ Fetched {len(videos_list)} videos for user {user_id}")
            
            return Response(
                {
                    "status": "success",
                    "total": len(videos_list),
                    "videos": videos_list
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"❌ Error fetching videos: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
  

# ========== URL (urls.py) ==========
# Add this to your urls.py:
# path('api/user-videos/<int:user_id>/', GetUserVideosView.as_view(), name='get_user_videos'),