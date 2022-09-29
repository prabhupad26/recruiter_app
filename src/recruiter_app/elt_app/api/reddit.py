from recruiter_app.utilities import helpers
import requests
import time
import asyncio
import aiohttp


class RedditData:
    global_wait = 0

    def __init__(self):
        self.session_token, self.session_time = helpers.get_auth_token_reddit()
        self.session = requests.sessions.Session()
        self.headers = {"Authorization": self.session_token}
        self.session.headers = self.headers

        self.host_url = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("HOST")
        self.web_dev_thread = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("web_dev_thread")
        self.devops_thread = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("devops_thread")
        self.cyber_seq_thread = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("cyber_seq_thread")
        self.ml_thread = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("ml_thread")
        self.py_thread = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("py_thread")
        self.comments = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("comments")
        self.user_details = helpers.get_prop("DATA_SOURCES").get("REDDIT").get("user_details")
        self.tasks = []

    def _fetch(self, url, **kwargs):
        # time.sleep(2)
        complete_url = "".join([self.host_url, url])
        content = self.session.get(complete_url, **kwargs)
        if content.status_code != 200:
            if content.status_code == 429:
                retry_count = 10
                while retry_count:
                    print("Too many requests exception returned from server , going to sleep 5s")
                    time.sleep(5)
                    content = self.session.get(complete_url, **kwargs)
                    if content.status_code == 200:
                        print("retry successful")
                        break
                    retry_count -= 1
                if retry_count == 0:
                    raise Exception("Retry failed, please rerun")
            else:
                raise Exception(f"HTTP request {url} failed, err code : {content.status_code} \n"
                                f"Message : {content.content}")
        quota_remaining = content.headers.get('x-ratelimit-remaining')
        reset_on = content.headers.get('x-ratelimit-reset')
        print(f"{'*' * 10}Quota remaining: {quota_remaining}{'*' * 10}")
        if quota_remaining == 0:
            print(f"Waiting for about {reset_on}s for github quota to reset ")
            time.sleep(int(reset_on) - time.time())
        return content

    def get_articles(self, thread_name, after=None, t='all', limit=100):
        """
        Get article details from the api
        :param thread_name: name of reddit thread
        :param after: show results after list index
        :param t: 'all' for all time top articles
        :param limit: number of articles per page
        :return: response object in json
        """
        url = f"{self.__getattribute__(thread_name)}/top"
        params = {
            't': t,
            "limit": limit,
        }
        if after:
            params['after'] = after
            params['count'] = 1
        res = self._fetch(url, params=params)
        res = res.json()
        res = res.get("data").get("children")
        return res

    async def get_article_comments(self, session, thread_name, article_id, limit=100):
        """
        Get article comments from the api
        :param session: aiohttp client session object
        :param thread_name: name of thread
        :param article_id: id of the article
        :param limit: number of comments per page
        :return: comment object in json
        """
        if RedditData.global_wait > 0:
            await asyncio.sleep(RedditData.global_wait)
            print(f"Resetting the global wait time of {RedditData.global_wait} to 0s")
            RedditData.global_wait = 0

        url = f"{self.__getattribute__(thread_name)}/comments/{article_id}"
        complete_url = "".join([self.host_url, url])
        params = {
            "limit": limit,
        }
        async with session.get(complete_url, params=params, headers=self.headers) as response:
            if response.status != 200:
                if response.status == 429:
                    retry_count = 10
                    while retry_count:
                        print("Too many requests exception returned from server , going to sleep 5s")
                        await asyncio.sleep(5)
                        response = await self.get_article_comments(session, thread_name,
                                                                   article_id, limit=100)
                        if response.status == 200:
                            print("retry successful")
                            break
                        retry_count -= 1
            quota_remaining = response.headers.get('x-ratelimit-remaining')
            reset_on = response.headers.get('x-ratelimit-reset')
            print(f"{'*' * 10}Quota remaining: {quota_remaining}{'*' * 10}")
            if quota_remaining == 0:
                print(f"Quota reached setting wait period of {reset_on}s")
                RedditData.global_wait = int(reset_on) - time.time()

            response = await response.json()
            if len(response) > 1:
                return response[1].get("data").get("children")
            print(f"There are no comments for article_id {article_id}")
            return None

    async def exec_get_article_comments(self, jd, article_ids):
        """
        Asyncio coroutine to fetch article comments
        :param jd: name of reddit thread
        :param article_ids: list of articles
        :return:
        """
        async with aiohttp.ClientSession() as session:
            for article_id in article_ids:
                self.tasks.append(self.get_article_comments(session, jd, article_id))
            results = await asyncio.gather(*self.tasks)
            self.tasks = []
        return results
