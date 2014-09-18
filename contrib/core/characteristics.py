from collections import Counter
from contrib.api.entities import APIUser
from contrib.api.ttr import TTR_API
from contrib.core.tracking import TTR_Tracking
from contrib.db.database_engine import Persistent

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
        return Counter of users which input user was mentioned
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


def remove_dog(name):
    return name if '@' != name[0] else name[1:]


def get_params_for_api(user):
    params = {}
    if isinstance(user, str):
        params['screen_name'] = remove_dog(user)
        return params
    if isinstance(user, APIUser):
        return user
    if 'sn_id' in user:
        params['user_id'] = user.get('sn_id')
    if 'screen_name' in user:
        params['screen_name'] = user.get('screen_name')

    return params


def get_params_for_db(user):
    params = {}
    if isinstance(user, str):
        params['screen_name'] = user
    elif isinstance(user, int):
        params['sn_id'] = user
    elif isinstance(user, APIUser):
        return {'sn_id': user.get('sn_id')}
    else:
        params['_id'] = str(user)
    return params


class TTR_Characterisitcs(BaseCharacteristics):
    def __init__(self, database, api):
        self.database = database
        self.api = api
        if self.api:
            self.tracker = TTR_Tracking(api, database)

    def __get_user(self, user_params):
        if isinstance(user_params, APIUser):
            #check that user in db
            if not user_params.get('_id'):
                saved_user = self.database.get_user_info(sn_id=user_params.get('sn_id'))
                if not saved_user:
                    self.database.save_user(user_params)
                return saved_user
            else:
                return user_params

        user_params['use_as_cache'] = True
        user = self.database.get_user_info(**user_params)
        if not user:
            if self.api:
                user_params.pop('use_as_cache')
                user = self.api.get_user_info(**user_params)
                self.database.save_user(user)
        return user

    def __get_message(self, message_id):
        message = self.database.get_message(message_id, use_as_cache=True)
        if not message:
            if self.api:
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
        if self.api:
            result_from_api = self.api.get_all_timeline(since_id=last_message.get('sn_id') if last_message else None,
                                                        user=user_params)
            for el in result_from_api:
                el['user'] = db_user_ref
                self.database.save_message(el)
        messages = self.database.get_messages(dict({'user': db_user_ref}, **params if params else {}))
        return list(messages)

    def __get_actual_relations(self, user, relations_type='friends'):
        user_params = get_params_for_db(user)
        saved_user = self.database.get_user_info(**user_params)
        if self.api:
            user_api_params = get_params_for_api(user)
            api_user = self.api.get_user_info(**user_api_params)
            real_count = api_user.get('%s_count' % relations_type)
            saved_count = self.database.get_relations_count(api_user.get('sn_id'), relations_type)
            delta = real_count - saved_count
            new, removed, _ = self.tracker.get_relations_diff(saved_user, delta, relations_type=relations_type)
            new_users, _ = self.api.get_users_info(new)
            for el in new_users:
                self.database.save_user(el)
        related_users = self.database.get_related_users(from_id=saved_user.get('sn_id'), relation_type=relations_type)
        return related_users

    def timeline_length(self, user):
        user = self.__get_user(get_params_for_api(user))
        return user.get('statuses_count')

    def hashtags(self, user):
        hashtags = []
        messages = self.__get_user_messages(user,
                                            params={'entities.hashtags': {'$not': {'$size': 0}}}
        )
        for el in messages:
            for ht in el.get('entities').get('hashtags'):
                hashtags.append(ht.get('text'))
        return Counter(hashtags)

    def urls(self, user):
        urls = []
        messages = self.__get_user_messages(user,
                                            params={'entities.urls': {'$not': {'$size': 0}}}
        )
        for el in messages:
            for url in el.get('entities').get('urls'):
                urls.append(url.get('expanded_url'))
        return Counter(urls)

    def __get_users(self, user_names_list):
        result = []
        not_in_db_users = []
        for user_name in user_names_list:
            user = self.database.get_user_info(screen_name=user_name)
            if not user:
                not_in_db_users.append(user_name)
            else:
                result.append(user)
        if self.api and len(not_in_db_users):
            retrieved,_ = self.api.get_users_info(screen_names=not_in_db_users)
            for user in retrieved:
                self.database.save_user(user)
                result.append(user)
        return result

    def mentions(self, user, only_names=False):
        messages = self.__get_user_messages(user,
                                            params={'entities.user_mentions': {'$not': {'$size': 0}}}
        )
        mentions = []
        for el in messages:
            for mention in el.get('entities').get('user_mentions'):
                mention_screen_name = mention.get('screen_name').lower()
                mentions.append(mention_screen_name)
        result = Counter(mentions)
        if not only_names:
            loaded_users = self.__get_users(result.keys())
            return Counter({el: result.get(el.screen_name.lower()) for el in loaded_users})
        return result

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
        messages = self.__get_user_messages(who, params={'entities.urls': {'$not': {'$size': 0}}}
        )
        count = 0
        for message in messages:
            urls = message.get('entities').get('urls')
            for saved_url in urls:
                if url in (saved_url.get('url'), saved_url.get('expanded_url'), saved_url.get('display_url')):
                    count += 1
        return count

    def count_hashtags(self, who, hashtag):
        search_ht = hashtag if '#' != hashtag[0] else hashtag[1:]
        ht = self.hashtags(who)
        return ht.get(search_ht, 0)

    def count_mentions(self, who, mentioned):
        mentions = self.mentions(who, True)
        if isinstance(mentioned, str):
            mentioned_name = remove_dog(mentioned)
        elif isinstance(mentioned, dict):
            mentioned_name = mentioned.get('screen_name')
        else:
            return 0
        return mentions.get(mentioned_name, 0)

    def count_reposts(self, who, whose):
        user = self.__get_user(get_params_for_api(who))
        user_producer = self.__get_user(get_params_for_api(whose))
        if user and user_producer:
            intersted_messages = self.__get_user_messages(user=user,
                                                          params={
                                                              'retweeted_status': {'$exists': True},
                                                              'retweeted_status.user.sn_id': user_producer.sn_id})
            return len(intersted_messages)
        else:
            return 0

    def get_nearest_users(self, user, depth=3, rel_type='friends'):
        """
        return user's nearest user in range of depth param by relations with type == rel_type
        if from_rels - all users like [user - [rel_type] - > subject]
        if to_rels - all users like [subject - [rel_type] -> user]
        return {subject:depth}
        """

        def get_nearest(interested_user):
            nearest = set()
            nearest.update(self.__get_actual_relations(interested_user, rel_type))
            return nearest

        def update_result_map(result_map, new_nearest, depth):
            for el in new_nearest:
                if el == user:
                    continue
                if not result_map.has_key(el):
                    result_map[el] = depth

        result_map = {}
        current_incidents = set()
        for i in range(1, depth + 1):
            if not len(current_incidents):
                nearest = get_nearest(user)
                current_incidents.update(nearest)
                update_result_map(result_map, nearest, i)
            else:
                new_current_incidents = set()
                for el in current_incidents:
                    nearest = get_nearest(el)
                    new_current_incidents.update(nearest)
                    update_result_map(result_map, nearest, i)
                current_incidents = new_current_incidents
        return result_map


