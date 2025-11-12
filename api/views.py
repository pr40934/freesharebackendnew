import base64
import boto3
import logging
import json
from .models import Video, DeleteQueue, UserProfile, UserSession, VideoView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView  # pyright: ignore[reportMissingImports]
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta

# from celery import shared_task
from decouple import config
# from keys import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION, BUCKET_NAME 
from .task import process_video_delete_queue

from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.middleware.csrf import get_token
from django.contrib.auth.models import User
from .serializers import UserProfileSerializer, UserSessionSerializer
from .utils import verify_supabase_token, get_client_ip
from django.forms.models import model_to_dict

from django.utils import timezone
import user_agents 

logger = logging.getLogger(__name__)


DECRYPTION_KEY = 987654321  # Example key for XOR decryption

# ============================================
# HELPERS
# ============================================

def get_s3():
    return boto3.client(
        "s3",
        aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
        region_name=config("AWS_REGION"),
    )


# ============================================
# VIDEO UPLOAD VIEWS (ORIGINAL - UNCHANGED)
# ============================================

@method_decorator(csrf_exempt, name='dispatch')
class GetPresignedUrlsView(APIView):
    """Generate multipart presigned URLs for video upload"""
    def post(self, request):
        try:
            videoId = request.data.get("video_Id")
            filename = request.data.get("filename")
            filetype = request.data.get("filetype")
            filesize = int(request.data.get("filesize"))
            user_id = request.user.id
            # user_id = 234
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
                Bucket=config("BUCKET_NAME"),
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
                            "Bucket": config("BUCKET_NAME"),
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
                media_type='VIDEO'
            )
            video.s3_key = s3_key
            video.save()

            return Response({"uploadId": upload_id, "parts": urls, "videoId": video.id})
        
        except Exception as e:
            print("Error in GetPresignedUrlsView:", e)
            return Response({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CompleteMultipartUploadView(APIView):
    """Complete multipart upload"""
    def post(self, request):
        try:
            upload_id = request.data.get("uploadId")
            parts = request.data.get("parts")
            video_id = request.data.get("uploadedVideoId")

            video = Video.objects.get(id=video_id)
            s3 = get_s3()

            s3.complete_multipart_upload(
                Bucket=config("BUCKET_NAME"),
                Key=video.s3_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts}
            )
            video.status = 'PRIVATE'
            video.save()
            
            return Response({"status": "success", "videoId": video_id})
        except Exception as e:
            print("Error in complete the video upload:", e)
            return Response({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PresignedThumbNailUploadView(APIView):
    """Generate presigned URL for thumbnail upload"""
    def _go(self, file_name, file_type, video_id):
        if not video_id:
            return Response({"error": "video_id required"}, status=400)
        if not file_name or not file_type:
            return Response({"error": "file_name & file_type required"}, status=400)

        video = Video.objects.get(id=video_id)
        s3 = get_s3()

        key = f"uploadedThumbnails/{video.user_id}/{file_name}"

        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": config("BUCKET_NAME"), "Key": key, "ContentType": file_type},
            ExpiresIn=3600,
        )
        video.thumbnail = key
        video.save()
        return Response({"url": url, "thumbnail_id": video_id})

    def get(self, request):
        return self._go(request.GET.get("file_name"), request.GET.get("file_type"), request.GET.get("video_id"))
    
    def post(self, request):
        return self._go(request.data.get("file_name"), request.data.get("file_type"), request.data.get("video_id"))


class TriggerDeleteQueueView(APIView):
    """Trigger video deletion queue processing"""
    def post(self, request):
        process_video_delete_queue(batch_size=50)
        return Response({"status": "Deletion task triggered"})


class VideoDataSaveView(APIView):
    """Save video metadata"""
    def post(self, request, *args, **kwargs):
        payload = request.data  
        video_id = request.data.get("video_id")
        video_file_name = request.data.get("orginial_file_titile")
        video_title = request.data.get("video_title")
        video_desc = request.data.get("description") 

        print('='*50)
        print("Received video metadata:", payload)
        print('='*50)
        print("Received video_id:", video_id) 
        print('='*50)

        if video_id:
            vid_obj = Video.objects.filter(id=video_id).last()
            vid_obj.filename = video_file_name  
            vid_obj.title = video_title 
            vid_obj.description = video_desc 
            vid_obj.save()  
        else:
            return Response(
                {"message": "Video Id missed while saving the video data !", "data": payload},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"message": "Video data saved successfully!", "data": payload},
            status=status.HTTP_201_CREATED
        )


# @method_decorator(csrf_exempt, name='dispatch')
# class GetUserVideosView(APIView):
#     """Get all videos for a user"""
    
#     def get(self, request, user_id):
#         try:
#             if not user_id:
#                 return Response(
#                     {"error": "user_id is required"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             videos = Video.objects.filter(
#                 user_id=user_id,
#             ).order_by('-created_at').values()
            
#             videos_list = list(videos)
            
#             logger.info(f"✅ Fetched {len(videos_list)} videos for user {user_id}")
            
#             return Response(
#                 {
#                     "status": "success",
#                     "total": len(videos_list),
#                     "videos": videos_list
#                 },
#                 status=status.HTTP_200_OK
#             )
        
#         except Exception as e:
#             logger.error(f"❌ Error fetching videos: {str(e)}")
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


@method_decorator(csrf_exempt, name='dispatch')
class GetUserVideosView(APIView):
    """Get all videos for authenticated user"""

    def get(self, request):
        try:
            user = request.user
            if not user or not user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            print('='*50)
            print('user_id :: ',user.id)
            print('='*50)

            videos = Video.objects.filter(
                user_id=user.id
            ).order_by('-created_at').values()

            videos_list = list(videos)

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



@method_decorator(csrf_exempt, name='dispatch')
class GetVideoDetailsView(APIView):

    authentication_classes = []  # Disable authentication
    permission_classes = [] # Allow any user (including unauthenticated)

    def get(self, request):
        try:
            # user = request.user
            # if not user or not user.is_authenticated:
            #     return Response(
            #         {"error": "Authentication required"},
            #         status=status.HTTP_401_UNAUTHORIZED
            #     )
            
            decrypted_id = request.GET.get('key')
            
            print('='*50)
            print('decrypted_id :: ',decrypted_id)
            print('='*50)

            # def encrypt(num: int, key: int) -> str:
            #     val = num ^ key
            #     return base64.urlsafe_b64encode(str(val).encode()).decode()

            # def decrypt(enc: str, key: int) -> int:
            #     val = int(base64.urlsafe_b64decode(enc.encode()).decode())
            #     return val ^ key

            # # example
            # e = encrypt(12345, DECRYPTION_KEY)
            # print(e)
            # print(decrypt(e, DECRYPTION_KEY))

            # data = {}

            # video = Video.objects.filter(id=decrypted_id).last()

            # videos_data = [model_to_dict(v) for v in video]

            # if videos_data:
            #     if videos_data.status == 'PUBLIC':
            #         data = {
            #             "video_url"   : videos_data.s3_key,
            #             "video_title" : videos_data.title,
            #             "video_desc"  : videos_data.description,
            #             "video_filename" : videos_data.filename,
            #         }
            #     else:
            #         return Response(
            #                 {"error": "Video is not public", 'message': 'video in pravate by uploader'},
            #                 status=status.HTTP_403_FORBIDDEN
            #             )
            # else:
            #     return Response(
            #         {"error": "Video was deleted by uploader or not found"},
            #         status=status.HTTP_404_NOT_FOUND
            #     )


            data = {}

            video = Video.objects.filter(id=decrypted_id).last()

            if video:
                if video.status == 'PUBLIC':
                    data = {
                        "video_url": video.s3_key,
                        "video_title": video.title,
                        "video_desc": video.description, 
                        "video_filename": video.filename,
                        "video_thumbnail": video.thumbnail, 
                    }
                else:
                    return Response(
                        {"error": "Video is not public", "message": "Video is private by uploader"},
                        status=status.HTTP_403_FORBIDDEN,
                    ) 
            else:
                return Response(
                    {"error": "Video was deleted by uploader or not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "status": "success",
                    "data": data,
                    # "total": len(videos_list),
                    # "videos": videos_list
                }, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"❌ Error fetching videos: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================
# AUTH VIEWS (NEW - ADDED)
# ============================================

class OAuthCallbackView(APIView):
    """
    Handle Supabase OAuth callback
    POST /api/auth/callback/
    Body: {
        "access_token": "supabase_jwt",
        "refresh_token": "optional_refresh_token"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = json.loads(request.body)
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')

            if not access_token:
                return Response(
                    {'error': 'Missing access token'},
                    status=HTTP_400_BAD_REQUEST
                )

            # Verify Supabase token
            decoded = verify_supabase_token(access_token)
            if not decoded:
                return Response(
                    {'error': 'Invalid token'},
                    status=HTTP_401_UNAUTHORIZED
                )

            # Extract user data from JWT
            supabase_id = decoded.get('sub')
            email = decoded.get('email')
            full_name = decoded.get('name', '')
            avatar_url = decoded.get('picture', '')
            email_verified = decoded.get('email_verified', False)

            # Get or create Django user
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': full_name.split()[0] if full_name else '',
                    'last_name': ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                }
            )

            if not created:
                user.first_name = full_name.split()[0] if full_name else user.first_name
                user.last_name = ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else user.last_name
                user.save()

            # Get or create user profile
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={'supabase_user_id': supabase_id}
            )

            # Update profile
            profile.avatar_url = avatar_url
            profile.full_name = full_name
            profile.is_email_verified = email_verified
            profile.last_login_ip = get_client_ip(request)
            profile.last_login_date = datetime.now()
            profile.save()

            # Create session record
            session_id = f"{supabase_id}_{datetime.now().timestamp()}"
            expires_at = datetime.now() + timedelta(days=7)

            UserSession.objects.create(
                user=user,
                supabase_session_id=session_id,
                access_token=access_token,
                refresh_token=refresh_token or '',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                expires_at=expires_at
            )

            # Create or get Django token
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                },
                'profile': UserProfileSerializer(profile).data,
                'session_id': session_id,
            }, status=HTTP_200_OK)

        except Exception as e:
            print(f"OAuth callback error: {str(e)}")
            return Response(
                {'error': 'Authentication failed', 'detail': str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProfileView(APIView):
    """
    Get/Update user profile
    GET /api/profile/ - Get profile (Protected)
    PUT /api/profile/ - Update profile (Protected)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
            print('='*50)
            print(profile)
            print('='*50)
            print(request.user.profile)
            return Response(UserProfileSerializer(profile).data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=HTTP_400_BAD_REQUEST
            )

    def put(self, request):
        try:
            profile = request.user.profile
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)

            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=HTTP_400_BAD_REQUEST
            )


