from collections import Counter
from contrib.api.ttr import TTR_API
from contrib.core.tracking import TTR_Tracking
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
        :param message: some dict with sn_id or some unicode
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
        :param social_object: some dict with sn_id and object type: [social_object, user, message]
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

    def urls(self, user):
        """
        return external url in user timeline
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


def get_params_for_api(user):
    params = {}
    if isinstance(user, str):
        params['screen_name'] = user if '@' != user[0] else user[1:]
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
        self.tracker = TTR_Tracking(api, database)

    def __get_user(self, user_params):
        user_params['use_as_cache'] = True
        user = self.database.get_user(**user_params)
        if not user:
            user_params.pop('use_as_cache')
            user = self.api.get_user(**user_params)
            user['_id'] = self.database.save_user(user)
        return user

    def __get_message(self, message_id):
        message = self.database.get_message(message_id, use_as_cache=True)
        if not message:
            message, user = self.api.get_message(message_id)
            user_ref = self.database.get_user_ref({'_id': self.database.save_user(user)})
            message['user'] = user_ref
            self.database.save_message(message)
        return message

    def __get_user_messages(self, user, params=None):
        user_params = get_params_for_api(user)
        db_user = self.__get_user(user_params)
        db_user_ref = self.database.get_user_ref(db_user)
        last_message = self.database.get_message_last(db_user)
        if last_message:
            result_from_api = self.api.get_all_timeline(since_id=last_message.get('sn_id'), user=user_params)
        else:
            result_from_api = self.api.get_all_timeline(user=user_params)
        new_messages = []
        for el in result_from_api:
            el['user'] = db_user_ref
            self.database.save_message(el)
            new_messages.append(el)
        messages = self.database.get_messages(dict({'user': db_user_ref}, **params if params else {}))
        return list(messages)

    def __get_actual_relations(self, user, relations_type='friends'):
        user_params = get_params_for_api(user)
        api_user = self.api.get_user(**user_params)
        real_count = api_user.get('%s_count' % relations_type)
        saved_user = self.database.get_user(**user_params)
        saved_count = saved_user.get('%s_count' % relations_type)
        delta = real_count - saved_count
        new, removed, _ = self.tracker.get_relations_diff(saved_user, delta)
        new_users = self.api.get_users(new)
        for el in new_users:
            self.database.save_user(el)
        friends = self.database.get_relations(from_id=saved_user.get('_id'), relation_type=relations_type)
        return friends

    def timeline_length(self, user):
        user = self.__get_user(get_params_for_api(user))
        return user.get('statuses_count')

    def hashtags(self, user):
        hashtags = []
        messages = self.__get_user_messages(user)
        for el in messages:
            for ht in el.get('entities').get('hashtags'):
                hashtags.append(ht.get('text'))
        return Counter(hashtags)

    def urls(self, user):
        urls = []
        messages = self.__get_user_messages(user)
        for el in messages:
            for url in el.get('entities').get('urls'):
                urls.append(url.get('extended_url'))
        return Counter(urls)

    def mentions(self, user, only_names=False):
        messages = self.__get_user_messages(user)
        mentions = []
        screen_names = set()
        for el in messages:
            for mention in el.get('entities').get('user_mentions'):
                mention_screen_name = mention.get('screen_name')
                if not only_names:
                    if mention_screen_name not in screen_names:
                        user_mention = self.__get_user(get_params_for_api(mention_screen_name))
                        mentions.append(user_mention)
                        screen_names.add(mention_screen_name)
                else:
                    mentions.append(mention_screen_name)
        return Counter(mentions)

    def real_name(self, user):
        user = self.__get_user(get_params_for_api(user))
        return user.get('name')

    def dt_init(self, social_object):
        return social_object.get('created_at')

    def friends_count(self, user):
        user = self.__get_user(get_params_for_api(user))
        return user.get('friends_count')

    def followers_count(self, user):
        user = self.__get_user(get_params_for_api(user))
        return user.get('followers_count')

    def reposts_count(self, message):
        if isinstance(message, dict):
            sn_id = message.get('sn_id')
            found_message = self.__get_message(sn_id)
        elif isinstance(message, str):
            messages = self.database.get_messages_by_text({'text': message}, limit=1)
            if len(messages):
                found_message = messages[0]
            else:
                found_message = None
        elif isinstance(message, (int, long)):
            found_message = self.__get_message(message)
        else:
            found_message = None

        if found_message:
            return found_message.get('retweet_count')

    def friends(self, user):
        result = self.__get_actual_relations(user, 'friends')
        return result

    def followers(self, user):
        result = self.__get_actual_relations(user, 'followers')
        return result

    def count_urls(self, who, url):
        messages = self.__get_user_messages(who)
        count = 0
        for message in messages:
            urls = message.get('entites').get('urls')
            for saved_url in urls:
                if url in (saved_url.get('url'), saved_url.get('expanded_url'), saved_url.get('display_url')):
                    count += 1
        return count

    def count_hashtags(self, who, hashtag):
        if hashtag[0] == '#':
            search_ht = hashtag[1:]
        else:
            search_ht = hashtag[:]
        ht = self.hashtags(who)
        return ht.get(search_ht, 0)

    def count_mentions(self, who, mentioned):
        mentions = self.mentions(who, True)
        return mentions.get(mentioned, 0)

    def count_reposts(self, who, whose):
        user = self.__get_user(who)
        user_producer = self.__get_user(whose)
        intersted_messages = self.__get_user_messages(user=user,
                                                      params={
                                                          'in_reply_to_screen_name': user_producer.get('screen_name'),
                                                          'in_reply_to_user_id': user_producer.get('sn_id')})
        return len(intersted_messages)


if __name__ == '__main__':
    api = TTR_API()
    db = db_handler()
    ch = TTR_Characterisitcs(api, db)
    tl_length = ch.timeline_length('@linoleum2k12')
    assert tl_length == 80
    ht = ch.hashtags('@linoleum2k12')
    real_name = ch.real_name('@linoleum2k12')
    friends_count = ch.friends_count('@linoleum2k12')
    assert friends_count == 7
    followers_count = ch.followers_count('@linoleum2k12')
    assert followers_count == 11
    urls = ch.urls('@linoleum2k12')
    dt_init = ch.dt_init('@linoleum2k12')
    mentions_users = ch.mentions('@linoleum2k12', only_names=False)
    mentions_names = ch.mentions('@linoleum2k12', only_names=True)

    api_tl = api.get_all_timeline({'screen_name': '@linoleum2k12'})
    some_message = api_tl.next()
    rt_count = ch.reposts_count(some_message.get('sn_id'))

    ht_count = ch.count_hashtags('@linoleum2k12', '#test')
    assert ht_count == 1

    url_count = ch.count_urls('@linoleum2k12', 'railstutorial.org')
    assert url_count == 1

    ment_count = ch.count_mentions('@linoleum2k12', '@lutakisel4ikova')
    assert ment_count == 2

    friends = ch.friends('@linoleum2k12')
    for el in friends:
        print el

    followers = ch.followers('@linoleum2k12')
    for el in followers:
        print el
