from recruiter_app.utilities.helpers import *


class RatingRecipe:
    def __init__(self, skills_required, data_skills_obj,
                 so_extra_score, primary_data_source, gh_extra_score=None,
                 so_dampen_factor=0.25, gh_dampen_factor=0.25):
        self.skills_required = skills_required
        self.data_skills_obj = data_skills_obj
        self.so_extra_score = so_extra_score
        self.gh_extra_score = gh_extra_score
        self.primary_data_source = primary_data_source
        self.so_dampen_factor = so_dampen_factor
        self.gh_dampen_factor = gh_dampen_factor
        self.result_queue_params = []

    def get_dampening_weight(self, skill_obj):
        """
        Get the regularization params for every feature
        :param skill_obj:
        :return:
        """
        dampening_weights = {}
        if skill_obj:
            scores_dict = get_all_feature_scores(skill_obj)
            if scores_dict["so_q_score"] and scores_dict["so_a_score"] and \
               scores_dict["so_q_score"] > 0 and scores_dict["so_a_score"] > 0:
                if scores_dict["so_q_score"] > scores_dict["so_a_score"]:
                    dampening_weights['dampen_so_question'] = self.so_dampen_factor
                if scores_dict["so_top_q_score"] > scores_dict["so_top_a_score"]:
                    dampening_weights['dampen_so_question_top'] = self.so_dampen_factor
            if scores_dict["gh_watchers_count"] and scores_dict["gh_forks_count"] and scores_dict["gh_stars_count"]:
                if sum([scores_dict["gh_watchers_count"],
                        scores_dict["gh_forks_count"]]) > scores_dict["gh_stars_count"]:
                    dampening_weights['dampen_gh_features'] = self.gh_dampen_factor
        return dampening_weights

    def calculate_rating(self, result_queue):
        """
        Main function for calculating the final score of the candidate
        :param result_queue: the queue to which this function pushes:
         - candidate id
         - job title for which the rating has happened
         - final score
        :return:
        """
        final_rating = 0
        for skill, skill_weight in self.skills_required.items():
            candidate_skills_dict = self.data_skills_obj.get(skill)
            if not candidate_skills_dict:
                continue
            dampening_weights = self.get_dampening_weight(candidate_skills_dict)
            so_question_weight = 1
            so_question_top_weight = 1
            gh_features_weight = 1
            if dampening_weights:
                dampen_so_question = dampening_weights.get("dampen_so_question")
                dampen_so_question_top = dampening_weights.get("dampen_so_question_top")
                dampen_gh_features = dampening_weights.get("dampen_gh_features")
                so_question_weight = 1 if not dampen_so_question else dampen_so_question
                so_question_top_weight = 1 if not dampen_so_question_top else dampen_so_question_top
                gh_features_weight = 1 if not dampen_gh_features else dampen_gh_features
            ft_scores_dict = get_all_feature_scores(candidate_skills_dict)
            skill_rating = sum([ft_scores_dict["so_q_score"] * so_question_weight,
                                ft_scores_dict["so_a_score"],
                                ft_scores_dict["so_top_q_score"] * so_question_top_weight,
                                ft_scores_dict["so_top_a_score"],
                                ft_scores_dict["so_top_a_isa_score"],
                                ft_scores_dict["gh_forks_count"] * gh_features_weight,
                                ft_scores_dict["gh_stars_count"],
                                ft_scores_dict["gh_watchers_count"] * gh_features_weight,
                                ft_scores_dict["gh_repo_count"]])
            final_rating += skill_rating * skill_weight
        if final_rating > 0:
            final_rating += self.so_extra_score
            if self.gh_extra_score:
                final_rating += self.gh_extra_score
        self.result_queue_params.extend([final_rating])
        result_queue.put(self.result_queue_params)
