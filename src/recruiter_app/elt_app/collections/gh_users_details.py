import mongoengine


class GithubUser(mongoengine.Document):
    meta = {
        "db_alias": 'core',
        "collection": 'gh_users_details'
    }
    login_name = mongoengine.StringField(required=True, unique=True)
    name = mongoengine.StringField()
    email = mongoengine.StringField(default=None)
    bio = mongoengine.StringField(default=None)
    followers = mongoengine.IntField(default=0)
    public_repos = mongoengine.IntField(default=0)
    public_gists = mongoengine.IntField(default=0)
    for_jd = mongoengine.StringField(required=True)
    lang_score = mongoengine.DictField()
    alter_ego = mongoengine.DictField()