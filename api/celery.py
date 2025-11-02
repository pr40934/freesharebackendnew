# from celery.schedules import crontab

# app.conf.beat_schedule = {
#     'process-delete-queue-every-1-min': {
#         'task': 'myapp.tasks.process_video_delete_queue',
#         'schedule': crontab(minute='*/1'),  # runs every 1 minute
#         'args': (50,)  # batch_size
#     },
# } 
