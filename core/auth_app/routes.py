import os
import jwt
import uuid
import time
import json
import requests
import datetime
from core.auth_app import bp
from core import mail
from flask_mail import Message


@bp.route('/send_email', methods=['GET'])
def send_email():
    # Getting the access token
    access_token_data = get_access_token()
    if not access_token_data:
        return ({"Error": "Issue retrieving access token."}), 400
    access_token = access_token_data['access_token']

    # Bulk API Kick off
    test_group_id = os.environ.get('TEST_GROUP_ID')
    fhir_bulk_kick_off = os.environ.get('FHIR_KICK_OFF_URL')
    kick_off_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
        "Prefer": "respond-async"
    }
    kick_off_resp = requests.get(
        f"{fhir_bulk_kick_off}{test_group_id}/$export?_type=patient,observation&_typeFilter=Observation%3Fcategory%3Dlaboratory",  # noqa: E501
        headers=kick_off_headers
    )
    if kick_off_resp.status_code != 202:
        print(kick_off_resp.json(), flush=True)
        return ({
            "Error": "Issue during bulk api kick off"
        }), kick_off_resp.status_code

    # Getting the url and status check
    fhir_status_check_url = kick_off_resp.headers['Content-Location']
    fhir_bulk_status_check_data = check_status(
        fhir_status_check_url, access_token
    )
    if not fhir_bulk_status_check_data:
        return ({
            "Error": "Issue during fhir bulk status check"
        }), 400

    # Getting observation url from fhir bulk api response
    observation_urls = []
    existing_ndjson = []
    for each in fhir_bulk_status_check_data['output']:
        # Observation urls are kept in a list incase there are more than one
        if each['type'] == "Observation":
            observation_urls.append(each["url"])

    # Getting data from the observation url
    for each_observation_url in observation_urls:
        obv_resp = requests.get(
            each_observation_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if obv_resp.status_code == 401:
            access_token_data = get_access_token()
            if not access_token_data:
                return ({"Error": "Issue retrieving access token."}), 400
            access_token = access_token_data['access_token']
            obv_resp = requests.get(
                each_observation_url,
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )
        if obv_resp.status_code != 200:
            return ({
                "Error": f"Issue during fetching observatiions data with status code {obv_resp.status_code}."
            }), 400
        resp_ndjson = (obv_resp.text).splitlines()
        existing_ndjson = existing_ndjson + resp_ndjson
    json_observations = []
    ref_range_low = ref_range_high = None
    for line in existing_ndjson:
        try:
            json_observation = json.loads(line)
            json_observations.append(json_observation)
        except json.JSONDecodeError:
            print(f"Failed to parse line as JSON: {line}")
    abnormal_list = []

    # Checking for abnormal data
    for each_json in json_observations:
        abnormal_obj = {}
        obv_value = each_json.get('valueQuantity', {}).get('value')
        ref_range = each_json.get('referenceRange', [None])[0]
        if ref_range:
            ref_range_low = ref_range.get('low', {}).get('value') 
            ref_range_high = ref_range.get('high', {}).get('value')
        if obv_value and ref_range_low and ref_range_high:
            if obv_value <= ref_range_low or obv_value >= ref_range_high:
                abnormal_obj['Lab test for'] = each_json.get('code', {}).get('text')
                abnormal_obj['Reason'] = "Abnormal value"
                abnormal_obj['Patient ID'] = each_json.get('subject', {}).get('reference')
                abnormal_obj['Patient name'] = each_json.get('subject', {}).get('display')
                abnormal_obj['Value'] = obv_value
                abnormal_obj['Reference range high'] = ref_range_high
                abnormal_obj['Reference range low'] = ref_range_low
        else:
            abnormal_obj['Lab test for'] = each_json.get('code', {}).get('text')
            abnormal_obj['Reason'] = "Incomplete data"
            abnormal_obj['Patient ID'] = each_json.get('subject', {}).get('reference')
            abnormal_obj['Patient name'] = each_json.get('subject', {}).get('display')
            abnormal_obj['value'] = obv_value if obv_value else None
            abnormal_obj['Reference range high'] = ref_range_high if ref_range_high else None
            abnormal_obj['Reference range low'] = ref_range_low if ref_range_low else None
        if len(abnormal_obj) > 0:
            abnormal_list.append(json.dumps(abnormal_obj, indent=4))
    if abnormal_list:
        body_string = "Abnormal Data List \n\n"
        html_string = "<b>Abnormal Data List</b><br><ul>"
        for each_item in abnormal_list:
            body_string += f"{each_item}\n,"
            html_string += f"<li>{each_item}</li><br><br>"
        try:
            msg = Message(
                subject="Abnormal Lab report",
                recipients=['vern.kihn@ethereal.email'],
                body=body_string,
                html=html_string + "</ul>" 
            )
            mail.send(msg)
            return "Email sent successfully."
        except Exception as e:
            return ({
                "Error": f"{e} error occured."
            }), 400
    else:
        return ({
            "Message": "No abnormal data. Email not sent."
        }), 200


def get_access_token():
    """Gets the access token from epic"""
    with open('keys.json', 'r') as key_file:
        private_key_data = json.load(key_file)

    # Extract the private key from the loaded data
    private_key = jwt.algorithms.RSAAlgorithm.from_jwk(
        json.dumps(private_key_data['keys'][0])
    )
    payload = {
        'iss': os.environ.get('EPIC_CLIENT_ID'),
        'sub': os.environ.get('EPIC_CLIENT_ID'),
        'aud': os.environ.get('EPIC_TOKEN_URL'),
        'jti': str(uuid.uuid1()),
        'iat': datetime.datetime.now(),
        'exp': datetime.datetime.now() + datetime.timedelta(minutes=5)
    }
    jwt_headers = {
        "typ": "JWT",
        "kid": private_key_data['keys'][0]['kid']
    }
    # Sign the JWT
    token = jwt.encode(
        payload, private_key, algorithm='RS256', headers=jwt_headers
    )

    # Getting the access token
    get_access_token_url = os.environ.get('EPIC_TOKEN_URL')
    token_req_headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    post_data = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": f"{token}"
    }
    get_access_token_resp = requests.post(
        get_access_token_url,
        data=post_data,
        headers=token_req_headers
    )
    if get_access_token_resp.status_code == 200:
        access_token_data = get_access_token_resp.json()
    else:
        access_error_data = get_access_token_resp.json()
        print("Error occured", access_error_data, flush=True)
        access_token_data = None
    return access_token_data


def check_status(url, access_token, interval=10, timeout_val=3000):
    """Polls the bulk api endpoint to get the data"""
    start_time = datetime.datetime.now()
    timeout = datetime.timedelta(seconds=timeout_val)
    while True:
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        if resp.status_code == 401:
            access_token_data = get_access_token()
            if not access_token_data:
                return ({"Error": "Issue retrieving access token."}), 400
            access_token = access_token_data['access_token']
            resp = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )
        if resp.status_code == 200:
            print(
                "Data recieved.",
                flush=True
            )
            return resp.json()
        elif resp.status_code == 202:
            print(
                f"Received 202, retrying in {interval} seconds...",
                flush=True
            )
        # Maybe add here aru status code auda k garne
        current_time = datetime.datetime.now()
        if (current_time - start_time) > timeout:
            print("Request timed out", flush=True)
            return None
        time.sleep(interval)
