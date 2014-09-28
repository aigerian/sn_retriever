from os import fdopen
import random
import string
import time
from birdy.twitter import UserClient, TwitterRateLimitError
from contrib.api.entities import APIUser, APIMessage, APIContentObject, APISocialObject
from contrib.api.ttr import TTR_API
from contrib.api.vk import ContentResult, rel_types_groups, \
    rel_types_users
from contrib.api.vk.vk_execute import VK_API_Execute
from contrib.db.database_engine import Persistent
import properties  # hi Pasha
from walker_vk import persist_content_result

__author__ = '4ikist'

import cProfile
import hotshot


class FakeVK(VK_API_Execute):
    def __init__(self):
        super(FakeVK, self).__init__(logins=[])

    def get_groups_info(self, group_ids):
        return [APISocialObject({'sn_id': random.randint(0, 1000)}) for el in xrange(10)]

    def get_user_info(self, user_id):
        return [APIUser({'sn_id': random.randint(0, 1000000), 'screen_name': rand_str(el * 3)}) for el in xrange(10)]


rand_str = lambda cnt: ''.join([str(random.choice(string.ascii_letters)) for el in xrange(cnt)])


class FakeContentResult(ContentResult):
    def __init__(self):
        super(FakeContentResult, self).__init__()
        self.add_comments(
            [APIMessage({'sn_id': el * random.randint(0, 3917333),
                         'owner': APIUser({'sn_id': random.randint(0, 1000000),
                                           'screen_name': rand_str(el * 3)})}) for el in
             xrange(random.randint(0, 1000))])
        self.add_content(
            [APIContentObject({'sn_id': el * random.randint(0, 3917333),
                               'owner': APIUser({'sn_id': random.randint(0, 1000000),
                                                 'screen_name': rand_str(el * 3)})}) for el in
             xrange(random.randint(0, 100))])
        for el in rel_types_groups:
            self.add_relations((random.randint(0, 1000), el, random.randint(0, 1000)))
        for el in rel_types_users:
            self.add_relations((random.randint(0, 1000), el, random.randint(0, 1000)))


def profile_hotspot(func):
    """Decorator for run function profile"""

    def wrapper(*args, **kwargs):
        profile_filename = func.__name__ + '.prof_ht'
        profiler = hotshot.Profile(profile_filename)
        profiler.start()
        result = func(*args, **kwargs)
        profiler.stop()
        profiler.close()
        return result

    return wrapper


def profile_cprofile(func):
    """Decorator for run function profile"""

    def wrapper(*args, **kwargs):
        profile_filename = func.__name__ + '.prof_cp'
        profiler = cProfile.Profile()
        result = profiler.runcall(func, *args, **kwargs)
        profiler.dump_stats(profile_filename)
        return result

    return wrapper


def test_vk_execute():
    vk = VK_API_Execute()
    photos = vk.get_photos_data('durov' or 1)  # hi pasha$)
    photo = photos.content[0]
    photo_comments = vk.get_photos_comments_data(1)
    photo_comment = photo_comments.comments[0]

    videos = vk.get_videos_data('266544674' or 266544674)
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


vk = FakeVK()
persist = Persistent(truncate=True)


@profile_cprofile
def test_persist():
    for el in xrange(10):
        print el
        content_result = FakeContentResult()
        persist_content_result(content_result, el, persist)


if __name__ == '__main__':
    vk = VK_API_Execute(logins=[])
    import pickle
    pickle.dump(vk, fdopen(1,'w+'))