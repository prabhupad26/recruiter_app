"""
Throttle:
- 30 req per sec
- 10k req daily
- limit -> pagesize:100
- limit -> id size : 100

"""
import requests
import os
from recruiter_app.utilities import helpers
import time
import urllib.parse
import asyncio
import aiohttp
from datetime import datetime


class StackExchangeData:
    quota_remaining = 0
    in_backoff_state = False
    back_off_till = None

    def __init__(self):
        config_props = helpers.get_prop("DATA_SOURCES").get("STACKOVERFLOW")
        self.access_token = os.environ['access_token']
        self.client_id = os.environ['client_id']
        self.session = requests.sessions.Session()
        self.default_params = {
            'order': 'desc',
            'sort': 'reputation',
            'site': 'stackoverflow',
            'client_id': self.client_id,
            'key': self.access_token
        }
        self.host = config_props.get('HOST')
        self.top_tag_url = config_props.get('user_top_tags')
        self.get_users_url = config_props.get('users')
        self.get_users_top_q = config_props.get('user_top_questions')
        self.get_users_top_a = config_props.get('user_top_answers')
        self.task_get_users = []

    def _fetch(self, url, **kwargs):
        """
        Synchronous http request call
        :param url: url string
        :param kwargs: params in url
        :return: response object
        """
        time.sleep(2)
        url = "".join([self.host, url])
        content = self.session.get(url, **kwargs)
        if content.status_code != 200:
            raise Exception(f"HTTP request {url} failed, err code : {content.status_code} \n"
                            f"Message : {content.content}")
        content = content.json()
        print(f"{'*' * 10}Quota remaining: {content.get('quota_remaining')}{'*' * 10}")
        if content.get('quota_remaining') <= 100:
            raise Exception("WARNING Limit is 100!!!!")
        if content.get('backoff'):
            print(f"backoff parameter received must wait for {content.get('backoff')}s")
            time.sleep(int(content.get('backoff')))
        return content

    async def handle_backoff(self, backoff):
        if StackExchangeData.quota_remaining < 1:
            print("stackexchange api Quota has been exhausted, will now wait till the reset")
            utc_midnight = datetime(2022, 9, datetime.utcnow().day + 1, 0, 0, 0, 0)
            utc_now = datetime.utcnow()
            backoff = utc_midnight.timestamp() - utc_now.timestamp()
        backoff = int(backoff)
        StackExchangeData.in_backoff_state = True
        print(f"backoff parameter received must wait for {backoff}s")
        StackExchangeData.back_off_till = time.time() + backoff + 2
        await asyncio.sleep(backoff + 2)
        print("backoff period is over resuming execution")
        StackExchangeData.in_backoff_state = False

    async def _async_fetch(self, url, **kwargs):
        """
        Async task to send the http requests
        :param url: complete url
        :param kwargs: keyword argument for passing param in http requests
        :return: "items" values in response received from the http requests
        """
        if StackExchangeData.in_backoff_state and time.time() < StackExchangeData.back_off_till:
            wait_period = StackExchangeData.back_off_till - time.time()
            if wait_period > 0:
                print(f"In backoff state and wait period is {wait_period}")
                await asyncio.sleep(wait_period)
            print("backoff period is over resuming execution")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                if response.status != 200:
                    if response.status == 403:
                        print(f"Cannot access this profile {url}")
                    else:
                        raise Exception(f"HTTP request {url} failed, err code : {response.status} \n"
                                        f"Message : {response.content}")
                content = await response.json()
                StackExchangeData.quota_remaining = content.get('quota_remaining')
                print(f"{'*' * 10}Quota remaining: {StackExchangeData.quota_remaining}{'*' * 10}")
                backoff = content.get('backoff')
                if backoff or StackExchangeData.quota_remaining < 1:
                    await self.handle_backoff(backoff)
                return content.get('items')

    def get_top_qna(self, query_type, user_id, tag_name, page=1, pagesize=100):
        """
        Fetch top qna data for a user for a tag - tag_name
        :param query_type: question tag or answer tag
        :param user_id: id of the user
        :param tag_name: name of tag
        :param page: page number
        :param pagesize: number of results per page
        :return: response object from the request
        """
        params = self.default_params.copy()
        params.update({"page": str(page),
                       "pagesize": str(pagesize),
                       "sort": "activity"})
        if query_type == 'question':
            url = self.get_users_top_q.format(user_id,
                                              urllib.parse.quote(tag_name))
        else:
            url = self.get_users_top_a.format(user_id,
                                              urllib.parse.quote(tag_name))
        response_obj = self._fetch(url, params=params)
        response_obj = response_obj.get('items')
        return response_obj

    def get_tags(self, users_list, page=1, pagesize=100):
        """
        Fetch tags of every user
        :param users_list: list of user ids (max - 100)
        :param page: page number
        :param pagesize: number of result per page (max 100)
        :yield: back response object and has_more indicator which tells
        the called function whether to continue or stop
        """
        users_list = [str(user.user_id) for user in users_list]
        print(f"Getting tags from stackoverflow for {len(users_list)} users")
        if len(users_list) > 100:
            raise Exception(f"Trying to fetch details for {len(users_list)} which is > 100")
        users_list = ";".join(users_list)
        params = self.default_params.copy()
        params.update({"page": str(page), "pagesize": str(pagesize)})
        url = self.top_tag_url.format(users_list)
        response_obj = self._fetch(url, params=params)
        has_more = response_obj.get('has_more')
        response_obj = response_obj.get('items')
        yield response_obj, has_more

    async def get_users(self, page_counts, page_size=100):
        """
        Calls users/ api for fetching 100 users per page,
        100 pages are requested at a time using helpers.create_batch
        and executed in asynch mode
        # TODO : Open issue : # 10
        :param page_counts: number of pages
        :param page_size: number of results returned per page
        :return:
        """
        users_obj_list = []
        url = "".join([self.host, self.get_users_url])
        for page_batch in helpers.create_batch(page_counts, start=1):
            for page in page_batch:
                print(f"Creating task for page {page}")
                params = self.default_params.copy()
                params.update({"page": str(page), "pagesize": str(page_size)})
                self.task_get_users.append(asyncio.create_task(self._async_fetch(url,
                                                                                 params=params)))
            users_obj_per_pages = await asyncio.gather(*self.task_get_users)
            [[users_obj_list.append(user_obj) for user_obj in user_obj_page]
             for user_obj_page in users_obj_per_pages]
            self.task_get_users = []
        return users_obj_list
