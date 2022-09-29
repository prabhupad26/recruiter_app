from recruiter_app.elt_app.collections.gh_users_details import GithubUser
from recruiter_app.elt_app.collections.so_users_details import StackOverflowUser
from recruiter_app.elt_app.collections.reddit_user_props import RedditUserProps
from recruiter_app.elt_app.service.mongo import service_update_alter_ego
from recruiter_app.utilities.helpers import mongo_global_init
from difflib import SequenceMatcher
from tqdm import tqdm


class MergeDataSources:
    def __init__(self, confidence=0.8):
        mongo_global_init(host_type='cloud')
        self.gh_users = GithubUser.objects()
        self.so_users = StackOverflowUser.objects()
        self.rd_users = RedditUserProps.objects()
        self.similarity_confidence = confidence

    def is_similar(self, name1, name2):
        s = SequenceMatcher(None, name1, name2)
        return s.ratio() > self.similarity_confidence

    def merge_data(self):
        """
        alter_ego field is updated if there is a match
        :return:
        """
        with tqdm(total=len(self.so_users)) as pbar:
            pbar.set_description("Processing stackoverflow")
            for so_user in self.so_users:
                if "github" not in so_user.alter_ego:
                    for gh_user in self.gh_users:
                        if self.is_similar(so_user.display_name.lower(),
                                           gh_user.name.lower()):
                            service_update_alter_ego(so_user, gh_user.name, "github")
                            service_update_alter_ego(gh_user, so_user.display_name, "stackoverflow")
                            # print(f"Match found {so_user.display_name.lower()} ** {gh_user.name.lower()}")
                            break
                # if "reddit" not in so_user.alter_ego:
                for rd_user in self.rd_users:
                    if self.is_similar(so_user.display_name.lower(),
                                       rd_user.user_name.lower()):
                        service_update_alter_ego(so_user, rd_user.user_name, "reddit")
                        service_update_alter_ego(rd_user, so_user.display_name, "stackoverflow")
                        # print(f"Match found {so_user.display_name.lower()} ** {rd_user.user_name.lower()}")
                        break
                pbar.update(1)
        with tqdm(total=len(self.gh_users)) as pbar:
            pbar.set_description("Processing github")
            for gh_user in self.gh_users:
                # if "reddit" not in gh_user.alter_ego:
                for rd_user in self.rd_users:
                    if self.is_similar(gh_user.name.lower(),
                                       rd_user.user_name.lower()):
                        service_update_alter_ego(gh_user, rd_user.user_name, "reddit")
                        service_update_alter_ego(rd_user, gh_user.name, "github")
                        # print(f"Match found {gh_user.name.lower()} ** {rd_user.user_name.lower()}")
                        break
                pbar.update(1)


if __name__ == '__main__':
    mds = MergeDataSources()
    mds.merge_data()
