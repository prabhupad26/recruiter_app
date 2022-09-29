import mongoengine


class EvalCandidates(mongoengine.Document):
    meta = {
        "db_alias": 'core',
        "collection": 'evaluate_candidates'
    }
    candidate_id = mongoengine.IntField(required=True)
    jd_name = mongoengine.StringField(required=True)
    token = mongoengine.StringField(required=True)
    answer_1 = mongoengine.StringField()
    answer_2 = mongoengine.StringField()
    answer_3 = mongoengine.StringField()
