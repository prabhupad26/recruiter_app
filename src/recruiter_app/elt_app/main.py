from recruiter_app.elt_app.api import *
from recruiter_app.elt_app.collections import *
from recruiter_app.elt_app.service import *
from recruiter_app.utilities.helpers import mongo_global_init, get_prop
import asyncio
from tqdm import tqdm
import sys


class SOFactory(StackExchangeData):
    """
    Orchestrate actions between stackoverflow api calls and data update
    """
    user_counter = 1

    def __init__(self, mongo_host_type='local'):
        super().__init__()
        mongo_global_init(host_type=mongo_host_type)

    def get_tags_users_list(self, tags_threshold=5):
        """
        Fetch the users for which tags_top_qna_data_available
        is != True
        :param tags_threshold: threshold for number of top questions/answers
        :return:
        """
        print("Fetching existing users with tags_score")
        tags_users_dict = {}
        for data in StackOverflowUser.objects(tags_top_qna_data_available__ne=True):
            tags = []
            for tag in list(data.tags_score.keys()):
                tags_data_available = StackOverflowUser.objects().filter(
                    user_id=data.user_id)[0]['tags_data_available']
                if tags_data_available:
                    tags.append(data.tags_score[tag]['name'])
            tags_users_dict[data.user_id] = tags[:tags_threshold + 1]
        return tags_users_dict

    def get_incomplete_users(self, users_obj=None, has_more=True, threshold=10):
        """
        Fetch the users for which the tags_data_available is != True
        Also checks if users in users_obj have achieved the threshold
        :param users_obj: list of users for which the tags data is to be fetched
        :param has_more: tell the calling func that more users which do not have tags data are available
        :param threshold:
        :return: users_obj, more_users,
        reset_page - whenever a new user is added the page counter
        should reset to 0 again
        """
        reset_page = False
        if users_obj:
            for user_obj in users_obj:
                reset_page = mongo.service_update_tags_data_available(has_more,
                                                                      user_obj,
                                                                      threshold)
        users_obj = StackOverflowUser.objects(tags_data_available__ne=True).limit(100)
        more_users = True if len(StackOverflowUser.objects(
            tags_data_available__ne=True
        ).limit(101)) > 100 else False
        return users_obj, more_users, reset_page

    def update_user_tag_coll_qna(self):
        """
        Fetch the qna scores for every user for which tags_top_qna_data_available
        is != True
        Async issue :
        https://github.com/Big-Data-Programming/big-data-programming-april2022-team_apps/issues/3
        :return:
        """
        tag_users_data = self.get_tags_users_list()
        top_qna_results_list = []
        if tag_users_data:
            print(f"Updating top qna details for {tag_users_data} users")
            for user in tag_users_data:
                print(f"Getting QnA scores for user - {user}")
                target_tags = tag_users_data[user]
                for target_tag in target_tags:
                    top_qna_results_list.append((user, target_tag))
                    mongo.service_update_top_qna(user,
                                                 self.get_top_qna('question',
                                                                  user, target_tag),
                                                 target_tag,
                                                 'question')
                    mongo.service_update_top_qna(user,
                                                 self.get_top_qna('answer',
                                                                  user, target_tag),
                                                 target_tag,
                                                 'answer')
        else:
            print("No users document with tag details object, skipping top qna update")

    def create_user_tags_collection(self):
        """
        Fetch top tags of multiple users (max 100 users at a time)
        :return: None
        """
        print("Creating user tags details")
        existing_users_list, _, _ = self.get_incomplete_users()
        more_incomplete_users = True
        if existing_users_list:
            page = 1
            while more_incomplete_users:
                print(f"Looking in page {page}")
                for response_obj, has_more in self.get_tags(existing_users_list, page):
                    mongo.service_create_user_tags_records(response_obj)
                    existing_users_list, more_incomplete_users, reset_page = self.get_incomplete_users(
                        existing_users_list,
                        has_more)
                    page += 1
                    if reset_page:
                        print(f"New users added, resetting the page index")
                        page = 1
                    if not more_incomplete_users:
                        print("No more users are available for which tags are to be fetched")
                        break
                    self.update_user_tag_coll_qna()
        if not len(existing_users_list):
            """
            Just in case the top qna props were not updated for every 
            tag object
            """
            self.update_user_tag_coll_qna()
        print("Users Tag creation completed")

    def create_user_collection(self):
        """
        - Keep fetching the data until the mining target is achieved
          - Basic details of stackoverflow users and call mongodb's
            service_create_record
        """
        print("Creating user_details collection")
        target_counts = get_prop("MINING_TARGET").get("SO_COUNT")
        page_counts = target_counts // 100
        print(f"To achieve target {target_counts}, will look in {page_counts} pages")
        users_data_list = asyncio.run(self.get_users(page_counts=page_counts))
        for user_data in users_data_list:
            mongo.service_create_record(user_data)
        print("User collections created with basic details")
        self.create_user_tags_collection()


