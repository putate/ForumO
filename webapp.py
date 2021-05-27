import json
import os
from flask import Flask, url_for, render_template, request, Markup, jsonify
from flask import redirect
from flask import session
from flask_oauthlib.client import OAuth
import pymongo
import sys
import pprint
from bson.objectid import ObjectId
os.environ['OAUTHLIB_INSECURE_TRANSPORT']='1'
# This code originally from https://github.com/lepture/flask-oauthlib/blob/master/example/github.py
# Edited by P. Conrad for SPIS 2016 to add getting Client Id and Secret from
# environment variables, so that this will work on Heroku.
# Edited by S. Adams for Designing Software for the Web to add comments and remove flash messaging

app = Flask(__name__)

app.debug = True #Change this to False for production
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)


#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary 
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/', methods=['GET','POST'])
def renderMain():
    connection_string = os.environ["MONGO_CONNECTION_STRING"]
    db_name = os.environ["MONGO_DBNAME"]
    
    client = pymongo.MongoClient(connection_string)
    db = client[db_name]
    collection = db['ForumPosts'] 
    posts = db.post1
    
    if 'user_data' in session:
        if 'newThread' in request.form:
            x=1
            for post in posts.find({"thread": request.form["newThread"]}):
               x = x - 1           
            if x == 1:
                post = {"thread": request.form["newThread"]}
                posts_id = posts.insert_one(post).inserted_id
    
    return render_template('h0me.html', optionD = get_optionz())
    
@app.route('/1', methods=['GET','POST'])
def renderMain1():
    connection_string = os.environ["MONGO_CONNECTION_STRING"]
    db_name = os.environ["MONGO_DBNAME"]
    
    client = pymongo.MongoClient(connection_string)
    db = client[db_name]
    collection = db['ForumPosts'] 
    posts = db.post
    
    if 'delete' in request.form: 
        id = ObjectId(request.form['delete'])
        posts.delete_one({'_id':id})

    print(request.form)
    if 'threads' in request.form:
        session["threads"] = request.form['threads']
    
    if 'user_data' in session:
        if 'firstQ' in request.form:
            if 'threads' in session:
                post = {"author": session['user_data']['login'], "message": request.form['firstQ'], "thread": session["threads"]}
                posts_id = posts.insert_one(post).inserted_id
    return render_template('home.html', postz = get_postz(session["threads"]), head = get_head(session["threads"]))    

def get_optionz():
    connection_string = os.environ["MONGO_CONNECTION_STRING"]
    db_name = os.environ["MONGO_DBNAME"]
    
    client = pymongo.MongoClient(connection_string)
    db = client[db_name]
    collection = db['ForumPosts']
    posts = db.post1
    
    options = ""
    for post in posts.find():
        options = options + Markup("<option value=\"" + post["thread"] + "\">" + post["thread"] + "</option>")
    return options 
    
def get_postz(x):
    connection_string = os.environ["MONGO_CONNECTION_STRING"]
    db_name = os.environ["MONGO_DBNAME"]
    
    client = pymongo.MongoClient(connection_string)
    db = client[db_name]
    collection = db['ForumPosts']
    posts = db.post
    
    options = ""
    for post in posts.find():
      if post["thread"] == x:
        if 'user_data' in session:
            if post["author"] == session['user_data']['login']:
                if str("@" + session['user_data']['login']) in post["message"]:
                    options = options + Markup("<p style=color:green>" + post["author"] + str(": ") + post["message"] + "</p>") + Markup('<form action="/1" method="post"> <button type="submit" name="delete" value="'+str(post["_id"])+'">Delete</button> </form>')
                else:
                    options = options + Markup("<p>" + post["author"] + str(": ") + post["message"] + "</p>") + Markup('<form action="/1" method="post"> <button type="submit" name="delete" value="'+str(post["_id"])+'">Delete</button> </form>')
            else:
                if str("@" + session['user_data']['login']) in post["message"]:
                    options = options + Markup("<p style=color:green>" + post["author"] + str(": ") + post["message"] + "</p>") 
                else:
                    options = options + Markup("<p>" + post["author"] + str(": ") + post["message"] + "</p>") 
        else:
            options = options + Markup("<p>" + post["author"] + str(": ") + post["message"] + "</p>")
    return options 
    
def get_head(x):
    return Markup("<h1>" + x + str(" thread") + "</h1>")

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    return render_template('message.html', message='You were logged out')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args)      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            #pprint.pprint(vars(github['/email']))
            #pprint.pprint(vars(github['api/2/accounts/profile/']))
            message='You were successfully logged in as ' + session['user_data']['login'] + '.'
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
    return render_template('message.html', message=message)

#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']


if __name__ == '__main__':
    app.run()
