from recruiter_app.elt_app.collections.gh_users_details import GithubUser
from recruiter_app.elt_app.collections.reddit_user_props import RedditUserProps
from recruiter_app.elt_app.collections.so_users_details import StackOverflowUser
from recruiter_app.elt_app.collections.candidate_ratings import CandidateRatings
import re


def service_create_record(user_data):
    """
    Updates the data received from the api call
    into so_users_details collection
    :param user_data: dict containing the basic
    details of user
    :return: _id in mongo db
    """
    if not StackOverflowUser.objects().filter(user_id=user_data.get('user_id')):
        user_obj = {'user_id': user_data.get('user_id'),
                    'reputation': user_data.get('reputation'),
                    'accept_rate': user_data.get('accept_rate'),
                    'display_name': user_data.get('display_name'),
                    'gold_badge_count': user_data.get('badge_counts').get('gold'),
                    'silver_badge_count': user_data.get('badge_counts').get('silver'),
                    'bronze_badge_count': user_data.get('badge_counts').get('bronze'),
                    'website_url': user_data.get('website_url')}
        so_data = StackOverflowUser()
        so_data.display_name = user_obj['display_name']
        so_data.user_id = user_obj['user_id']
        so_data.gold_badge_count = user_obj['gold_badge_count']
        so_data.silver_badge_count = user_obj['silver_badge_count']
        so_data.bronze_badge_count = user_obj['bronze_badge_count']
        so_data.accept_rate = user_obj['accept_rate']
        so_data.reputation = user_obj['reputation']
        so_data.website_url = user_obj['website_url']

        so_data.save()
        return so_data.id
    print(f"Stackoverflow User {user_data.get('user_id')} already present in db")


def service_update_tags_data_available(has_more, user_obj, threshold):
    user_tags = StackOverflowUser.objects().filter(user_id=user_obj.user_id)[0]
    if len(user_tags.tags_score) > threshold or (len(user_tags.tags_score) < threshold and not has_more):
        user_obj.tags_data_available = True
        user_obj.save()
        reset_page = True
    else:
        reset_page = False
    return reset_page


def service_update_top_qna(user, data_obj_list, tag_name, query_type):
    """
    Update top question and answer data for the tag - tag_name
    :param user: id of the user
    :param data_obj_list: top qna data list
    :param tag_name: name of tag
    :param query_type: type of tag - question or answer
    :return: None
    """
    tag_name = f"tag_{tag_name}"
    tag_name = re.sub("[`~!@#$%^&*()\\]\\[+={}/|:;\"\'<>,.?-]", '_', tag_name)
    user_tags_score_obj = StackOverflowUser.objects(user_id=user)[0]
    for data_obj in data_obj_list:
        if query_type == 'question':
            user_tags_score_obj.tags_score[tag_name][f"top_question_{data_obj.get('question_id')}_score"] = \
                data_obj.get('score')
        else:
            user_tags_score_obj.tags_score[tag_name][f"top_answer_{data_obj.get('answer_id')}_score"] = \
                data_obj.get('score')
            user_tags_score_obj.tags_score[tag_name][f"top_answer_{data_obj.get('answer_id')}_is_accepted"] = \
                data_obj.get('is_accepted')
    user_tags_score_obj.tags_top_qna_data_available = True
    user_tags_score_obj.save()


def service_create_user_tags_records(data):
    """
    Updates the tags_score dict field with format
    {
        "tags_score": {
            "tag_name": {
                {"question_score": {question_score},
                 "answer_score": {answer_score},
                 "name": {original_tag_name}
            }
        }
    }
    :param data:
    :return: None
    """
    print("Creating the user tag records for new users")
    for user_tag_data in data:
        user_data = StackOverflowUser.objects().filter(user_id=user_tag_data.get('user_id'))[0]
        tag_obj_name = f"tag_{user_tag_data.get('tag_name')}"
        tag_obj_name = re.sub("[`~!@#$%^&*()\\]\\[+={}/|:;\"\'<>,.?-]", '_', tag_obj_name)
        user_data.tags_score[tag_obj_name] = {}
        if user_tag_data.get('question_count') > 0:
            score_per_q = user_tag_data.get('question_score') / user_tag_data.get('question_count')
            user_data.tags_score[tag_obj_name]['question_score'] = score_per_q
        if user_tag_data.get('answer_count') > 0:
            score_per_a = user_tag_data.get('answer_score') / user_tag_data.get('answer_count')
            user_data.tags_score[tag_obj_name]['answer_score'] = score_per_a
        user_data.tags_score[tag_obj_name]['name'] = user_tag_data.get('tag_name')
        user_data.tags_data_available = True
        user_data.save()


def service_create_github_users(jd_name, data_obj, repo_objs):
    """
    Creating the collection with user details and user repo details
    :param jd_name: job title
    :param data_obj: user details dict
    :param repo_objs: user repo details dict
    :return: None
    """
    gh_user = GithubUser()
    gh_user.login_name = data_obj.get('login')
    gh_user.name = data_obj.get('name') if data_obj.get('name') else data_obj.get('login')
    gh_user.email = data_obj.get('email')
    gh_user.bio = data_obj.get('bio')
    gh_user.followers = data_obj.get('followers')
    gh_user.public_repos = data_obj.get('public_repos')
    gh_user.public_gists = data_obj.get('public_gists')
    gh_user.for_jd = jd_name
    gh_user.lang_score = {}
    for idx, repo_obj in enumerate(repo_objs, start=1):
        prog_language = repo_obj.get('language')
        if prog_language:
            prog_language = prog_language.replace(' ', '_').lower()
            if f"lang_{prog_language}" not in gh_user.lang_score:
                gh_user.lang_score[f"lang_{prog_language}"] = {}

            gh_user.lang_score[f"lang_{prog_language}"] \
                [f"repo_{idx}_forks"] = repo_obj.get('forks_count')

            gh_user.lang_score[f"lang_{prog_language}"] \
                [f"repo_{idx}_stars"] = repo_obj.get('stargazers_count')

            gh_user.lang_score[f"lang_{prog_language}"] \
                [f"repo_{idx}_watchers"] = repo_obj.get('watchers_count')
    gh_user.save()


def service_create_rd_record(users_obj, jd):
    """
    Create reddit users collections
    :param users_obj: users dict
    :param jd: name of job title
    :return: None
    """
    print(f"\nInserting users_obj for jd - {jd} to collection")
    for user_props in users_obj:
        if RedditUserProps.objects(user_name=user_props):
            rup = RedditUserProps.objects(user_name=user_props)[0]
            rup.update(thread_props=users_obj[user_props])
        else:
            if user_props and jd:
                rup = RedditUserProps()
                rup.user_name = user_props
                rup.for_jd = jd
                rup.thread_props = users_obj[user_props]
                rup.save()


def service_update_alter_ego(source_obj, value, label):
    """
    updates the alter_ego field in every user collection
    in source_obj with value with label
    :param source_obj: DOM object for which data is updated
    :param value: id of user in another source
    :param label: name of the source
    :return:
    """
    if source_obj.alter_ego:
        # incase there is already an
        # existing alter_ego in another source
        so_existing_obj = source_obj.alter_ego
        so_existing_obj.update({label: f"{value}"})
        source_obj.update(alter_ego=so_existing_obj)
    else:
        source_obj.update(alter_ego={label: f"{value}"})


def service_create_candidate_rating(user_id, jd_name, rating):
    cd_rating_obj = CandidateRatings()
    cd_rating_obj.user_id = user_id
    cd_rating_obj.jd_name = jd_name
    cd_rating_obj.rating = rating
    cd_rating_obj.save()
