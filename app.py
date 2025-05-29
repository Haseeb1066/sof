from flask import Flask, render_template, request
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os
import pandas as pd
import io
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
client = OpenAI()

# Tableau Config
PAT_NAME = "test"
PAT_SECRET = "MMPfXGM1SiiimTQoRV7HTA==:cSqLgPrazgDIvtrl5wlPB9GKdZTTMFTH"
SITE_CONTENT_URL = "multinetpakistanpvtltd"
TABLEAU_SERVER = "https://prod-apnortheast-a.online.tableau.com"
API_VERSION = "3.18"
VIEW_ID = "6bcc2ce9-60e5-4c42-9ff1-e38b14e82f74"

chat_history = []

def sign_in():
    signin_url = f"{TABLEAU_SERVER}/api/{API_VERSION}/auth/signin"
    payload = {
        "credentials": {
            "personalAccessTokenName": PAT_NAME,
            "personalAccessTokenSecret": PAT_SECRET,
            "site": {"contentUrl": SITE_CONTENT_URL}
        }
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(signin_url, json=payload, headers=headers)
    if response.status_code != 200:
        return None, None
    root = ET.fromstring(response.text)
    ns = {'t': 'http://tableau.com/api'}
    credentials = root.find('t:credentials', ns)
    if credentials is None:
        return None, None
    token = credentials.attrib['token']
    site_id = credentials.find('t:site', ns).attrib['id']
    return token, site_id

def get_view_data(token, site_id, view_id):
    headers = {"X-Tableau-Auth": token}
    data_url = f"{TABLEAU_SERVER}/api/{API_VERSION}/sites/{site_id}/views/{view_id}/data"
    response = requests.get(data_url, headers=headers)
    if response.status_code != 200:
        return None
    return pd.read_csv(io.StringIO(response.text))

def ask_openai(question, context_data):
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use the provided data to answer questions."},
        {"role": "user", "content": f"Here is the data:\n{context_data}"},
        {"role": "user", "content": question}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return response.choices[0].message.content

@app.route("/", methods=["GET", "POST"])
def index():
    global chat_history

    token, site_id = sign_in()
    if not token:
        return "❌ Tableau authentication failed."

    df = get_view_data(token, site_id, VIEW_ID)
    if df is None:
        return "❌ Failed to fetch data from Tableau View."

    data_str = df.to_string(index=False)  # Keep data hidden from frontend

    if request.method == "POST":
        user_input = request.form["user_input"]
        bot_reply = ask_openai(user_input, data_str)
        chat_history.append({"user": user_input, "bot": bot_reply})

    return render_template("index.html", chat_history=chat_history)

if __name__ == "__main__":
    # app.run(debug=True, host='172.16.2.131', port=5000)
    app.run(debug=True)