class GHFactory(GithubData):
    """
    Orchestrate actions between GitHub api calls and data update
    """
    # TODO : Feature to extract any github feature for existing candidate

    def __init__(self, mongo_host_type='local'):
        super().__init__()
        mongo_global_init(host_type=mongo_host_type)

    def build_users_collection(self, jd_name):
        """
        Using GitHub search api the users are searched with jd_name
        The search will keep happening till mining target is achieved
        or page till 10
        :param jd_name: name of the job description
        :return: None
        """
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        target_counts = get_prop("MINING_TARGET").get("GH_COUNT")
        page = 0
        with tqdm(total=target_counts.get(jd_name)) as pbar:
            # GitHub search limit is 1000 results in total that's why page < 11
            while len(GithubUser.objects(for_jd=jd_name)) < target_counts.get(jd_name) and page < 11:
                print(f"\nGetting users in page {page}")
                data_json = self.get_users_list(jd_name, page)
                if len(data_json.get('items')) > 0:
                    user_list = [item.get('login') for item in data_json.get('items')]
                    user_list = asyncio.run(self.exec_get_user_foll(user_list))
                    print("\nFiltering out the users which are already there in collection")
                    user_list = list(filter(lambda x: not GithubUser.objects(login_name=x), user_list))
                    if user_list:
                        print(f"\nGetting the data for {len(user_list)} users")
                        results_users_obj, results_user_repo_obj = asyncio.run(self.exec_get_user_repo(user_list))
                        for user_details_obj, user_repo_obj in zip(results_users_obj, results_user_repo_obj):
                            if user_details_obj is not None and user_repo_obj is not None and len(user_repo_obj):
                                login_name = user_details_obj.get('login')
                                if login_name and not GithubUser.objects(login_name=login_name):
                                    print(f"Insert docs started for users in page {page}")
                                    mongo.service_create_github_users(jd_name,
                                                                      user_details_obj,
                                                                      user_repo_obj)
                    pbar.set_description("\nBuilding users collection progress ")
                    pbar.update(len(GithubUser.objects(for_jd=jd_name)))
                else:
                    print(f"No more users found for {jd_name}")
                    break
                page += 1


class RedditFactory(RedditData):
    """
        Orchestrate actions between reddit api calls and data update
    """

    def __init__(self, mongo_host_type='local'):
        super().__init__()
        mongo_global_init(host_type=mongo_host_type)

    def create_user_obj(self, content_objs, content_type='article'):
        """
        Formats the data so that the mongo service can update it in
        database
        :param content_objs:  dict of content data
        :param content_type: type of content - article or comment
        :return:
        """
        users_obj = {}
        article_ids = []
        after = None
        print(f"\nCreating users_obj from API response for {content_type}")
        for content_obj in tqdm(content_objs):
            content_obj = content_obj.get("data")
            if content_obj.get("author") not in users_obj:
                users_obj[content_obj.get("author")] = {}
            content_name = f"{content_type}_{content_obj.get('id')}"
            if content_name not in users_obj[content_obj.get("author")]:
                users_obj[content_obj.get("author")][content_name] = {}
            users_obj[content_obj.get("author")][content_name]["score"] = content_obj.get("score")
            users_obj[content_obj.get("author")][content_name]["awards"] = \
                content_obj.get("total_awards_received")
            if content_type == 'comment':
                users_obj[content_obj.get("author")][content_name]["body"] = \
                    content_obj.get("body")
            if content_type == 'article':
                users_obj[content_obj.get("author")][content_name]["title"] = content_obj.get("title")
                users_obj[content_obj.get("author")][content_name]["selftext"] = content_obj.get("selftext")
                users_obj[content_obj.get("author")][content_name]["upvote_ratio"] = \
                    content_obj.get("upvote_ratio")
                after = f"t3_{content_obj.get('id')}"
                article_ids.append(content_obj.get('id'))
        return users_obj, after, article_ids

    def create_users_from_comments(self, jd, article_ids):
        """
        Create users collection using data from comments
        :param jd: name of thread
        :param article_ids: list of article ids
        :return:
        """
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        articles_comments_obj = asyncio.run(self.exec_get_article_comments(jd, article_ids))
        if articles_comments_obj:
            for article_comments_obj in articles_comments_obj:
                users_obj, _, _ = self.create_user_obj(article_comments_obj,
                                                       content_type="comment")
                mongo.service_create_rd_record(users_obj, jd)

    def create_user_from_articles(self, articles_obj, jd):
        """
        Create users collection from articles
        :param articles_obj:
        :param jd:
        :return:
        """
        users_obj, after, article_ids = self.create_user_obj(articles_obj,
                                                             content_type="article")
        mongo.service_create_rd_record(users_obj, jd)
        self.create_users_from_comments(jd, article_ids)
        return after

    def build_users_collection(self, jds):
        """
        Using reddit api the users are searched from specific threads
        defined in jds list the search will keep happening till mining
        target is achieved or page till 10
        :param jds: list of reddit threads
        :return: None
        """
        target_counts = get_prop("MINING_TARGET").get("REDDIT_COUNTS")
        for jd in jds:
            after = None
            while len(RedditUserProps.objects(for_jd=jd)) < target_counts.get(jd):
                articles_obj = self.get_articles(jd, after)
                if len(articles_obj) > 0:
                    last_article_id = self.create_user_from_articles(articles_obj, jd)
                    after = last_article_id
                    print(f"will start fetching results after {after}")
                    print(f"{target_counts.get(jd) - len(RedditUserProps.objects(for_jd=jd))} "
                          f"away from target for jd - {jd}")
                else:
                    print("No more articles found")
                    break
            print(f"{jd} completed moving on to next jd")

