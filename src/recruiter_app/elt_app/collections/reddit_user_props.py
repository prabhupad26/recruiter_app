import mongoengine


class RedditUserProps(mongoengine.Document):
    meta = {
        "db_alias": 'core',
        "collection": 'reddit_user_props'
    }
    user_name = mongoengine.StringField(required=True, unique=True)
    for_jd = mongoengine.StringField(required=True)
    thread_props = mongoengine.DictField()
    alter_ego = mongoengine.DictField()
