import requests as Requests
import json as Json
from flask import (
    Flask,
    request as Request,
    render_template_string as RenderTemplateString,
    session as Session,
    redirect as Redirect,
    url_for as URL_For,
    flash as Flash,
)
import os as OS
import random as Random
import string as String


def SendVerificationCode(PhoneNumber, VerificationCode):
    Url = "https://rest.payamak-panel.com/api/SendSMS/BaseServiceNumber"
    Username = "9914256801"
    Password = "1393@Karun4"
    TemplateId = 376289

    Payload = {
        "username": Username,
        "password": Password,
        "to": PhoneNumber,
        "bodyId": TemplateId,
        "text": VerificationCode,
    }
    Headers = {"Content-Type": "application/json"}
    try:
        Response = Requests.post(Url, data=Json.dumps(Payload), headers=Headers)
        Response.raise_for_status()
        ApiResponse = Response.json()

        if ApiResponse.get("RetStatus") == 1:
            return (ApiResponse, None)
        else:
            ErrorMessage = ApiResponse.get("Value", "An unknown API error occurred.")
            print(f"SMS API returned a failure status: {ErrorMessage}")
            return (None, f"Failed to send SMS: {ErrorMessage}")

    except Requests.exceptions.HTTPError as e:
        print(f"SMS API returned an HTTP error: {e}")
        return (None, "The SMS service is currently unavailable.")
    except Requests.exceptions.RequestException as e:
        print(f"An error occurred while calling the SMS API: {e}")
        return (None, "Could not connect to the SMS service.")


App = Flask(__name__)
App.secret_key = OS.urandom(24)

IndexTemplate = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phone Verification</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #333; }
        input[type="tel"] { width: 90%; padding: 0.8rem; margin-top: 1rem; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 95%; padding: 0.8rem; margin-top: 1rem; border: none; background-color: #007BFF; color: white; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        button:hover { background-color: #0056b3; }
        .message { margin-top: 1rem; padding: 1rem; border-radius: 4px; background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Enter Your Phone Number</h1>
        <p>We will send you a one-time verification code.</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="message {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="post">
            <input type="tel" name="PhoneNumber" placeholder="e.g., 09123456789" required>
            <button type="submit">Send Code</button>
        </form>
    </div>
</body>
</html>
"""

VerifyTemplate = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enter Code</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #333; }
        p { color: #555; }
        input[type="text"] { width: 90%; padding: 0.8rem; margin-top: 1rem; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 95%; padding: 0.8rem; margin-top: 1rem; border: none; background-color: #28a745; color: white; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        button:hover { background-color: #218838; }
        .message { margin-top: 1rem; padding: 1rem; border-radius: 4px; }
        .message.success { background-color: #d4edda; color: #155724; }
        .message.error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Enter Verification Code</h1>
        <p>A code was sent to <strong>{{ PhoneNumber }}</strong>.</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="message {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="post">
            <input type="text" name="OtpCode" placeholder="Enter the code" required>
            <button type="submit">Verify</button>
        </form>
    </div>
</body>
</html>
"""

SuccessTemplate = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Success</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #28a745; }
        a { color: #007BFF; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Verification Successful!</h1>
        <p>Your phone number has been verified.</p>
        <a href="{{ url_for('Index') }}">Start Over</a>
    </div>
</body>
</html>
"""


@App.route("/", methods=["GET", "POST"])
def Index():
    if Request.method == "POST":
        PhoneNumber = Request.form["PhoneNumber"]
        VerificationCode = "".join(Random.choices(String.digits, k=5))
        ApiResponse, ErrorMessage = SendVerificationCode(PhoneNumber, VerificationCode)

        if ApiResponse:
            Session["OtpCode"] = VerificationCode
            Session["PhoneNumber"] = PhoneNumber
            print(f"Verification code sent to {PhoneNumber}: {Session['OtpCode']}")
            return Redirect(URL_For("Verify"))
        else:
            Flash(ErrorMessage or "An unknown error occurred.", "error")
            return Redirect(URL_For("Index"))

    return RenderTemplateString(IndexTemplate)


@App.route("/verify", methods=["GET", "POST"])
def Verify():
    PhoneNumber = Session.get("PhoneNumber")
    if not PhoneNumber:
        return Redirect(URL_For("Index"))

    if Request.method == "POST":
        UserEnteredCode = Request.form["OtpCode"]
        StoredCode = Session.get("OtpCode")

        if UserEnteredCode == StoredCode:
            Session.pop("OtpCode", None)
            Session.pop("PhoneNumber", None)
            return RenderTemplateString(SuccessTemplate)
        else:
            Flash("Invalid verification code. Please try again.", "error")
            return RenderTemplateString(VerifyTemplate, PhoneNumber=PhoneNumber)

    return RenderTemplateString(VerifyTemplate, PhoneNumber=PhoneNumber)


if __name__ == "__main__":
    App.run(debug=True)
