#import necessary libraries for flask
from flask import Flask, redirect, url_for, render_template, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy



#import necessary libraries to connect with keycloak
from flask_oidc import OpenIDConnect
from keycloak.keycloak_openid import KeycloakOpenID
#other needed libraries
import json

from decouple import config
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)


app.config.update({
    'SECRET_KEY': 'supercalifragilisticexpialidocious',
    'TESTING': True,
    'DEBUG': True,
    'OIDC_CLIENT_SECRETS': 'client_secrets.json',
    'OIDC_COOKIE_SECURE': False,
    'OIDC_REQUIRE_VERIFIED_EMAIL': False,
    'OIDC_USER_INFO_ENABLED': True,
    'OIDC_OPENID_REALM': 'testing',
    'OIDC_TOKEN_TYPE_HINT' : 'access_token',
    'OIDC_INTROSPECTION_AUTH_METHOD': 'client_secret_post'
})

oidc = OpenIDConnect(app)
keycloak_openid = KeycloakOpenID(server_url=config('SERVER_URL'),
                                client_id="flask-app",
                                realm_name="testing",
                                client_secret_key=config("KEYCLOAK_SECRET"))

app.config ['SQLALCHEMY_DATABASE_URI'] = config('DB_URI')

app.config ["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = config('SECRET_KEY')
#image
app.config ['IMAGE_UPLOADS'] = 'static/uploads'
app.config ['ALLOWED_IMAGE_EXTENSIONS'] = ['JPEG', 'PNG', 'JPG']

def allowed_image(filename):
    if not '.' in filename:
        return False
    ext = filename.rsplit('.', 1)[1]    

    if ext.upper() in app.config ['ALLOWED_IMAGE_EXTENSIONS']:
        return True


db = SQLAlchemy(app)



class Todo(db.Model):
    No = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String, nullable=True)
    Desc = db.Column(db.String, nullable=True)
    Time = db.Column(db.String, nullable=False)
    Status = db.Column(db.Boolean, default=False)
    Image = db.Column(db.String, nullable=True)
    User_email = db.Column(db.String, nullable=False)

    def __init__(self, Title, Desc, Time, Status, Image, User_email):
        
        self.Title = Title
        self.Desc = Desc
        self.Time = Time
        self.Image = Image
        self.Status = Status
        self.User_email = User_email

#using a db to check a user has pro Prodb
class Prodb(db.Model):
    No = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String, nullable=False)
    Pro = db.Column(db.Boolean, default=False)
    
    def __init__(self, Email, Pro):
        self.Email = Email
        self.Pro = Pro

#token = keycloak_openid.token("debxd", "debxd")
@app.route('/', methods=['POST', 'GET'])
@oidc.require_login
def home():
    return redirect('/todo/')

@app.route('/login/', methods=['POST', 'GET'])
@oidc.require_login
def login():
    return redirect('/todo/')

@app.route('/todo/', methods=['POST', 'GET'])
@oidc.require_login
def index():
    email = oidc.user_getfield('email')
    #add user entry

    pro = False
    user_obj = Prodb(email, pro)
        
    db.session.add(user_obj)

    db.session.commit()


    if request.method == "POST":
        if 'todostatus' in request.form:
            status = request.form.get('status')
            todo_no = request.form.get('todo_no')
            todo_obj = Todo.query.filter_by(No=todo_no, User_email=email ).first()
            if status != todo_obj.Status :
                if status == 'on':
                    todo_obj.Status = True
                    db.session.commit()
                    
                    return redirect('/todo/')

                else:
                    todo_obj.Status = False
                    db.session.commit()
                    
                    return redirect('/todo/')
            
        else:

            title = request.form.get('title')
            desc = request.form.get('desc')
            time = request.form.get('time')
            has_pro = Prodb.query.filter_by(Email=email).first().Pro
            if request.files is not None and has_pro is True:
                image = request.files.get('image')
                print(image)

                    

                if  image.filename == "" or  image.filename is None:
                    image.filename = 'default.jpg'
                

                if not allowed_image(image.filename):
                    flash("This file type isn't allowed!")
                    return redirect("/")
                
                image_filename = secure_filename(image.filename)

                image.save(os.path.join(app.config ['IMAGE_UPLOADS'], image_filename))
                
                status = False
                email = oidc.user_getfield('email')
                full_todo = Todo(title,desc,time,status,image_filename, email)
                db.session.add(full_todo)
                db.session.commit()
                flash("TODO ADDED!", category="success")
                return redirect("/todo/")
            else:
                status = False
                image_filename = 'default.jpg'
                email = oidc.user_getfield('email')
                full_todo = Todo(title,desc,time,status,image_filename, email)
                db.session.add(full_todo)
                db.session.commit()
                flash("TODO ADDED!", category="success")
                return redirect("/todo/")
                
    else:
         

        todo_list = Todo.query.filter_by(User_email = email).order_by(Todo.Time)
        todo_count = todo_list.count()
        has_pro = Prodb.query.filter_by(Email=email).first().Pro
        return render_template('index.html', email=email, todo_list=todo_list, todo_count=todo_count, has_pro=has_pro)

