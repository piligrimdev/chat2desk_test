import requests

class Handler:
  headers = {
      "Authorization": f""
  }

  def _retrieve_until_meets_condition_(self, url: str, condition, **kwargs) -> object | None:
      offset = 0
      offset_step = 200
      limit = 200
      remaining = -1

      params = {
          'limit': limit,
          'offset': offset
      }

      with requests.Session() as ses:
          ses.headers = self.headers.copy()
          while True:
              params['limit'] = limit
              params['offset'] = offset

              response = ses.get(url, params=params)
              response.raise_for_status()

              resp_json = response.json()

              result = condition(resp_json, **kwargs)
              if result:
                  return result

              if remaining == -1:
                  remaining = resp_json['meta']['total']

              remaining -= limit
              offset += offset_step

              if remaining <= 0:
                  return None

  def available_operator_condition(self, resp_json: dict) -> int | None:
      for operator in resp_json['data']:
          if operator['opened_dialogs'] < 5:
              return operator['id']
      return None

  def user_id_by_name_condition(self, resp_json: dict, username: str) -> int | None:
      for client in resp_json['data']:
          if client['username'] == username:
              return client['id']
      return None

  def tag_id_by_label_condition(self, resp_json: dict, label: str) -> int | None:
      for tag in resp_json['data']:
          if tag['label'] == label:
              return tag['id']
      return None

  def process_new_request(self, tag_label: str, client_id: int, dialog_id: int) -> int:
      client_data = self.get_client_by_id(client_id)
      tag_id = self.get_tag_id_by_label(tag_label)

      if client_data and tag_id and self.client_has_tag(client_data['data'], tag_id):
          operator_id = self.get_available_operator()
          if operator_id:
              self.send_message_to_user(client_id, "Оператор найден", False, 'system')
              self.set_operator_to_dialog(dialog_id, operator_id, 'OPEN')
              return operator_id
          else:
              self.send_message_to_user(client_id, "Оператор не найден", False, 'comment')
      return -1

  def process_external_post_request(self, username: str, tag_label: str) -> bool:
      client_id = self.get_user_id_by_username(username)

      if client_id:
          self.send_message_to_user(client_id, f"Привет,{username}. Хорошего дня!", False, 'to_client')

          tag_id = self.get_tag_id_by_label(tag_label)
          if tag_id:
            self.assign_tag_to_client(client_id, tag_id)
            return True
      return False

  def client_has_tag(self, client_data: dict, tag_id: int) -> bool:
      for tag in client_data['tags']:
          if tag['id'] == tag_id:
              return True
      return False

  def get_client_by_id(self, client_id: int) -> dict | None:

      response = requests.get(f'https://api.chat2desk.com/v1/clients/{client_id}', headers=self.headers)

      if response.ok:
          return response.json()

      return None

  def set_operator_to_dialog(self, dialog_id: int, operator_id: int, state: str = None, initiator_id: int = None) -> int:

      if not state:
          state = 'closed'
      if not initiator_id:
          initiator_id = operator_id

      body = {
          "operator_id": operator_id,
          "state": state.lower(),
          "initiator_id": initiator_id
      }

      response = requests.put(f' https://api.chat2desk.com/v1/dialogs/{dialog_id}', headers=self.headers, data=body)
      response.raise_for_status()

  def get_client_id_by_dialog_id(self, dialog_id: int) -> int | None:

      response = requests.get(f' https://api.chat2desk.com/v1/dialogs/{dialog_id}', headers=self.headers)

      if response.ok:
          json = response.json()
          last_msg = json['data']['last_message']
          client_id = last_msg['client_id']
          return client_id

      return None

  def get_request_by_id(self, request_id: int) -> dict | None:

      response = requests.get(f'https://api.chat2desk.com/v1/requests/{request_id}', headers=self.headers)

      if response.ok:
          return response.json()

      return None

  def get_available_operator(self) -> int | None:
      return self._retrieve_until_meets_condition_('https://api.chat2desk.com/v1/operators/',
                                                   self.available_operator_condition)

  def assign_tag_to_client(self, client_id: int, tag_id: int) -> None:
      body = {
          'assignee_id': client_id,
          'tag_ids': [tag_id],
          'assignee_type': 'client'
      }

      response = requests.post('https://api.chat2desk.com/v1/tags/assign_to', headers=self.headers, data=body)
      response.raise_for_status()

  def get_user_id_by_username(self, username: str) -> int | None:
      return self._retrieve_until_meets_condition_('https://api.chat2desk.com/v1/clients/',
                                                   self.user_id_by_name_condition,
                                                   username=username)

  def get_tag_id_by_label(self, label: str) -> int | None:
      return self._retrieve_until_meets_condition_('https://api.chat2desk.com/v1/tags/',
                                                   self.tag_id_by_label_condition,
                                                   label=label)

  def send_message_to_user(self, user_id: int, text: str, open_dialog: bool, type: str) -> int:

      params = {
          'client_id': user_id,
          'text': text,
          'open_dialog': open_dialog,
          'type': type
      }

      response = requests.post('https://api.chat2desk.com/v1/messages', headers=self.headers,
                               params=params)
      response.raise_for_status()

  def manually_handler(self, input_data, c2d):
    self.headers['Authorization'] = c2d.token
    client_name = input_data.get('name', '')

    result = f"Failed assign VIP tag for client with name {client_name}"
    try:
        if self.process_external_post_request(client_name, 'VIP'):
            result = f"Assigned VIP tag for client with name {client_name}"
    except requests.exceptions.Timeout:
        print('Request timed out')
    except requests.exceptions.RequestException as e:
        print(f'Exception raised by request method: {e}')

    return result

  def new_request_handler(self, input_data, c2d):
    self.headers['Authorization'] = c2d.token
    client_id = input_data.get('client_id', '')
    dialog_id = input_data.get('dialog_id', '')

    result = f"Failed to attach operator for client with id {client_id}"

    try:
        operator_id = self.process_new_request('VIP', client_id, dialog_id)
        if operator_id != -1:
            result = f"Attached operator with {operator_id} for client with id {client_id}"
    except requests.exceptions.Timeout:
        print('Request timed out')
    except requests.exceptions.RequestException as e:
        print(f'Exception raised by request method: {e}')

    return result
