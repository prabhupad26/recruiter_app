import mongoengine


class CandidateRatings(mongoengine.Document):
    meta = {
        "db_alias": 'core',
        "collection": 'candidate_ratings'
    }
    jd_name = mongoengine.StringField(required=True)
    user_id = mongoengine.IntField(required=True)
    rating = mongoengine.FloatField(default=0.0)
