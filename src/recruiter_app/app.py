import sys
import asyncio
import requests
from recruiter_app.elt_app import *
from recruiter_app.utilities import *


def start(mode):
    """
    Main function which is called for executing the recruiter_app
    :param mode: parameter which will decide the mode of execution
    possible values are -
    extract_stackoverflow,
    extract_github,
    extract_reddit,
    merge_data,
    rating_prep,
    rate_candidate,
    get_top_n_candidates
    :return:
    """
    if mode == "extract_stackoverflow":
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("Starting Stackoverflow factory")
        so_factory = SOFactory('cloud')
        so_factory.create_user_collection()
        print("Stackoverflow data extracted successfully")

    elif mode == "extract_github":
        print("Starting Github factory")
        gh_factory = GHFactory('cloud')
        jds = ['web developer', 'python developer', 'data scientist',
               "full stack developer", "devops engineer"]
        for jd in jds:
            print(f"Now mining for jd - {jd}")
            gh_factory.build_users_collection(jd)
            print(f"Mining target achieved for {jd}, moving to next jd")
        print("Github data extracted successfully")

    elif mode == "extract_reddit":
        print("Starting Reddit factory")
        all_jds = ["web_dev_thread", "devops_thread",
                   "cyber_seq_thread", "ml_thread", "py_thread"]
        rf = RedditFactory('cloud')
        rf.build_users_collection(all_jds)
        print("Reddit data extracted successfully")

    elif mode == "merge_data":
        print("Starting to merge data from different sources")
        mds = MergeDataSources()
        mds.merge_data()
        print("Successfully completed merge data")

    elif mode == "rating_prep":
        print("Creating csv file for labelling the tags/langs")
        so_user_list = StackOverflowUser.objects()
        gh_user_list = GithubUser.objects()
        run_prep_skill_count_csv(so_user_list, gh_user_list)
        print("Successfully completed rating_prep")

    elif mode == "rate_candidate":
        jd_list = ["python developer", "data scientist", "web developer", "devops engineer"]
        for jd in jd_list:
            print(f"rating for job description : {jd}")
            re_obj = RatingEngine(jd)
            re_obj.start()
            print(f"finished rating for jd : {jd}")

    elif mode == "get_top_n_candidates":
        mongo_global_init(host_type="cloud")
        n = int(os.environ["top_n"])
        jd_list = ["python developer", "data scientist", "web developer", "devops engineer"]
        for jd in jd_list:
            print(f"for jd : {jd}")
            top_candidates = CandidateRatings.objects(jd_name=jd).order_by('-rating').limit(n)
            for candidate in top_candidates:
                print(f"Sending mail to {candidate.user_id}with rating f{candidate.rating}")
                mail_data_payload = {"candidate_id": str(candidate.user_id),
                                     "jd_name": jd}
                req = requests.post("http://127.0.0.1:5000/notify_candidates",
                                    json=mail_data_payload)
                print(f"request sent status is : {req.status_code}")

    else:
        raise Exception(f"mode {mode} is not recognized, please enter any of: "
                        f"stackoverflow, github, redit")


if __name__ == '__main__':
    print("Welcome to hush hush recruiter cmd line tool")
    if len(sys.argv) < 2:
        raise Exception("Enter the mode of execution")
    mode = sys.argv[1]
    print(f"Tool will run in {mode} mode")
    start(mode)
    print("Execution completed successfully")
