import requests


class Handler:
    headers = {"Authorization": ""}

    def _retrieve_until_meets_condition_(self, url: str,
                                         condition, **kwargs) -> object | None:
        """
        Запрашивает объекты по API до тех пор, пока необходимый объект не будет найден.

        :param url: url для API запроса
        :param condition: метод, который будет проверять,
         есть ли искомый объект среди полученных
        :param kwargs: аргументы, передаваемые в метод condition
        :return: Искомый объект или None
        """
        offset = 0
        offset_step = 200
        limit = 200
        remaining = None

        params = {"limit": limit, "offset": offset}

        with requests.Session() as ses:
            ses.headers = self.headers.copy()
            while True:
                params["limit"] = limit
                params["offset"] = offset

                response = ses.get(url, params=params)
                response.raise_for_status()

                resp_json = response.json()

                result = condition(resp_json, **kwargs)
                if result:
                    return result

                if remaining is None:
                    remaining = resp_json["meta"]["total"]

                remaining -= (
                    limit  # Вычитаем из общего числа объектов кол-во полученных
                )
                offset += offset_step  # Для запроса следующей пачку

                if remaining <= 0:  # Если объектов не осталось
                    return None

    def available_operator_condition(self, resp_json: dict) -> int | None:
        """
        Метод, передаваемый в Handler._retrieve_until_meets_condition_().

        Проверяет, есть ли среди полученных операторов тот, у которого кол-во диалогов меньше 5.
        :param resp_json: json с операторам.
        :return: id первого подходящего оператора или None, если такого нет.
        """
        for operator in resp_json["data"]:
            if operator["opened_dialogs"] < 5:
                return operator["id"]
        return None

    def user_id_by_name_condition(self, resp_json: dict, username: str) -> int | None:
        """
        Метод, передаваемый в Handler._retrieve_until_meets_condition_().

        Среди полученных клиентов ищет клиента с подходящим именем.
        :param resp_json: json с клиентами.
        :param username: имя, по которому будет идти поиск
        :return: id подходящего клиента или None, если такого нет.
        """
        for client in resp_json["data"]:
            if client["name"] == username:
                return client["id"]
        return None

    def tag_id_by_label_condition(self, resp_json: dict, label: str) -> int | None:
        """
        Метод, передаваемый в Handler._retrieve_until_meets_condition_().

        Среди полученных тегов ищет тег с подходящим названием.
        :param resp_json: json c тегами
        :param label: название, по которому будет идти поиск
        :return: id подходящего тега или None, если такого нет.
        """
        for tag in resp_json["data"]:
            if tag["label"] == label:
                return tag["id"]
        return None

    def process_new_request(
        self, tag_label: str, client_id: int, dialog_id: int
    ) -> int:
        """
        Метод, обрабатывающий новый запрос.

        Если клиент имеет необходимый тег, ищет свободного оператора.
        Отправляет системное сообщение и переводит на оператора, если свободный оператор найден.
        Отправляет сообщение-комментарий, если оператор не найден.
        :param tag_label: Название необходимого клиенту тега.
        :param client_id: id клиента у запроса
        :param dialog_id: id диалога у запроса
        :return: id оператора если он найден, в противном случае -1.
        """
        client_data = self.get_client_by_id(client_id)
        tag_id = self.get_tag_id_by_label(tag_label)

        if client_data and tag_id and self.client_has_tag(client_data["data"], tag_id):
            operator_id = self.get_available_operator()
            if operator_id:
                self.send_message_to_user(client_id, "Оператор найден", False, "system")
                self.set_operator_to_dialog(dialog_id, operator_id, "OPEN")
                return operator_id
            else:
                self.send_message_to_user(
                    client_id, "Оператор не найден", False, "comment"
                )
        return -1

    def process_external_post_request(self, username: str, tag_label: str) -> bool:
        """
        Метод, обрабатывающий запрос из внешней системы.

        Ищет клиента с указанный именем.
        Если клиент существует, присваивает ему тег с указанным
         названием и отправляет приветсвенное сообщение.
        :param username: имя искомого клиентами.
        :param tag_label: название тега, который необходимо присвоить.
        :return: True, если клиент найден,
         сообщение отправлено и присвоен тег. В противном случае False/
        """
        client_id = self.get_user_id_by_username(username)

        if client_id:
            self.send_message_to_user(
                client_id, f"Привет,{username}. Хорошего дня!", False, "to_client"
            )

            tag_id = self.get_tag_id_by_label(tag_label)
            if tag_id:
                self.assign_tag_to_client(client_id, tag_id)
                return True
        return False

    def client_has_tag(self, client_data: dict, tag_id: int) -> bool:
        """
        Проверяет, имеет ли клиент необходимый тег.

        :param client_data: json-данные клиента.
        :param tag_id: id искомого тега.
        :return: True, если имеет. False, если нет.
        """
        for tag in client_data["tags"]:
            if tag["id"] == tag_id:
                return True
        return False

    def get_client_by_id(self, client_id: int) -> dict | None:
        """
        Запрашивает по API данные клиента с указанным id.

        :param client_id: id клиента.
        :return: json-данные клиента если он найден.
         None, если не найден или ответ вернулся с ошибкой.
        """
        response = requests.get(
            f"https://api.chat2desk.com/v1/clients/{client_id}", headers=self.headers
        )

        if response.ok:
            return response.json()

        return None

    def set_operator_to_dialog(
        self,
        dialog_id: int,
        operator_id: int,
        state: str = None,
        initiator_id: int = None,
    ) -> None:
        """
        Присваивает оператора диалогу.

        Выбрасывает исключение, если результат запроса не успешен.
        :param dialog_id: id диалога.
        :param operator_id: id оператора.
        :param state: "OPEN" для того, чтобы открыть диалог. "CLOSE", чтобы не открывать.
        :param initiator_id: id инициатора диалога. По умолчанию будет установлен id оператора.
        :return: None.
        """
        if not state:
            state = "closed"
        if not initiator_id:
            initiator_id = operator_id

        body = {
            "operator_id": operator_id,
            "state": state.lower(),
            "initiator_id": initiator_id,
        }

        response = requests.put(
            f" https://api.chat2desk.com/v1/dialogs/{dialog_id}",
            headers=self.headers,
            data=body,
        )
        response.raise_for_status()

    def get_client_id_by_dialog_id(self, dialog_id: int) -> int | None:
        """
        Запрашивает по API id клиента у диалога с  указанным id.

        :param dialog_id: id диалога.
        :return: id клиента, если запрос успешен. None, если нет.
        """
        response = requests.get(
            f" https://api.chat2desk.com/v1/dialogs/{dialog_id}", headers=self.headers
        )

        if response.ok:
            json = response.json()
            last_msg = json["data"]["last_message"]
            client_id = last_msg["client_id"]
            return client_id

        return None

    def get_request_by_id(self, request_id: int) -> dict | None:
        """
        Получает данные обращения по id.

        :param request_id: id обращения.
        :return: json-данные обращения, если оно найдено.
        None, если не найдено или запрос не успешен.
        """
        response = requests.get(
            f"https://api.chat2desk.com/v1/requests/{request_id}", headers=self.headers
        )

        if response.ok:
            return response.json()

        return None

    def get_available_operator(self) -> int | None:
        """
        Получает первого доступного оператора.

        :return: id оператора, если он найден. None, если нет.
        """
        return self._retrieve_until_meets_condition_(
            "https://api.chat2desk.com/v1/operators/", self.available_operator_condition
        )

    def assign_tag_to_client(self, client_id: int, tag_id: int) -> None:
        """
        Присваивает тег клиенту.

        Выбрасывает исключение, если результат запроса не успешен.
        :param client_id: id клиента.
        :param tag_id: id тега.
        :return: None.
        """
        body = {
            "assignee_id": client_id,
            "tag_ids": [tag_id],
            "assignee_type": "client",
        }

        response = requests.post(
            "https://api.chat2desk.com/v1/tags/assign_to",
            headers=self.headers,
            data=body,
        )
        response.raise_for_status()

    def get_user_id_by_username(self, username: str) -> int | None:
        """
        Ищет пользователя по его имени.

        :param username: искомое имя пользователя.
        :return: id пользователя, если найден пользователь с указанным именем. None, если нет.
        """
        return self._retrieve_until_meets_condition_(
            "https://api.chat2desk.com/v1/clients/",
            self.user_id_by_name_condition,
            username=username,
        )

    def get_tag_id_by_label(self, label: str) -> int | None:
        """
        Ищет тег по его названию.

        :param label: название тега.
        :return: id тега, если найден тег с таким названием. None, если нет.
        """
        return self._retrieve_until_meets_condition_(
            "https://api.chat2desk.com/v1/tags/",
            self.tag_id_by_label_condition,
            label=label,
        )

    def send_message_to_user(
        self, client_id: int, text: str, open_dialog: bool, type: str
    ) -> None:
        """
        Отправляет клиенту сообщение.

        Выбрасывает исключение, если результат запроса не успешен.
        :param client_id: id клиента.
        :param text: Текст сообщения.
        :param open_dialog: Флаг, True, если диалог необходимо открыть. False, если нет.
        :param type: Тип сообщения.
        :return: None.
        """
        params = {
            "client_id": client_id,
            "text": text,
            "open_dialog": str(open_dialog).lower(),
            "type": type,
        }

        response = requests.post(
            "https://api.chat2desk.com/v1/messages", headers=self.headers, params=params
        )
        response.raise_for_status()

    def manually_handler(self, input_data, c2d):
        """
        Обработчик триггеров из внешних систем.

        :param input_data: Входные данные.
        :param c2d: Объект c2d.
        :return: Результат обработки.
        """
        self.headers["Authorization"] = c2d.token
        client_name = input_data.get("name", "")

        result = f"Failed assign VIP tag for client with name {client_name}"
        try:
            if self.process_external_post_request(client_name, "VIP"):
                result = f"Assigned VIP tag for client with name {client_name}"
        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.RequestException as e:
            print(f"Exception raised by request method: {e}")

        return result

    def new_request_handler(self, input_data, c2d):
        """
        Обработчик новых обращений.

        :param input_data: Входные данные.
        :param c2d: Объект c2d.
        :return: Результат обработки.
        """
        self.headers["Authorization"] = c2d.token
        client_id = input_data.get("client_id", "")
        dialog_id = input_data.get("dialog_id", "")

        result = f"Failed to attach operator for client with id {client_id}"

        try:
            operator_id = self.process_new_request("VIP", client_id, dialog_id)
            if operator_id != -1:
                result = f"Attached operator with {operator_id} for client with id {client_id}"
        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.RequestException as e:
            print(f"Exception raised by request method: {e}")

        return result
