import codecs
import datetime
import json
import os
import random
import string
import sys

import httplib2
import requests
from flask import session as login_session
from flask import (Flask, flash, jsonify, make_response, redirect,
                   render_template, request, send_from_directory, url_for)
from oauth2client.client import FlowExchangeError, flow_from_clientsecrets
from sqlalchemy import asc, create_engine, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from werkzeug.utils import secure_filename

from models import Base, Chapter, Comment, File, Subject, Topic, User

sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)


UPLOAD_FOLDER = '/var/www/catalog/static/upload'


ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg',
                          'jpeg', 'gif', 'docx', 'pptx', 'doc', 'pptx', 'ppt'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = 'super_secret_key'

# connecting database
engine = create_engine('postgresql://octauser:dynamic*_*website@localhost/octa')  # noqa

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

APPLICATION_NAME = "End Prep"


# handler methods with route decorators
subjects = session.query(Subject).all()

# home page handler


@app.route('/')
@app.route('/home')
def homeHandler():
    users = session.query(User).all()
    users.sort(key=lambda x: x.rating, reverse=True)
    leaders = users[0:3]
    return render_template(
        'home.html', subjects=subjects,users=leaders)


# single article handler
@app.route('/<string:subject>/chapter')
def topics(subject):
    if 'username' not in login_session:
       return redirect(url_for('login'))
    tpc = session.query(Chapter).filter_by(subject_name=subject).all()
    return render_template('topics.html', subject=subject, tpc=tpc, subjects=subjects)


@app.route('/<string:subject>/<string:chapter>/topics')
def files(subject, chapter):
    if 'username' not in login_session:
        return redirect('login')
    chapter1 = session.query(Chapter).filter_by(title=chapter).one()
    docfiles = session.query(File).filter_by(chapter_id=chapter1.id).all()
    return render_template('doclist.html', subject=subject, chapter=chapter, docfiles=docfiles, subjects=subjects)

# LOGIN
@app.route('/login')
def login():
    if 'username' not in login_session:
        state = ''.join(
            random.choice(
                string.ascii_uppercase +
                string.digits) for x in range(32))
        login_session['state'] = state
        return render_template('login.html', STATE=state)
    else:
        flash("Already Logged In")
        return redirect(url_for('homeHandler'))


# User Helper Functions
# This method is to add a new user to the database
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# This method is to get the information of a registered user from the database
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# This method returns user_id
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# facebook oauth
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
   

    app_id = "1744882785574298"
    app_secret = "0961263c7e0499f6c77bdec5cbd2f50a"
    url = '''https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s''' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.11/me"
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.11/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.11/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['user_id']
    del login_session['facebook_id']
    return "You have been logged out"


# logging out handler
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        elif login_session['provider'] == 'facebook':
            fbdisconnect()
        del login_session['provider']
        flash("You have successfully been logged out.")
    else:
        flash("You were not logged in.")
    return redirect(url_for('homeHandler'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/download/<string:filename>')
def uploaded_file(filename):
    if 'username' not in login_session:
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/accessfile/<string:filename>', methods=['GET', 'POST'])
def access_file(filename):
    if 'username' not in login_session:
        return redirect(url_for('login'))
    fdata = session.query(File).filter_by(name=filename).one()
    if request.method == 'POST':
        text = request.form['comment']
        commentData = Comment(data=text, time=str(
            datetime.datetime.now()), user_id=login_session['user_id'], file_id=fdata.id)
        session.add(commentData)
        session.commit()
        return redirect(url_for('access_file', filename=filename))
    else:
        topics = session.query(Topic).filter_by(file_id=fdata.id).all()
        comments = session.query(Comment, User).filter(
            Comment.user_id == User.id).filter_by(file_id=fdata.id).all()
        return render_template('file.html', subjects=subjects, topics=topics, filename=filename, fdata=fdata, comments=comments)


@app.route('/<string:subject>/upload', methods=['GET', 'POST'])
def upload(subject):
    if 'username' not in login_session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files.getlist('file')
        # if user does not select file, browser also
        # submit a empty part without filename
        for f in file:
            if allowed_file(f.filename):
                chapterName = request.form['chapter']
                name = request.form['filename']
                keywords = request.form['keywords']
                chp = session.query(Chapter).filter_by(title=chapterName).one()
                f.filename = secure_filename(f.filename)
                keyArr = keywords.split(',')
                fn = File(name=name,
                          file_name=f.filename,
                          time=str(datetime.datetime.now()),
                          user_id=login_session['user_id'],
                          chapter_id=chp.id,
                          )
                session.add(fn)
                session.commit()
                session.refresh(fn)
                for i in keyArr:
                    key = Topic(title=i, file_id=fn.id)
                    print fn.id
                    session.add(key)
                    session.commit()
                #f.save(os.path.join(app.root_path,'/static/upload', f.filename))
		f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
                flash(f.filename + " file uploaded")
            else:
                flash(f.filename + " file not uploaded")
        flash("File(s) uploaded")
        return redirect(request.url)
    chapters = session.query(Chapter).filter_by(subject_name=subject).all()
    return render_template('upload.html', chapters=chapters, subjects=subjects, subject=subject)


@app.route('/map')
def map():
    return render_template('map.html', subjects=subjects)


@app.route('/search')
def search():
    searchT = request.args['search']
    file = session.query(Topic, File).filter(
        Topic.file_id == File.id).filter_by(title=searchT).all()
    return render_template('search.html', subjects=subjects, file=file, searchT=searchT)


@app.route('/deletecomment/<int:id>', methods=['GET', 'POST'])
def deleteComment(id):
    comment = session.query(Comment).filter_by(id=id).one()
    if comment.user_id != login_session['user_id']:
        return '''<script>function myFunction() 
            {alert('You are not authorized to delete this comment');}
            </script><body onload='myFunction()'>'''
    else:
        file = session.query(File).filter_by(id=comment.file_id).one()
        session.delete(comment)
        session.commit()
        return redirect(url_for('access_file', filename=file.name))

@app.route('/<string:filename>/like', methods=['PUT','DELETE'])
def like(filename):
    file = session.query(File).filter_by(name=filename).one()
    owner = session.query(User).filter_by(id=file.user_id).one()
    if request.method == 'DELETE':
        file.rating -= 1
        owner.rating -= 1
    elif request.method == 'PUT':
        file.rating += 1
        owner.rating += 1
    session.add(file)
    session.add(owner)
    session.commit()
    session.refresh(file)
    return '%s'%file.rating


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    # app.run(host='0.0.0.0', port=80)
    app.run(host='0.0.0.0', port=5000)
