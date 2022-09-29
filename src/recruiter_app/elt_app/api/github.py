import os
from recruiter_app.utilities import helpers
import requests
import time
import asyncio
import aiohttp
from tqdm import tqdm


class GithubData:
    quota_remaining = None
    reset_on = 0
    quota_checked = False

    def __init__(self):
        config_props = helpers.get_prop("DATA_SOURCES").get("GITHUB")
        self.access_token = os.environ['github_pat']
        self.session = requests.sessions.Session()
        self.host = config_props.get('HOST')
        self.search_users = config_props.get('search_users')
        self.user_details = config_props.get('user_details')
        self.user_repos_list = config_props.get('user_repos_list')
        self.user_repo_details = config_props.get('user_repo_details')
        self.user_followers_details = config_props.get('user_followers_url')
        self.user_following_details = config_props.get('user_following_url')
        self.check_quota_url = config_props.get('check_quota')
        self.auth_headers = {"Authorization": os.environ['github_pat']}
        self.session.headers.update(self.auth_headers)
        self.task_users_obj = []
        self.task_user_repo_obj = []
        self.task_user_foll = []

    def _fetch(self, url, **kwargs):
        """
        Function to send the http request
        :param url: url
        :param kwargs: params in url
        :return: json response object
        """
        # time.sleep(2)
        url = "".join([self.host, url])
        content = self.session.get(url, **kwargs)
        if content.status_code != 200:
            raise Exception(f"HTTP request {url} failed, err code : {content.status_code} \n"
                            f"Message : {content.content}")
        quota_remaining = int(content.headers.get('X-RateLimit-Remaining'))
        reset_on = int(content.headers.get('X-RateLimit-Reset'))
        print(f"{'*' * 10}Quota remaining: {quota_remaining}{'*' * 10}")
        if quota_remaining == 0:
            print(f"Waiting for about {reset_on}s for github quota to reset ")
            time.sleep(int(reset_on) - time.time())
        return content.json()

    def get_users_list(self, query_keyword, page=0, page_limit=100):
        """
        Get the list of users
        :param query_keyword: search with job title
        :param page: page number
        :param page_limit: number of results per page
        :return: list of users
        """
        params = {
            "q": query_keyword,
            "page": page,
            "per_page": page_limit
        }
        url = self.search_users
        return self._fetch(url, params=params, headers=self.auth_headers)

    async def check_quota(self, session):
        url = "".join([self.host, self.check_quota_url])
        async with session.get(url, headers=self.auth_headers) as response:
            if response.status != 200:
                raise Exception(f"HTTP request {url} failed, err code : {response.status} \n"
                                f"Message : {response.content}")
            quota_remaining = int(response.headers.get('X-RateLimit-Remaining'))
            reset_on = int(response.headers.get('X-RateLimit-Reset'))
            print(f"{'*' * 10}Quota remaining: {quota_remaining}{'*' * 10}")
            return quota_remaining, reset_on

    async def _fetch_async(self, session, url, **kwargs):
        """
        Asyncio coroutine to send the http requests for multiple users
        Quota limit handling:
        GitHub apis are limited to 5k requests per hour, once this
        quota is exhausted the code will wait on reset_on parameter
        which is obtained from the api header response.
        All the async calls
        will wait till the quota is reset
        :param session: aiohttp session
        :param url: url
        :param kwargs: param in url
        :return: json response object
        """
        print(f"{'*' * 10}Quota remaining: {GithubData.quota_remaining}{'*' * 10}")
        complete_url = "".join([self.host, url])
        if GithubData.quota_remaining < 1:
            while GithubData.reset_on - time.time() > 0 and GithubData.quota_remaining < 1:
                print(f"Wait period is still in future so waiting for {GithubData.reset_on - time.time()}s")
                await asyncio.sleep(int(GithubData.reset_on - time.time()) + 2)
                print("Wait period is over, execution will continue now")
                if not GithubData.quota_checked:
                    print("Checking new quota now")
                    GithubData.quota_checked = True
                    GithubData.quota_remaining, GithubData.reset_on = await self.check_quota(session)
                    GithubData.quota_checked = False
            if GithubData.reset_on - time.time() < 0 and not GithubData.quota_checked:
                print("reset_on is old, updating reset_on and quota")
                GithubData.quota_checked = True
                GithubData.quota_remaining, GithubData.reset_on = await self.check_quota(session)
                GithubData.quota_checked = False
            print(f"New quota is {GithubData.quota_remaining}")
        await asyncio.sleep(10)
        try:
            GithubData.quota_remaining -= 1
            async with session.get(complete_url, **kwargs) as response:
                if response.status != 200:
                    if response.status == 403:
                        print(f"Cannot access this profile {complete_url}")
                    else:
                        raise Exception(f"HTTP request {url} failed, err code : {response.status} \n"
                                        f"Message : {response.content}")
                content = await response.json()
                return content
        except Exception as e:
            """
            This handling is done for 3types of errors I have seen so far and its root cause is unknown:
            - cannot connect to host TimeOutError is raised
            - cannot access the profile (same profile can be accessed manually)
            - 502 - bad gateway
            - 503 - resource unavailable
            """
            print(f"Connection failed with error : {e}")

    async def exec_get_user_repo(self, user_list, page_limit=100):
        """
        Get user details and user repositories details
        :param user_list:
        :param page_limit:
        :return: list of user details and list of user repo details
        """
        params = {
            "per_page": page_limit
        }
        async with aiohttp.ClientSession() as session:
            GithubData.quota_remaining, GithubData.reset_on = await self.check_quota(session)
            list_users_obj = []
            list_user_repo_obj = []
            for gh_user_batch in helpers.create_batch(user_list):
                for gh_user in gh_user_batch:
                    self.task_users_obj.append(self._fetch_async(session,
                                                                 self.user_details.format(gh_user),
                                                                 headers=self.auth_headers))
                    self.task_user_repo_obj.append(self._fetch_async(session,
                                                                     self.user_repos_list.format(gh_user),
                                                                     params=params,
                                                                     headers=self.auth_headers))
                print("Starting 100 async requests")
                results_users_obj = await asyncio.gather(*self.task_users_obj)
                list_users_obj.extend(results_users_obj)
                print("Wait for 10s before executing next 100 async requests")
                time.sleep(10)
                print("Starting 100 async requests")
                results_user_repo_obj = await asyncio.gather(*self.task_user_repo_obj)
                list_user_repo_obj.extend(results_user_repo_obj)
                self.task_users_obj = []
                self.task_user_repo_obj = []
        return list_users_obj, list_user_repo_obj

    async def exec_get_user_foll(self, user_list, page_limit=50):
        """
        Pick 50 followers + 50 following users
        :param user_list:
        :param page_limit:
        :return:
        """
        # TODO : Check if it is fine to include followers ?
        params = {
            "per_page": page_limit
        }
        async with aiohttp.ClientSession() as session:
            GithubData.quota_remaining, GithubData.reset_on = await self.check_quota(session)
            final_list = []
            for gh_user_batch in helpers.create_batch(user_list):
                for gh_user in gh_user_batch:
                    self.task_user_foll.append(self._fetch_async(session,
                                                                 self.user_followers_details.format(gh_user),
                                                                 params=params,
                                                                 headers=self.auth_headers))
                    self.task_user_foll.append(self._fetch_async(session,
                                                                 self.user_following_details.format(gh_user),
                                                                 params=params,
                                                                 headers=self.auth_headers))
                results_users_foll_obj = await asyncio.gather(*self.task_user_foll)
                self.task_user_foll = []
                final_users_list = []
                print("Preparing the final users list")
                if results_users_foll_obj:
                    for user_objs in results_users_foll_obj:
                        if user_objs and len(user_objs) > 0:
                            for user_obj in user_objs:
                                if user_obj:
                                    final_users_list.append(user_obj.get("login"))
                final_list.extend(final_users_list)
            print(f"Users list of size {len(final_list)} created")
        return final_list
