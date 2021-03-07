import os

from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

from trackma.accounts import AccountManager
from trackma import utils
from envparse import env

app = Flask(__name__)
app.config['SECRET_KEY'] = '&e6F6jf#Bnr8QEVVwPuB*8HssHteHbxaK#M7ziVzvM*eSBDNfN3@498R@CSs5bapgvzuy9ruUq&$#z*Agydgd8ivUAyeg&^MBK9nW5vkT6g$bu4BG*8DaW%NYCyiXmcs'
Bootstrap(app)

class NameForm(FlaskForm):
    oauth_key = StringField('OAUTH Key', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    message = ""
    if form.validate_on_submit():
        global oauth_key
        oauth_key = form.oauth_key.data
        message = "Successfully submitted"
        shutdown_server()
    return render_template('index.html', form=form, message=message, link=auth_url)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


api = env.str('ACCOUNT_API')
username = env.str('ACCOUNT_USERNAME')
password = ''
oauth_key = ''
extra = {}
try:
    selected_api = utils.available_libs[api]
except KeyError as e:
    print("Invalid API.")
    raise e

if selected_api[2] == utils.LOGIN_PASSWD:
    password = env.str('ACCOUNT_PASSWORD')
elif selected_api[2] in [utils.LOGIN_OAUTH, utils.LOGIN_OAUTH_PKCE]:
    auth_url = selected_api[3]
    if selected_api[2] == utils.LOGIN_OAUTH_PKCE:
        extra['code_verifier'] = utils.oauth_generate_pkce()
        auth_url = auth_url % extra['code_verifier']
    # Ugly hack to open a temporary webserver to get the OAuth key
    app.run(host="0.0.0.0", debug=False)
    password = oauth_key

manager = AccountManager()

if len(manager.get_accounts()) == 0:
    print("No accounts found, adding account...")
    manager.add_account(username, password, api, extra)
    manager.set_default(1)
else:
    account_exists = False
    for num, account in manager.get_accounts():
        # Needs updated logic for OAuth login update
        if selected_api[2] == utils.LOGIN_PASSWD:
            if account["username"] == username and account["api"] == api:
                account_exists = True
                if account["password"] != password:
                    print("Account password mismatch, updating...")
                    manager.edit_account(num, username, password, api)
                if manager.get_default() != manager.get_account(num):
                    print("Setting account as default")
                    manager.set_default(num)
                break
    if not account_exists:
        print ("Could not find account, adding account...")
        manager.add_account(username, password, api, extra)
        manager.set_default(len(manager.get_accounts()))

config_path = utils.to_config_path('config.json')

try:
    config = utils.parse_config(config_path, utils.config_defaults)
except IOError:
    raise utils.EngineFatal("Couldn't open config file.")

for key, value in config.items():
    config[key] = env(key.upper(), cast=type(value), default=value)

utils.save_config(config, config_path)

