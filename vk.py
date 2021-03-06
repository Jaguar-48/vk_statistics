# -*- coding: utf-8 -*-
import vk_api
import re
import shutil
import requests
import os


class VkParser:
    def __init__(self, login, password, ids):
        self.vk_session = vk_api.VkApi(login=login, password=password, app_id=6305442, api_version='5.69')
        try:
            self.vk_session.auth()
        except vk_api.AuthError as error_msg:
            print error_msg
        self.vk = self.vk_session.get_api()
        self.ids = ids

    def __del__(self):
        print ("destructor called")

    def __save_photo(self, data, filename):
        with open(filename, 'wb') as out_file:
            shutil.copyfileobj(data.raw, out_file)

    # This method returns ids with given ages
    def get_checked_by_age(self, age_start, age_end):
        checked = {}
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            resp = pool.method_one_param(
                'users.get',
                key='user_ids',
                values=self.ids,
                default_values={'fields': 'bdate'}
            )
        for id, data in resp.result.items():
            if u'bdate' in data[0]:
                bdate = data[0][u'bdate']
                checked[id] = re.findall(r'[0-9]{4}', bdate)
                if (type(checked[id]) is list) and (len(checked[id]) > 0):
                    checked[id] = 2017 - int(checked[id][0])
        return [k for k, v in checked.items() if (v >= age_start) and (v <= age_end)]

    def get_personal_info(self, custom_ids=None):
        ids = self.ids
        if custom_ids is not None:
            ids = custom_ids

        result = {}
        info = self.vk.users.get(user_ids=str(ids), fields='''sex, bdate, city, country,
                                                           home_town,domain,has_mobile, education,universities, schools,status,
                                                           last_seen, followers_count,common_count,occupation, relation,personal,connections,
                                                            music,books,games, career, counters''')
        for i in range(len(info)):
            result[info[i]['id']] = {}
            result[info[i]['id']]['name'] = info[i][u'first_name']
            result[info[i]['id']]['surname'] = info[i][u'last_name']
            result[info[i]['id']]['sex'] = ''
            result[info[i]['id']]['age'] = 0
            result[info[i]['id']]['friends'] = 0
            result[info[i]['id']]['occupation'] = ''
            result[info[i]['id']]['university'] = ''
            if u'counters' in info[i]:
                result[info[i]['id']]['friends'] = info[i][u'counters'][u'friends']
            if u'bdate' in info[i]:
                bdate = info[i][u'bdate']
                result[info[i]['id']]['age'] = re.findall(r'[0-9]{4}', bdate)
                if (type(result[info[i]['id']]['age']) is list) and len(result[info[i]['id']]['age']) > 0:
                    result[info[i]['id']]['age'] = 2017 - int(result[info[i]['id']]['age'][0])
                else:
                    result[info[i]['id']]['age'] = 0
            if (u'occupation' in info[i]) and (u'name' in info[i][u'occupation']):
                result[info[i]['id']]['occupation'] = info[i][u'occupation'][u'name']
            if (u'universities' in info[i]) and (len(info[i][u'universities'])>0):
                for univer in info[i][u'universities']:
                    if u'name' in univer:
                        result[info[i]['id']]['university'] += univer[u'name']
                        result[info[i]['id']]['university'] += ', '
            if info[i][u'sex'] == 1:
                result[info[i]['id']]['sex'] = 'female'
            elif info[i][u'sex'] == 2:
                result[info[i]['id']]['sex'] = 'male'
            else:
                result[info[i]['id']]['sex'] = ''

        return result

    # if count=True, method returns photos count
    def get_user_photos(self, count=False, custom_ids=None):
        ids = self.ids
        if custom_ids is not None:
            ids = custom_ids
        result = {}
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            resp = pool.method_one_param(
                'photos.getAll',
                key='owner_id',
                values=ids
            )
        for id, photos in resp.result.iteritems():
            counter = 0
            if int(photos[u'count']) > 0:
                if count:
                    counter += int(photos[u'count'])
                    result[id] = counter
                    continue
                if not os.path.exists(str(id)):
                    os.makedirs(str(id))
                for i in xrange(len(photos[u'items'])):
                    resp = ''
                    for key, val in photos[u'items'][i].iteritems():
                        if (key.find(u'photo') > -1):
                            url = val
                            resp = requests.get(url, stream=True)
                    self.__save_photo(resp, str(id) + '/' + str(i) + '.jpg')
        if count:
            return result

    def get_user_comments(self, count=False):
        result = {}
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            resp = pool.method_one_param(
                'photos.getAllComments',
                key='owner_id',
                values=self.ids
            )
        for id, comments in resp.result.iteritems():
            counter = 0
            if int(comments[u'count']) > 0:
                if count:
                    counter += int(comments[u'count'])
                    result[id] = counter
                    continue
                for item in comments[u'items']:
                    if item[u'from_id'] == id:
                        with open(str(id) + '/comments', 'ab') as out_file:
                            out_file.write('\r\n' + item[u'text'].encode('utf-8') + '\r\n')
        if count:
            return result

    def get_user_stat(self):
        friends = {}
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            friends = pool.method_one_param(
                'friends.get',  # Метод
                key='user_id',  # Изменяющийся параметр
                values=self.ids,
                default_values={'fields': 'photo'}
            )
        return friends.result

    def get_group_members(self, group_ids, offset=0):
        members = []
        while True:
            with vk_api.VkRequestsPool(self.vk_session) as pool:
                resp = pool.method_one_param(
                    'groups.getMembers',
                    key='group_id',  # Изменяющийся параметр
                    values=group_ids,
                    default_values={'offset': offset}
                )
            group_ids = []
            offset += 1000
            for id, arr in resp.result.iteritems():
                if arr[u'count'] > 0:
                    items = arr[u'items']
                    members = list(set(members + items))
                    if (arr[u'count'] - offset > 0):
                        group_ids.append(id)
            if len(group_ids) == 0:
                break;
        return members

    def get_user_subscriptions(self, custom_ids=None):
        subscriptions = {}
        ids = self.ids
        if custom_ids is not None:
            ids = custom_ids
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            resp = pool.method_one_param(
                'users.getSubscriptions',
                key='user_id',  # Изменяющийся параметр
                values=ids
            )
        for id, sub in resp.result.iteritems():
            if int(sub[u'groups'][u'count']) > 0:
                subscriptions[id] = sub[u'groups'][u'items']
        return subscriptions