if __name__ == '__main__':
    api = TTR_API()
    db = Persistent()
    ch = TTR_Characterisitcs(db, api)
    user = api.get_user(screen_name='@linoleum2k12')
    if not user:
        user = db.get_user(screen_name='@linoleum2k12')
    tl_length = ch.timeline_length(user)
    assert tl_length == 80
    ht = ch.hashtags(user)
    real_name = ch.real_name(user)
    friends_count = ch.friends_count(user)
    assert friends_count == 7
    followers_count = ch.followers_count(user)
    assert followers_count == 11
    urls = ch.urls(user)
    dt_init = ch.dt_init(user)
    mentions_users = ch.mentions(user, only_names=False)
    mentions_names = ch.mentions(user, only_names=True)

    # api_tl = api.get_all_timeline(user)
    # some_message = api_tl.next()
    some_message = db.messages.find_one({'retweeted_status': {'$exists': True}})
    rt_count = ch.reposts_count(some_message.get('sn_id'))

    ht_count = ch.count_hashtags(user, '#test')
    assert ht_count == 1

    url_count = ch.count_urls(user, 'railstutorial.org')
    assert url_count == 1

    ment_count = ch.count_mentions('@linoleum2k12', '@lutakisel4ikova')
    assert ment_count == 3

    friends = ch.friends('@linoleum2k12')
    for el in friends:
        print el

    followers = ch.followers('@linoleum2k12')
    for el in followers:
        print el

    cr = ch.count_reposts('@linoleum2k12', '@lutakisel4ikova')