class SessionsView(APIView):
    """
    Get all active user sessions
    GET /api/sessions/ - List all sessions (Protected)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sessions = UserSession.objects.filter(
                user=request.user,
                is_active=True
            ).order_by('-last_activity')
            
            return Response(UserSessionSerializer(sessions, many=True).data)
        except Exception as e:
            print(f"Sessions fetch error: {str(e)}")
            return Response(
                {'error': 'Failed to fetch sessions'},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """
    Logout from current device
    POST /api/logout/
    Body: {
        "session_id": "session_id_to_logout"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            session_id = request.data.get('session_id')

            if session_id:
                UserSession.objects.filter(
                    user=request.user,
                    supabase_session_id=session_id
                ).update(is_active=False)

            try:
                request.user.auth_token.delete()
            except:
                pass

            return Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=HTTP_200_OK)

        except Exception as e:
            print(f"Logout error: {str(e)}")
            return Response(
                {'error': 'Logout failed', 'detail': str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutAllView(APIView):
    """
    Logout from all devices
    POST /api/logout-all/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            UserSession.objects.filter(user=request.user).update(is_active=False)

            try:
                request.user.auth_token.delete()
            except:
                pass

            return Response({
                'success': True,
                'message': 'Logged out from all devices'
            }, status=HTTP_200_OK)

        except Exception as e:
            print(f"Logout all error: {str(e)}")
            return Response(
                {'error': 'Logout failed', 'detail': str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )




# ============================================
# view tracking 
# ============================================


class VideoViewCreateAPIView(APIView):

    authentication_classes = []  # Disable authentication
    permission_classes = [] # Allow any user (including unauthenticated)

    def post(self, request):
        data = request.data
        video_id = data.get("video_id")
        duration = data.get("duration", 0)
        viewer_id = data.get("viewer_id")

        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)

        ip = self.get_client_ip(request)
        ua_string = request.META.get("HTTP_USER_AGENT", "")
        user_agent = user_agents.parse(ua_string)

        view = VideoView.objects.create(
            video=video,
            viewer_id=viewer_id,
            ip_address=ip,
            user_agent=ua_string,
            device_type="Mobile" if user_agent.is_mobile else "Desktop",
            os_info=user_agent.os.family,
            browser=user_agent.browser.family,
            screen_resolution=data.get("screen_resolution"),
            referrer=request.META.get("HTTP_REFERER"),
            duration_watched=duration,
            counted=float(duration) >= 30,  # count if watched ≥30s
        )

        return Response({"status": "ok", "counted": view.counted}, status=status.HTTP_201_CREATED)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
