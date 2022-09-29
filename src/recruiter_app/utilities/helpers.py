import json
import os
import mongoengine
import requests
from tqdm import tqdm
import re
import pandas as pd


def read_passwd():
    """
    Reads the password from a environment variable.
    """
    pass_store = {}
    if os.environ.get('session_key') and os.environ.get('session_password'):
        pass_store['session_key'] = os.environ.get('session_key')
        pass_store['session_password'] = os.environ.get('session_password')
    else:
        raise Exception("Either of session_key or session_password not set in the environment")
    return pass_store


def get_prop(prop_name):
    """
    Returns the props in config/config.json.
    """
    with open("config/config.json", "r") as f:
        config = json.load(f)
    for key, value in config.items():
        if key == prop_name:
            return value
    raise Exception(f"prop {prop_name} not found in config file at : config/config.json")


def mongo_global_init(host_type='local'):
    """
    Initialises mongo db connection which is available globally for
    every document object, syntax for defining a DOM (document object mapper):
    Extend the class from mongoengine.Document and initialise below dict
    in a variable named meta
    meta = {
        "db_alias": 'core',
        "collection": 'candidate_ratings'
    }
    :param host_type: to use mongo cluster use - "cloud",
    to use the mongo local instance use - "local"
    default port for both is 27017
    :return: None
    """
    if host_type == 'local':
        alias_core = 'core'
        db_name = 'hush_recruiter'
        data = {"host": "localhost", "port": 27017}
        mongoengine.register_connection(alias=alias_core, name=db_name, **data)
    else:
        print(f'Host type is {host_type}')
        alias_core = 'core'
        db_name = 'hush_recruiter'
        username = os.environ['mongo_user']
        password = os.environ['mongo_pass']
        data = {"host": f"mongodb+srv://{username}:{password}@cluster0.oonus.mongodb.net/?retryWrites=true&w=majority",
                "port": 27017,
                "username": username,
                "password": password}
        mongoengine.register_connection(alias=alias_core, name=db_name, **data)


def get_auth_token_reddit():
    client_id = os.environ['reddit_client_id']
    client_secret = os.environ['reddit_client_secret']
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    reddit_username = os.environ['reddit_user_name']
    reddit_password = os.environ['reddit_password']
    data = {
        'grant_type': 'password',
        'username': reddit_username,
        'password': reddit_password
    }
    auth_url = get_prop("DATA_SOURCES").get("REDDIT").get("token_retrieval")
    headers = {'User-Agent': 'Tutorial2/0.0.1',
               'Content-Type': 'application/x-www-form-urlencoded'}
    res = requests.post(auth_url, auth=auth, data=data, headers=headers)
    if res.status_code == 200:
        print("Authorization successful")
        res = res.json()
        return f"Bearer {res.get('access_token')}", res.get("expires_in")
    raise Exception("Authorization with reddit was not successful")


def create_batch(users, batch_size=100, start=0,
                 description= "\nProcessing batch {0}"):
    if type(users) == int:
        users = [i for i in range(users)]
    if type(users) == list or type(users) == mongoengine.queryset.queryset.QuerySet:
        with tqdm(total=len(users)) as pbar:
            for i in range(start, len(users), batch_size):
                next_batch = [user for user in users[i:i + batch_size]]
                pbar.set_description(description.format(i))
                pbar.update(batch_size)
                yield next_batch


def get_ad_score_weights(data_obj, data_source):
    final_weight = None
    if data_source == "stackoverflow":
        final_weight = 5
        if data_obj.gold_badge_count != 0:
            final_weight -= 1
        if data_obj.silver_badge_count != 0:
            final_weight -= 1
        if data_obj.bronze_badge_count != 0:
            final_weight -= 1
        if data_obj.reputation != 0:
            final_weight -= 1
        if data_obj.accept_rate != 0:
            final_weight -= 1
    elif data_source == "github":
        final_weight = 3
        if data_obj.followers != 0:
            final_weight -= 1
        if data_obj.public_repos != 0:
            final_weight -= 1
        if data_obj.public_gists != 0:
            final_weight -= 1
    return final_weight


def get_base_label(label, base_map):
    for base_label in base_map:
        if label in base_map[base_label]:
            return base_label
    # TODO : Remove this return when all tags are labelled
    return label


def sort_by_id(str_list):
    if len(str_list) == 1:
        # handling due to data issue
        return str_list
    str_list.sort(key=lambda x: re.findall(r'\d+', x)[0], reverse=True)
    return str_list


