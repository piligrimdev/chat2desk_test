import unittest
import responses

from main import Handler


class C2DMock:
    token: str = None

    def __init__(self, token: str):
        self.token = token

class TestCase(unittest.TestCase):
    def setUp(self):
        self.handler = Handler()

        self.c2d_mock = C2DMock('')

        self.responses = responses.RequestsMock()
        self.responses.start()

        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/clients/?limit=200&offset=0',
            'body': """{"data": [
                        {"username": "piligrimdev", "id": 726888910 },
                        {"username": "elsbv", "id": 740209971 } ],
                    "meta": {"total": 2,"limit": 200, "offset": 0}
                    }""",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/tags/',
            'body': """{"data": [
                        {"id": 379158, "label": "VIP" },
                        {"id": 379159,"label": "Лоялен" },
                        {"id": 379160, "label": "Недоволен"} ],
                        "meta": {"total": 3,"limit": 20,"offset": 0 }
                        }""",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.POST,
            'url': "https://api.chat2desk.com/v1/messages",
            'body': "{}",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.POST,
            'url': "https://api.chat2desk.com/v1/tags/assign_to",
            'body': "{}",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.PUT,
            'url': 'https://api.chat2desk.com/v1/dialogs/522372359',
            'body': "{}",
            'status': 200,
            'content_type': 'application/json'
        })

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    @responses.activate
    def test_external_request_has_user(self):
        result = self.handler.manually_handler({
            'event': 'event_name',
            'name': 'piligrimdev'
        }, self.c2d_mock)

        self.assertEqual(result,"Assigned VIP tag for client with name piligrimdev")

    @responses.activate
    def test_external_request_no_user(self):
        result = self.handler.manually_handler({
            'event': 'event_name',
            'name': 'piligrimde1231v'
        }, self.c2d_mock)

        self.assertEqual("Failed assign VIP tag for client with name piligrimde1231v", result)

    @responses.activate
    def test_new_request_has_available_operator(self):
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/clients/726888910',
            'body': """{ "data": { "id": 726888910, "tags": [ { "id": 379158 } ] } }""",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/operators/?limit=200&offset=0',
            'body': """{ "data": [ {"id": 312866, "opened_dialogs": 1 } ],
                                "meta": { "total": 1, "limit": 200, "offset": 0 }
                                }""",
            'status': 200,
            'content_type': 'application/json'
        })

        result = self.handler.new_request_handler({
                "id": 1112,
                "client_id": 726888910,
                "channel_id": 111,
                "dialog_id": 522372359,
                "type": "common"
            }, self.c2d_mock)

        self.assertEqual("Attached operator with 312866 for client with id 726888910", result)

    @responses.activate
    def test_new_request_no_available_operator(self):
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/clients/726888910',
            'body': """{ "data": { "id": 726888910, "tags": [ { "id": 379158 } ] } }""",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/operators/?limit=200&offset=0',
            'body': """{ "data": [ {"id": 312866, "opened_dialogs": 100 } ],
                                "meta": { "total": 1, "limit": 200, "offset": 0 }
                                }""",
            'status': 200,
            'content_type': 'application/json'
        })

        result = self.handler.new_request_handler({
            "id": 1112,
            "client_id": 726888910,
            "channel_id": 111,
            "dialog_id": 522372359,
            "type": "common"
        }, self.c2d_mock)

        self.assertEqual(f"Failed to attach operator for client with id 726888910", result)

    @responses.activate
    def test_new_request_no_vip_tag(self):
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/clients/726888910',
            'body': """{ "data": { "id": 726888910, "tags": [  ] } }""",
            'status': 200,
            'content_type': 'application/json'
        })

        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.chat2desk.com/v1/operators/?limit=200&offset=0',
            'body': """{ "data": [ {"id": 312866, "opened_dialogs": 1 } ],
                                    "meta": { "total": 1, "limit": 200, "offset": 0 }
                                    }""",
            'status': 200,
            'content_type': 'application/json'
        })

        result = self.handler.new_request_handler({
            "id": 1112,
            "client_id": 726888910,
            "channel_id": 111,
            "dialog_id": 522372359,
            "type": "common"
        }, self.c2d_mock)

        self.assertEqual(f"Failed to attach operator for client with id 726888910", result)
