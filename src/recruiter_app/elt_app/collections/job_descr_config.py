import mongoengine


class JobDescrConfig(mongoengine.Document):
    meta = {
        "db_alias": 'core',
        "collection": 'job_descr_config'
    }
    jd_name = mongoengine.StringField(required=True)
    skills_weightage = mongoengine.DictField()
