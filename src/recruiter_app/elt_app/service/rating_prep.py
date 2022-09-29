from recruiter_app.elt_app.collections.job_descr_config import JobDescrConfig
from recruiter_app.elt_app.collections.so_users_details import StackOverflowUser
from recruiter_app.elt_app.collections.gh_users_details import GithubUser
from recruiter_app.elt_app.service.rating_recipes import RatingRecipe
from recruiter_app.elt_app.service.exec_recipe import ExecuteRecipe

from recruiter_app.utilities.helpers import *
import pandas as pd
import os


class RatingEngine:
    """
    RatingEngine creates the skill dict which contains all the values required for
    preparing a recipe
    """
    def __init__(self, jd_name):
        mongo_global_init(host_type='cloud')
        self.jd_name = jd_name
        self.so_skill_tag_map = get_skill_tag_map(pd.read_csv("config/so_skills_count.csv"))
        self.gh_skill_tag_map = get_skill_tag_map(pd.read_csv("config/gh_skills_count.csv"))
        self.so_user_list = StackOverflowUser.objects()
        self.gh_user_list = GithubUser.objects()
        self.skills_required_obj = JobDescrConfig.objects(jd_name=self.jd_name)[0]
        self.norm_params = self.get_normalization_params()
        self.so_data = StackOverflowUser.objects(tags_data_available=True,
                                                 tags_top_qna_data_available=True)

    def get_normalization_params(self):
        """
        Get normalization parameters from collection
        :return:
        """
        norm_params_dict = {
            "max_gold_badge_count": self.so_user_list.order_by('-gold_badge_count').limit(1)[0].gold_badge_count,
            "min_gold_badge_count": self.so_user_list.order_by('gold_badge_count').limit(1)[0].gold_badge_count,
            "max_silver_badge_count": self.so_user_list.order_by('-silver_badge_count').limit(1)[
                0].silver_badge_count,
            "min_silver_badge_count": self.so_user_list.order_by('silver_badge_count').limit(1)[
                0].silver_badge_count,
            "max_bronze_badge_count": self.so_user_list.order_by('-bronze_badge_count').limit(1)[
                0].bronze_badge_count,
            "min_bronze_badge_count": self.so_user_list.order_by('bronze_badge_count').limit(1)[
                0].bronze_badge_count,
            "max_accept_rate": self.so_user_list.order_by('-accept_rate').limit(1)[0].accept_rate,
            "min_accept_rate": self.so_user_list.order_by('accept_rate').limit(1)[0].accept_rate,
            "max_reputation": self.so_user_list.order_by('-reputation').limit(1)[0].reputation,
            "min_reputation": self.so_user_list.order_by('reputation').limit(1)[0].reputation,
            "max_followers": self.gh_user_list.order_by('-followers').limit(1)[0].followers,
            "min_followers": self.gh_user_list.order_by('followers').limit(1)[0].followers,
            "max_public_repos": self.gh_user_list.order_by('-public_repos').limit(1)[0].public_repos,
            "min_public_repos": self.gh_user_list.order_by('public_repos').limit(1)[0].public_repos,
            "max_public_gists": self.gh_user_list.order_by('-public_gists').limit(1)[0].public_gists,
            "min_public_gists": self.gh_user_list.order_by('public_gists').limit(1)[0].public_gists}

        return norm_params_dict

    def get_normalised_score(self, score, score_label):
        """
        Calculate normalized score
        :param score: original score
        :param score_label: type of score
        :return:
        """
        norm_params = self.norm_params
        if score_label == "gold_badge":
            max_gold_badge_count = norm_params["max_gold_badge_count"]
            min_gold_badge_count = norm_params["min_gold_badge_count"]
            score = (score - min_gold_badge_count) / (max_gold_badge_count - min_gold_badge_count)
        elif score_label == "silver_badge":
            max_silver_badge_count = norm_params["max_silver_badge_count"]
            min_silver_badge_count = norm_params["min_silver_badge_count"]
            score = (score - min_silver_badge_count) / (max_silver_badge_count - min_silver_badge_count)
        elif score_label == "bronze_badge":
            max_bronze_badge_count = norm_params["max_bronze_badge_count"]
            min_bronze_badge_count = norm_params["min_bronze_badge_count"]
            score = (score - min_bronze_badge_count) / (max_bronze_badge_count - min_bronze_badge_count)
        elif score_label == "reputation":
            max_reputation = norm_params["max_reputation"]
            min_reputation = norm_params["min_reputation"]
            score = (score - min_reputation) / (max_reputation - min_reputation)
        elif score_label == "accept_rate":
            max_accept_rate = norm_params["max_accept_rate"]
            min_accept_rate = norm_params["min_accept_rate"]
            score = (score - min_accept_rate) / (max_accept_rate - min_accept_rate)
        elif score_label == "gh_followers":
            max_followers = norm_params["max_followers"]
            min_followers = norm_params["min_followers"]
            score = (score - min_followers) / (max_followers - min_followers)
        elif score_label == "gh_pub_repos":
            max_public_repos = norm_params["max_public_repos"]
            min_public_repos = norm_params["min_public_repos"]
            score = (score - min_public_repos) / (max_public_repos - min_public_repos)
        elif score_label == "gh_pub_gists":
            max_public_gists = norm_params["max_public_gists"]
            min_public_gists = norm_params["min_public_gists"]
            score = (score - min_public_gists) / (max_public_gists - min_public_gists)
        return score

    def get_additional_score(self, data_obj, data_source):
        """
        Calculates the normalized additional score
        :param data_obj:
        :param data_source:
        :return:
        """
        data_additional_score = 0
        weights = get_ad_score_weights(data_obj, data_source)
        # if all additional features are present then weights is 1
        weight = 1 / weights if weights else 1

        if data_source == "stackoverflow":
            if data_obj.gold_badge_count:
                data_additional_score += self.get_normalised_score(data_obj.gold_badge_count,
                                                                   "gold_badge") * weight
            if data_obj.silver_badge_count:
                data_additional_score += self.get_normalised_score(data_obj.silver_badge_count,
                                                                   "silver_badge") * weight
            if data_obj.bronze_badge_count:
                data_additional_score += self.get_normalised_score(data_obj.bronze_badge_count,
                                                                   "bronze_badge") * weight
            if data_obj.reputation:
                data_additional_score += self.get_normalised_score(data_obj.reputation,
                                                                   "reputation") * weight
            if data_obj.accept_rate:
                data_additional_score += self.get_normalised_score(data_obj.accept_rate,
                                                                   "accept_rate") * weight
        elif data_source == "github":
            if data_obj.followers:
                data_additional_score += self.get_normalised_score(data_obj.followers,
                                                                   "gh_followers") * weight
            if data_obj.public_repos:
                data_additional_score += self.get_normalised_score(data_obj.public_repos,
                                                                   "gh_pub_repos") * weight
            if data_obj.public_gists:
                data_additional_score += self.get_normalised_score(data_obj.public_gists,
                                                                   "gh_pub_gists") * weight
        else:
            raise NotImplementedError("Reddit not implemented yet")
        return data_additional_score

    def create_gh_skill_obj(self, lang_score_obj, so_skill_obj, repo_cnt=5):
        for lang in lang_score_obj:
            if lang_score_obj.get(lang):
                lang_scores = lang_score_obj.get(lang)
                lang_name = get_base_label(lang.split("_")[1], self.gh_skill_tag_map)
                if lang_name not in so_skill_obj:
                    so_skill_obj[lang_name] = load_base_scores()
                lang_scores_keys = lang_scores.keys()
                lang_fork_keys = list(filter(lambda x: re.search("^repo_.*_forks", x), lang_scores_keys))
                lang_fork_keys = sort_by_scores(lang_fork_keys, lang_scores)
                lang_stars_keys = list(filter(lambda x: re.search("^repo_.*_stars", x), lang_scores_keys))
                lang_stars_keys = sort_by_scores(lang_stars_keys, lang_scores)
                lang_watchers_keys = list(filter(lambda x: re.search("^repo_.*_watchers", x), lang_scores_keys))
                lang_watchers_keys = sort_by_scores(lang_watchers_keys, lang_scores)
                so_skill_obj[lang_name]["feature_forks"] += get_scores_dict(lang_fork_keys,
                                                                            lang_scores)
                so_skill_obj[lang_name]["feature_stars"] += get_scores_dict(lang_stars_keys,
                                                                            lang_scores)
                so_skill_obj[lang_name]["feature_watchers"] += get_scores_dict(lang_watchers_keys,
                                                                               lang_scores)
                so_skill_obj[lang_name]["feature_repo_count"] += len(lang_fork_keys)
        return so_skill_obj

    def create_so_skill_obj(self, tags_score_obj, topqna_cnt=5):
        """
        Similar tags are aggregated
        :param tags_score_obj:
        :param topqna_cnt:
        :return:
        """
        so_skill_obj = {}
        for tag in tags_score_obj:
            if tags_score_obj.get(tag):
                tag_obj = tags_score_obj.get(tag)
                name = get_base_label(tag_obj.get('name'), self.so_skill_tag_map)
                if name not in so_skill_obj:
                    so_skill_obj[name] = load_base_scores()
                if tag_obj.get("question_score"):
                    so_skill_obj[name]["feature_question_score"] += tag_obj.get("question_score")
                if tag_obj.get("answer_score"):
                    so_skill_obj[name]["feature_answer_score"] += tag_obj.get("answer_score")
                top_qna_keys = tag_obj.keys()
                top_q_keys = list(filter(lambda x: re.search("^top_question_.*_score", x),
                                         top_qna_keys))
                top_a_keys = list(filter(lambda x: re.search("^top_answer_.*_score", x),
                                         top_qna_keys))
                top_a_isa_keys = list(filter(lambda x: re.search("^top_answer_.*_is_accepted", x),
                                             top_qna_keys))
                top_q_keys = sort_by_id(top_q_keys)[:topqna_cnt]
                top_a_keys = sort_by_id(top_a_keys)[:topqna_cnt]
                top_a_isa_keys = sort_by_id(top_a_isa_keys)[:topqna_cnt]
                so_skill_obj[name]['feature_top_question'] += get_scores_dict(top_q_keys,
                                                                              tag_obj)
                so_skill_obj[name]['feature_top_answer'] += get_scores_dict(top_a_keys,
                                                                            tag_obj)
                so_skill_obj[name]['feature_top_a_accepted'] += get_scores_dict(top_a_isa_keys,
                                                                                tag_obj)
        return so_skill_obj

    def start(self):
        """
        Process the stackoverflow data in batches
        :return:
        """
        for so_data_batch in create_batch(self.so_data,
                                          description="\nProcessing Main Batch {0}"):
            recipes_list = []
            for so_data in so_data_batch:
                so_extra_score = self.get_additional_score(so_data,
                                                           data_source="stackoverflow")
                gh_extra_score = None
                if so_data.tags_score:
                    skill_obj = self.create_so_skill_obj(so_data.tags_score)
                    if so_data.alter_ego and so_data.alter_ego.get("github"):
                        # TODO : [Placeholder] for reddit additional score
                        gh_user = so_data.alter_ego.get("github")
                        gh_user_obj = GithubUser.objects(name=gh_user)[0]
                        gh_extra_score = self.get_additional_score(gh_user_obj,
                                                                   data_source="github")
                        skill_obj = self.create_gh_skill_obj(gh_user_obj.lang_score,
                                                             skill_obj)
                    rating_recipe = RatingRecipe(self.skills_required_obj.skills_weightage,
                                                 skill_obj,
                                                 so_extra_score,
                                                 primary_data_source="stackoverflow",
                                                 gh_extra_score=gh_extra_score)
                    rating_recipe.result_queue_params.extend([so_data.user_id,
                                                              self.jd_name])
                    recipes_list.append((so_data.user_id,
                                         self.jd_name,
                                         rating_recipe))
            exec_recipe = ExecuteRecipe()
            exec_recipe.start_processes(recipes_list)


if __name__ == '__main__':
    jd_list = ["python developer", "data scientist", "web developer", "devops engineer"]
    for jd in jd_list:
        print(f"rating for job description : {jd}")
        re_obj = RatingEngine(jd)
        re_obj.start()
        print(f"finished rating for jd : {jd}")
