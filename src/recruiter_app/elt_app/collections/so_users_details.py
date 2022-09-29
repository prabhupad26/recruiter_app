import mongoengine


class StackOverflowUser(mongoengine.Document):
    meta = {
        "db_alias": 'core',
        "collection": 'so_users_details'
    }
    display_name = mongoengine.StringField(required=True)
    user_id = mongoengine.IntField(required=True, unique=True)
    gold_badge_count = mongoengine.IntField(default=0)
    silver_badge_count = mongoengine.IntField(default=0)
    bronze_badge_count = mongoengine.IntField(default=0)
    accept_rate = mongoengine.IntField(default=0)
    reputation = mongoengine.IntField(default=0)
    website_url = mongoengine.StringField()
    tags_data_available = mongoengine.BooleanField(default=False)
    tags_top_qna_data_available = mongoengine.BooleanField(default=False)
    tags_score = mongoengine.DictField()
    alter_ego = mongoengine.DictField()