@app.route('/display/<filename>/')
@oidc.require_login
def display_image(filename):
    return redirect(url_for ('static', filename='uploads/'+filename), code=301)

@app.route('/todo/update/<int:todo_no>/', methods=['POST', 'GET'])
@oidc.require_login
def update(todo_no):
    email = oidc.user_getfield('email')
    todo_obj = Todo.query.filter_by(No=todo_no, User_email=email ).first()
    if request.method == "POST":
        title = request.form.get('Title')
        desc = request.form.get('Desc')
        time = request.form.get('Time')
        has_pro = Prodb.query.filter_by(Email=email).first().Pro
        if request.files is not None and has_pro is True:
            image = request.files.get('image')
            old_img = todo_obj.Image
            if os.path.exists(f'static/uploads/{old_img}'):
                os.remove(f'static/uploads/{old_img}')
                
            if image.filename == "" and not None:
                image.filename = 'default.jpg'
                

            if not allowed_image(image.filename):
                flash("This file type isn't allowed!")
                return redirect("/")
                
            image_filename = secure_filename(image.filename)

            image.save(os.path.join(app.config ['IMAGE_UPLOADS'], image_filename))

            todo_obj.Title = title
            todo_obj.Desc = desc
            todo_obj.Time = time
            todo_obj.Image = image_filename
            db.session.commit()
            flash("TODO UPDATED!", category="success")
            return redirect("/todo/")
        else:

            todo_obj.Title = title
            todo_obj.Desc = desc
            todo_obj.Time = time
            db.session.commit()
            flash("TODO UPDATED!", category="success")
            return redirect("/todo/")


    has_pro = Prodb.query.filter_by(Email=email).first().Pro
    return render_template('update.html', Title=todo_obj.Title, Desc=todo_obj.Desc, Time = todo_obj.Time, Image = todo_obj.Image, has_pro=has_pro)

@app.route("/todo/delete/<int:todo_no>/", methods=["POST", "GET"])
@oidc.require_login
def tododel(todo_no):
    todo_obj = Todo.query.filter_by(No=todo_no).first()
    img = todo_obj.Image
    if os.path.exists(f'static/uploads/{img}'):
        os.remove(f'static/uploads/{img}')
    Todo.query.filter_by(No=todo_no).delete()
    db.session.commit()
    flash("TODO DELETED!", category="error")
    return redirect("/todo/")


@app.route('/logout/')
@oidc.require_login
def logout():
    log_out_url = config('LOGOUT_URL')
    oidc.logout()
    return redirect(log_out_url)


import stripe


stripe.api_key = config('STRIPE_KEY')
my_domain = config('MY_DOMAIN')
@app.route('/create-checkout-session/', methods=['POST','GET'])
@oidc.require_login
def create_checkout_session():
    if request.method == 'POST':
        try:
            session = stripe.checkout.Session.create(
            
                line_items=[
                    {
                    'price' : config('PRODUCT_PRICE_TOKEN'),
                    'quantity' : 1


                    }
                ],
                mode='payment',
                success_url= f'{my_domain}/success/',
                cancel_url=f'{my_domain}/cancel/',  
            )
            
     
            if True:
                email = oidc.user_getfield('email')
                user_obj = Prodb.query.filter_by(Email=email).first()
                user_obj.Pro = True
                db.session.commit()
        except Exception as  e:
            print(e)
            flash('Something goes wrong with payment')
            return redirect('/todo/')

        return redirect(session.url, code=303)
    else:
        return render_template('checkout.html')

@app.route('/success/')
@oidc.require_login
def success():
    return render_template('success.html')


@app.route('/cancel/')
@oidc.require_login
def cancel():
    return render_template('cancel.html')


# You can find your endpoint's secret in your webhook settings
endpoint_secret = config('STRIPE_ENDPOINT_SECRET')
@app.route('/webhook/', methods=['POST'])
def webhook():
    event = None
    payload = request.data

    try:
        event = json.loads(payload)
    except:
        print('⚠️  Webhook error while parsing basic request.' + str(e))
        return jsonify(success=False)
    if endpoint_secret:

        sig_header = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except stripe.error.SignatureVerificationError as e:
            print('⚠️  Webhook signature verification failed.' + str(e))
            return jsonify(success=False)
            

    # Handle the event
    if event and event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object'] 
        print('Payment for {} succeeded'.format(payment_intent['amount']))

    elif event['type'] == 'payment_method.attached':
        payment_method = event['data']['object'] 

    else:
        # Unexpected event type
        print('Unhandled event type {}'.format(event['type']))

    
    return jsonify(success=True)

@app.route('/about/')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    db.create_all()
    app.run()