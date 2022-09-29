from flask import Flask, render_template, request
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

app = Flask(__name__, template_folder='templates')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'anamadheyaashoka003@gmail.com'
app.config['MAIL_PASSWORD'] = 'jrlcakojofqllwkz'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

s = URLSafeTimedSerializer('Thisisasecret!')

#Routes to the host and send e-mail
@app.route("/")
def index():
    send_mail()
    return '<h1>Email sent!!</h1>'

# create a secure token using salt and sample text.
# send email to all the selected candidates with the test link 
def send_mail():
    sample_token = "sample_token"
    token = s.dumps(sample_token, salt='test_sample_token')
    msg = Message('Interview-Software Engineer', sender='anamadheyaashoka003@gmail.com',
                  recipients=['anamadheyaashoka005@gmail.com', 'anamadheyaashoka003@gmail.com'])
    msg.html = f"""
    <html><body>
    <p>Dear Candidates,</p>
    <p>To continue your interview process, please click the below link and submit your answers with in next 2 days: </p>
    <p><a href=`http://127.0.0.1:5000/questions/{token}`>Exam link</a></p>
    <p>Thanks and Regards,</p>
    <p>HushHush Recruiter HR</p>
    """
    mail.send(msg)
    print("Message send successfully")

# Route to the home page with set of questions 
@app.route("/home", methods=["post", "get"])
def home():
    sample_token = "test_sample_token"
    token=s.dumps(sample_token, salt='test_sample_token')
    print(f"Generated token: {token}")
    # form will be visible only when visible is set to true 
    visible = True
    if request.method == 'POST':
        candidate_name = request.form['candidate_name']
        question1 = request.form['question1']
        question2 = request.form['question2']
        question3 = request.form['question3']

        print(
            f"Name: {candidate_name}\n Question answered:Q1 answered: {question1}\n Q2 answered: {question2}\n Q3 "
            f"answered: {question3}")
        if question1 is not None or question2 is not None or question3 is not None:
            visible = False
    return render_template("home.html", visible=visible)

# check the expiration of the link which is sent in e-mail
@app.route('/questions/<token>')
def confirm_email(token):
    try:
        #setting link expire time to 100 seconds
        s.loads(token, salt='test_sample_token', max_age=100)
        return render_template("home.html", visible=True)
    except SignatureExpired:
        # display when link is expired
        return '<h1>Link is expired!</h1>'


if __name__ == "__main__":
    app.run(debug=True)
