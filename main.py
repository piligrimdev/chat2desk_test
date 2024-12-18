import os

import requests
from dotenv import load_dotenv

load_dotenv()


def get_user_id_by_username(username: str) -> int:
    offset = 0
    offset_step = 1
    limit = 1
    remaining = -1

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    while True:
        params = {
            'limit': limit,
            'offset': offset
        }

        response = requests.get('https://api.chat2desk.com/v1/clients/', headers=headers,
                                params=params)
        print('.')

        clients_json = response.json()

        for client in clients_json['data']:
            if client['username'] == username:
                return client['id']

        if remaining == -1:
            remaining = clients_json['meta']['total']

        remaining -= limit
        offset += offset_step

        if remaining <= 0:
            return -1

def get_tag_id_by_label(label: str) -> int:
    offset = 0
    offset_step = 1
    limit = 1
    remaining = -1

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    while True:
        params = {
            'limit': limit,
            'offset': offset
        }

        response = requests.get('https://api.chat2desk.com/v1/tags/', headers=headers,
                                params=params)
        print('.')

        tags_json = response.json()

        for tag in tags_json['data']:
            if tag['label'] == label:
                return tag['id']

        if remaining == -1:
            remaining = tags_json['meta']['total']

        remaining -= limit
        offset += offset_step

        if remaining <= 0:
            return -1

def send_message_to_user(user_id: int, text: str, open_dialog: bool, type: str) -> int:
    # https://api.chat2desk.com/v1/messages

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    params = {
        'client_id': user_id,
        'text': text,
        'open_dialog': open_dialog,
        'type': type
    }

    response = requests.post('https://api.chat2desk.com/v1/messages', headers=headers,
                            params=params)

    return response.status_code

def assign_tag_to_client(client_id: int, tag_id: int) -> int:
    # https://api.chat2desk.com/v1/tags/assign_to

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    body = {
        'assignee_id': client_id,
        'tag_ids': [tag_id],
        'assignee_type': 'client'
    }

    response = requests.post('https://api.chat2desk.com/v1/tags/assign_to', headers=headers,data=body)

    return response.status_code

def get_available_operator() -> int | None:
    # https://api.chat2desk.com/v1/operators/

    offset = 0
    offset_step = 1
    limit = 1
    remaining = -1

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    while True:
        params = {
            'limit': limit,
            'offset': offset
        }

        response = requests.get('https://api.chat2desk.com/v1/operators/', headers=headers,
                                params=params)
        print('.')

        operator_json = response.json()

        for operator in operator_json['data']:
            if operator['opened_dialogs'] < 0:
                return operator['id']

        if remaining == -1:
            remaining = operator_json['meta']['total']

        remaining -= limit
        offset += offset_step

        if remaining <= 0:
            return None

def get_request_by_id(request_id: int) -> dict | None:
    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    response = requests.get(f'https://api.chat2desk.com/v1/requests/{request_id}', headers=headers)

    if response.ok:
        return response.json()

    return None

def get_client_id_by_dialog_id(dialog_id: int) -> int | None:
    # https://api.chat2desk.com/v1/dialogs/18498876/

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    response = requests.get(f' https://api.chat2desk.com/v1/dialogs/{dialog_id}', headers=headers)

    if response.ok:
        json = response.json()
        last_msg = json['data']['last_message']
        client_id = last_msg['client_id']
        return client_id

    return None

def set_operator_to_dialog(dialog_id: int, operator_id: int, state: str = None, initiator_id: int = None) -> int:
    # https://api.chat2desk.com/v1/dialogs/18498876/

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    if not state:
        state = 'closed'
    if not initiator_id:
        initiator_id = operator_id

    body={
        "operator_id": operator_id,
        "state": state,
        "initiator_id": initiator_id
    }

    response = requests.put(f' https://api.chat2desk.com/v1/dialogs/{dialog_id}', headers=headers, data=body)

    return response.status_code

def get_messages():
    # https://api.chat2desk.com/v1/messages/

    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    response = requests.get(f' https://api.chat2desk.com/v1/messages/', headers=headers)

    json = response.json()
    return [x['request_id'] for x in response.json()['data']]

def get_client_by_id(client_id: int) -> dict | None:
    headers = {
        "Authorization": f"{os.getenv('API_TOKEN', ' ')}"
    }

    response = requests.get(f'https://api.chat2desk.com/v1/clients/{client_id}', headers=headers)

    if response.ok:
        return response.json()

    return None

def client_has_tag(client_data: dict, tag_id: int) -> bool:
    for tag in client_data['tags']:
        if tag['id'] == tag_id:
            return True
    return False

def process_external_post_request():
    req_name = 'piligrimdev'
    tag_label_to_assign = 'VIP'
    client_id = get_user_id_by_username(req_name)

    if client_id == -1:
        print('No user with username', req_name)
    else:
        print('User with name ', req_name, ' has id ', client_id)
        send_message_to_user(client_id, f"Привет,{req_name}. Хорошего дня!", False, 'to_client')
        tag_id = get_tag_id_by_label(tag_label_to_assign)
        print(assign_tag_to_client(client_id, tag_id))

def process_new_request_tag_req(request_id):
    request_data = get_request_by_id(request_id)

    if VIP_id in request_data['tags']:
        client_id = get_client_id_by_dialog_id(request_data['dialog_id'])
        operator_id = get_available_operator()
        if operator_id:
            print(send_message_to_user(client_id, "Оператор найден", False, 'system'))
            print(set_operator_to_dialog(request_data['dialog_id'], operator_id, 'open'))
        else:
           print(send_message_to_user(client_id, "Оператор не найден", False, 'comment'))

# вариант с тегом пользователя
def process_new_request(request_id):
    request_data = get_request_by_id(request_id)
    client_id = get_client_id_by_dialog_id(request_data['dialog_id'])
    client_data = get_client_by_id(client_id)

    if client_has_tag(client_data['data'], VIP_id):
        operator_id = get_available_operator()
        if operator_id:
            print(send_message_to_user(client_id, "Оператор найден", False, 'system'))
            print(set_operator_to_dialog(request_data['dialog_id'], operator_id, 'open'))
        else:
           print(send_message_to_user(client_id, "Оператор не найден", False, 'comment'))

VIP_id = get_tag_id_by_label('VIP')

print(get_messages())