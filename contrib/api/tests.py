import time
from birdy.twitter import UserClient, TwitterRateLimitError
from contrib.api.ttr import TTR_API
from contrib.api.vk.vk_execute import VK_API_Execute
from contrib.db.database_engine import Persistent
import properties

__author__ = '4ikist'

def test_vk_execute():
    vk = VK_API_Execute()
    photos = vk.get_photos_data('266544674')
    photo = photos.content[0]
    photo_comments = vk.get_photos_comments_data('266544674')
    photo_comment = photo_comments.comments[0]

    videos = vk.get_videos_data('266544674')
    video = videos.content[0]
    video_comments = vk.get_comments_data('266544674', 'video', video['video_id'])
    video_comment = video_comments.comments[0]

    wall = vk.get_wall_data('266544674')
    wall_post = wall.content[0]
    wall_comments = vk.get_comments_data('266544674', 'wall', wall_post['wall_post_id'])
    wall_comment = wall_comments.comments[0]

    wall_comment_likers = vk.get_likers('266544674', wall_comment['comment_id'], 'comment', )
    photo_comment_likers = vk.get_likers('266544674', photo_comment['comment_id'], 'photo_comment', )
    video_comment_likers = vk.get_likers('266544674', video_comment['comment_id'], 'video_comment', )


def test_ttr():
    api = TTR_API()
    sr = api.search('medvedev')
    for el in sr:
        print el

if __name__ == '__main__':
    test_ttr()
    test_vk_execute()
