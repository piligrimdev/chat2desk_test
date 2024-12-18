import requests

class Handler:
  headers = {
      "Authorization": f""
  }

  def process_new_request(self, vip_tag_id: int, client_id: int, dialog_id: int) -> None:
      client_data = self.get_client_by_id(client_id)

      if client_data and self.client_has_tag(client_data['data'], vip_tag_id):
          operator_id = self.get_available_operator()
          if operator_id:
              self.send_message_to_user(client_id, "Оператор найден", False, 'system')
              self.set_operator_to_dialog(dialog_id, operator_id, 'OPEN')
          else:
              self.send_message_to_user(client_id, "Оператор не найден", False, 'comment')

  def process_external_post_request(self, username: str, tag_label: str) -> None:
      client_id = self.get_user_id_by_username(username)

      if client_id != -1:
          self.send_message_to_user(client_id, f"Привет,{username}. Хорошего дня!", False, 'to_client')
          tag_id = self.get_tag_id_by_label(tag_label)
          self.assign_tag_to_client(client_id, tag_id)

  def client_has_tag(self, client_data: dict, tag_id: int) -> bool:
      for tag in client_data['tags']:
          if tag['id'] == tag_id:
              return True
      return False

  def get_client_by_id(self, client_id: int) -> dict | None:
      headers = {
          "Authorization": f""
      }

      response = requests.get(f'https://api.chat2desk.com/v1/clients/{client_id}', headers=self.headers)

      if response.ok:
          return response.json()

      return None

  def set_operator_to_dialog(self, dialog_id: int, operator_id: int, state: str = None, initiator_id: int = None) -> int:
      # https://api.chat2desk.com/v1/dialogs/18498876/

      headers = {
          "Authorization": f""
      }

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

      return response.status_code

  def get_client_id_by_dialog_id(self, dialog_id: int) -> int | None:
      # https://api.chat2desk.com/v1/dialogs/18498876/

      headers = {
          "Authorization": f""
      }

      response = requests.get(f' https://api.chat2desk.com/v1/dialogs/{dialog_id}', headers=self.headers)

      if response.ok:
          json = response.json()
          last_msg = json['data']['last_message']
          client_id = last_msg['client_id']
          return client_id

      return None

  def get_request_by_id(self, request_id: int) -> dict | None:
      headers = {
          "Authorization": f""
      }

      response = requests.get(f'https://api.chat2desk.com/v1/requests/{request_id}', headers=self.headers)

      if response.ok:
          return response.json()

      return None

  def get_available_operator(self) -> int | None:
      # https://api.chat2desk.com/v1/operators/

      offset = 0
      offset_step = 1
      limit = 1
      remaining = -1

      headers = {
          "Authorization": f""
      }

      while True:
          params = {
              'limit': limit,
              'offset': offset
          }

          response = requests.get('https://api.chat2desk.com/v1/operators/', headers=self.headers,
                                  params=params)

          operator_json = response.json()

          for operator in operator_json['data']:
              if operator['opened_dialogs'] < 5:
                  return operator['id']

          if remaining == -1:
              remaining = operator_json['meta']['total']

          remaining -= limit
          offset += offset_step

          if remaining <= 0:
              return None

  def assign_tag_to_client(self, client_id: int, tag_id: int) -> int:
      # https://api.chat2desk.com/v1/tags/assign_to

      headers = {
          "Authorization": f""
      }

      body = {
          'assignee_id': client_id,
          'tag_ids': [tag_id],
          'assignee_type': 'client'
      }

      response = requests.post('https://api.chat2desk.com/v1/tags/assign_to', headers=self.headers, data=body)

      return response.status_code

  def get_user_id_by_username(self, username: str) -> int:
        offset = 0
        offset_step = 1
        limit = 1
        remaining = -1

        while True:
            params = {
                'limit': limit,
                'offset': offset
            }

            response = requests.get('https://api.chat2desk.com/v1/clients/', headers=self.headers,
                                    params=params)

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

  def get_tag_id_by_label(self, label: str) -> int:
      offset = 0
      offset_step = 1
      limit = 1
      remaining = -1

      headers = {
          "Authorization": f""
      }

      while True:
          params = {
              'limit': limit,
              'offset': offset
          }

          response = requests.get('https://api.chat2desk.com/v1/tags/', headers=self.headers,
                                  params=params)

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

  def send_message_to_user(self, user_id: int, text: str, open_dialog: bool, type: str) -> int:
      # https://api.chat2desk.com/v1/messages

      headers = {
          "Authorization": f""
      }

      params = {
          'client_id': user_id,
          'text': text,
          'open_dialog': open_dialog,
          'type': type
      }

      response = requests.post('https://api.chat2desk.com/v1/messages', headers=self.headers,
                               params=params)

      return response.status_code

  def manually_handler(self, input_data, c2d):
    self.headers['Authorization'] = c2d.token
    self.process_external_post_request(input_data['name'], 'VIP')
    return input_data['name']

  def new_request_handler(self, input_data, c2d):
    self.headers['Authorization'] = c2d.token
    vip_id = self.get_tag_id_by_label('VIP')
    self.process_new_request(vip_id, input_data['client_id'], input_data['dialog_id'])
    return input_data
