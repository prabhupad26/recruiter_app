# PROJECT HUSH RECRUITER


* linkedIn api response structure:

`a = [{'entityUrn': '',
      'profile': {
                          'summary': '',
                          'industryName': '',
                          'currentLocation': '',
                          'student': None,
                          'headline': ''
      },
      'education': [
                          {'schoolName': '',
                           'startDate_month': None, 'startDate_year': None,
                           'endDate_month': None, 'endDate_year': None},
                          {'schoolName': '', 'startDate_month': None,
                           'startDate_year': None, 'endDate_month': None, 'endDate_year': None}
      ],
      'projectView': [
                          {
                              'title': '',
                              'description': '',
                              'url': None},
                          {
                              'title': '',
                              'description': '',
                              'url': None},
                          {
                              'title': '',
                              'description': '',
                              'url': None}
                    ],
      'skillView': [
                    {'name': 'Python (Programming Language)'}
                    ]}
     ]
`
### Guidelines for data extraction
1. Select what all fields you are capturing.
2. Try to convert all these fields into numeric data (think of scoring these fields on a scale of 0-10)
3. A rule can be defined to calculate the scores of every field
4. Naming conventions :
    - all field name should be lowercase , ' ' is separated by '_'
    - If you can produce multiple subfields from a single field then follow naming convention -> <field_name>_<subfield_name>

* PSUEDO code for extracting data from public apis:
  * LinkedIn:
  viewProfile API
  Field - email (apply regex in summary)
  Field - Firstname
  Field - Lastname
  Field - text_data_headline
  Field - text_data_summary
  Field - text_data_work_descriptions - fetch latest description
  Field - numeric_data_work_experience *(only job role):
    rule_1 : extract the job role, then score +=add(match(job role, input job role) -> percent, years of experience )
  skillCategory API
  Field - numeric_data_skills: 
             skillCategory API - elements/[list of skill categories/endorsedSkills/[list of skills]/skill.name, endorsementCount, if insights then insights.insightText.text]
    rule_1 : skill_system_design has value 5 by default , 
    rule_2 : if this skill is endorsed then +1 , 
    rule_3 : if skill has linkedin skill assessment then +2
  posts api
  Field - text_data_posts (top 5)
  Field - numeric_data_posts:
    logic :  to filter relevant posts
    rule_1: fetch likes count for the relevant posts
  certifications api
  Field - numeric_data_certification:
  if timePeriod then if isIfRecent(months=3) then consider for scoring
  **optional -- check if the account activity isRecent
  StackOverflow:
  scores per tags
  badges per tags
  Number of answers
  reputation
  number of upvotes in each answer in top post

  * Github:
    * of stars in each repo
    * of contibutions
    * of forks
    * achievements(badges)

### Algorithm :
score_solution_architect = `field_1 * weight_field_1 + .... + field_n * weight_field_n`
`weight_field_*` will be defined manually, its not necessary that all fields have to be defined in case a field is not defined then it will be 0

### Algorithm for merging the data from different source :
* check if reference of the other source is defined in a source
* based on first name and last name (calculate similarity % between first name and last name)


### Python packaging
* `python -m build` in root directory
* `twine upload dist/*` in root directory

### Docker commands used:
* `docker build -t hushrecruiterimage .`
* `docker run --env-file ./env_variables.list hushrecruiterimage` make sure to fill the access token details in the .list file
* Tagging the image :  `docker tag hushrecruiterimage prabhupad26/big-data-prog-sol:hushrecruiterimage`
* Pushing the tagged image : `docker push prabhupad26/big-data-prog-sol:hushrecruiterimage`

### Sending test link to the selected candidates via e-mail
Once candidates are selected through an algorithm, selected candidates receive a test link via mail. The test link contains 3 coding questions which need to be submitted within a specified time, otherwise the link will expire.