def load_base_scores():
    return {"feature_question_score": 0,
            "feature_answer_score": 0,
            "feature_top_question": 0,
            "feature_top_answer": 0,
            "feature_top_a_accepted": 0,
            "feature_forks": 0,
            "feature_stars": 0,
            "feature_watchers": 0,
            "feature_repo_count": 0}


def get_scores_dict(keys_list, tag_obj):
    total_score = 0
    for key_name in keys_list:
        total_score += tag_obj.get(key_name)
    return total_score


def sort_by_scores(repo_list, lang_score_obj):
    sorted_list = [(repo, lang_score_obj.get(repo)) for repo in repo_list]
    sorted_list.sort(key=lambda x: x[1], reverse=True)
    return [e[0] for e in sorted_list]


def get_all_feature_scores(skill_obj):
    ft_scores_dict = {"so_q_score": skill_obj.get('feature_question_score'),
                      "so_a_score": skill_obj.get('feature_answer_score'),
                      "so_top_q_score": skill_obj.get('feature_top_question'),
                      "so_top_a_score": skill_obj.get('feature_top_answer'),
                      "so_top_a_isa_score": skill_obj.get('feature_top_a_accepted'),
                      "gh_forks_count": skill_obj.get('feature_forks'),
                      "gh_stars_count": skill_obj.get('feature_stars'),
                      "gh_watchers_count": skill_obj.get('feature_watchers'),
                      "gh_repo_count": skill_obj.get('feature_repo_count')}
    return ft_scores_dict


def get_so_tags_count(tags_prop_obj):
    skill_name_counts = {}
    len_tags_prop_obj = len(tags_prop_obj)
    for tag_idx in range(len_tags_prop_obj):
        for tag in tags_prop_obj[tag_idx].tags_score.keys():
            if tag.startswith('tag_'):
                tag_name = tags_prop_obj[tag_idx].tags_score.get(tag).get('name')
                if tag_name:
                    if tag_name not in skill_name_counts:
                        skill_name_counts[tag_name] = 0
                    skill_name_counts[tag_name] += 1
    df = pd.DataFrame().from_dict(skill_name_counts, orient='index')
    df.to_csv('so_skills_count.csv')


def get_gh_lang_count(tags_prop_obj):
    skill_name_counts = {}
    len_tags_prop_obj = len(tags_prop_obj)
    for tag_idx in range(len_tags_prop_obj):
        for tag in tags_prop_obj[tag_idx].lang_score.keys():
            if tag.startswith('lang_'):
                tag_name = tag.split("lang_")[1]
                if tag_name not in skill_name_counts:
                    skill_name_counts[tag_name] = 0
                skill_name_counts[tag_name] += 1
    df = pd.DataFrame().from_dict(skill_name_counts, orient='index')
    df.to_csv('gh_skills_count.csv')

# TODO : [Placeholder] for reddit additional score

# def get_rd_content_count(self):
#         tags_prop_obj = RedditUserProps.objects()
#         skill_name_counts = {}
#         len_tags_prop_obj = len(tags_prop_obj)
#         for tag_idx in range(len_tags_prop_obj):
#             for_jd = tags_prop_obj[tag_idx].for_jd
#             for tag in tags_prop_obj[tag_idx].thread_props.keys():
#                 if tag.startswith('comment_'):
#                     skill_name_counts[tags_prop_obj
#                     [tag_idx].thread_props[tag]['body']] = for_jd
#                 if tag.startswith('article_'):
#                     skill_name_counts[tags_prop_obj
#                     [tag_idx].thread_props[tag]['title']] = for_jd
#         df = pd.DataFrame().from_dict(skill_name_counts, orient='index')
#         df.to_csv('rd_skills_count.csv')


def get_skill_tag_map(df):
    """
    Dict structure : {"c#": ["c#", "c_sharp"]}
    :param df:
    :return:
    """
    tag_map = {}
    all_tags = set(df.tags.values)
    for tag in all_tags:
        if isinstance(tag, str):
            if tag not in tag_map:
                tag_map[tag] = []
            tag_map[tag].extend(df[df.tags == tag].tag_names.values)
    return tag_map


def run_prep_skill_count_csv(so_user_list, gh_user_list):
    print("Prep stackoverflow started")
    get_so_tags_count(so_user_list)
    print("Prep github started")
    get_gh_lang_count(gh_user_list)
    # TODO : [Placeholder] for reddit additional score
    # print("Prep reddit started")
    # get_rd_content_count(self.rd_user_list)
