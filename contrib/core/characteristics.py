from contrib.api.ttr import TTR_API
from contrib.db.mongo_db_connector import db_handler

__author__ = '4ikist'


class BaseCharacteristics(object):

    def followers_count(self, user):
        """
        return count followers of input user
        :param user: some dict with sn_id, screen_name
        :return: count
        """
        raise NotImplementedError

    def friends_count(self, user):
        """
        return count friends of user
        :param user: some dict with sn_id, screen_name
        :return: count
        """
        raise NotImplementedError

    def reposts_count(self, message):
        """
        return count reposts of input message
        :param message: some dict with sn_id
        :return: count
        """
        raise NotImplementedError

    def timeline_length(self, user):
        """
        return count of user message
        :param user: some dict with sn_id
        :return: count
        """
        raise NotImplementedError

    def real_name(self, user):
        """
        return real name of user
        :param user: some dict with sn_id
        :return: string of real name
        """
        raise NotImplementedError

    def dt_init(self, social_object):
        """
        return date when social object was created
        social object can be message or user or another social object like page from fb or another...
        :param user: some dict with sn_id
        :return: datetime
        """
        raise NotImplementedError

    def followers(self, user):
        """
        return generator of user followers
        :param user:
        :return:
        """
        raise NotImplementedError

    def friends(self, user):
        """
        return generator of user friends
        :param user:
        :return:
        """
        raise NotImplementedError

    def mentions(self, user, only_names=False):
        """
        return generator of users which input user was mentioned
        :param user:
        :param only_names: if true - returning generator with only names
        :return:
        """
        raise NotImplementedError

    def hashtags(self, user):
        """
        return generator of user messages hashtags
        :param user:
        :return:
        """
        raise NotImplementedError

    def urls(self,user):
        """
        return external url in user timeline
        :param user:
        :return:
        """
        raise NotImplementedError

    def mentioned_urls(self, user):
        """
        returns generator of user mentioned urls
        :param user:
        :return:
        """
        raise NotImplementedError

    def count_mentions(self, who, mentioned):
        """
        returns count mentions of mentioned user by who user
        :param mentioned: user who mentioned by who
        :param who: user who mention
        :return:
        """
        raise NotImplementedError

    def count_hashtags(self, who, hashtag):
        """
        returns count
        :param who:
        :param hashtag:
        :return:
        """
        raise NotImplementedError

    def count_urls(self, who, url):
        """
        returns count user (who) is mentioned input url
        :param who:
        :param url:
        :return:
        """
        raise NotImplementedError

    def count_reposts(self, who, whose):
        """
        return count of user (who) reposts messages of another user (whose)
        :param who:
        :param whose:
        :return:
        """
        raise NotImplementedError

def get_user_params(user):
    params = {}
    if isinstance(user,str):
        params['screen_name'] = user
        return params
    if 'sn_id' in user:
        params['user_id'] = user.get('sn_id')
    if 'screen_name' in user:
        params['screen_name'] = user.get('screen_name')
    return params

class TTR_Characterisitcs(BaseCharacteristics):
    def __init__(self, api, database):
        self.database = database
        self.api = api

    def timeline_length(self, user):
        user = self.api.get_user(**get_user_params(user))
        self.database.save_user(user)
        return user.get('statuses_count')

    def hashtags(self, user):
        return super(TTR_Characterisitcs, self).hashtags(user)

    def real_name(self, user):
        return super(TTR_Characterisitcs, self).real_name(user)

    def mentioned_urls(self, user):
        return super(TTR_Characterisitcs, self).mentioned_urls(user)

    def friends_count(self, user):
        return super(TTR_Characterisitcs, self).friends_count(user)

    def urls(self, user):
        return super(TTR_Characterisitcs, self).urls(user)

    def dt_init(self, social_object):
        return super(TTR_Characterisitcs, self).dt_init(social_object)

    def followers_count(self, user):
        return super(TTR_Characterisitcs, self).followers_count(user)

    def mentions(self, user, only_names=False):
        return super(TTR_Characterisitcs, self).mentions(user, only_names)

    def reposts_count(self, message):
        return super(TTR_Characterisitcs, self).reposts_count(message)

    def friends(self, user):
        return super(TTR_Characterisitcs, self).friends(user)

    def followers(self, user):
        return super(TTR_Characterisitcs, self).followers(user)

    def count_urls(self, who, url):
        return super(TTR_Characterisitcs, self).count_urls(who, url)

    def count_hashtags(self, who, hashtag):
        return super(TTR_Characterisitcs, self).count_hashtags(who, hashtag)

    def count_mentions(self, who, mentioned):
        return super(TTR_Characterisitcs, self).count_mentions(who, mentioned)

    def count_reposts(self, who, whose):
        return super(TTR_Characterisitcs, self).count_reposts(who, whose)


if __name__ == '__main__':
    ch = TTR_Characterisitcs(TTR_API(), db_handler())
    ct = ch.timeline_length('linoleum2k12')