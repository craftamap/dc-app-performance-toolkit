import json
from abc import ABC
import typing

import requests
from requests import Response


class Client(ABC):
    def __init__(self, host: str, user: str, password: str):
        self._host = host
        self._user = user
        self._password = password

    @property
    def host(self) -> str:
        return self._host

    @property
    def user(self) -> str:
        return self._user

    @property
    def password(self) -> str:
        return self._password


class RestClient(Client):
    JSON_HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    LOGIN_POST_HEADERS = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.9'
        }

    @staticmethod
    def to_json(obj: dict) -> str:
        return json.dumps(obj)

    def __init__(
        self, host: str, user: str, password: str, session: typing.Optional[requests.Session] = None, timeout: int = 30
    ):
        super().__init__(host, user, password)

        self._requests_timeout = timeout
        self._session = session or requests.Session()

    @property
    def requests_timeout(self) -> int:
        return self._requests_timeout

    @property
    def session(self) -> requests.Session:
        return self._session

    @property
    def base_auth(self) -> typing.Tuple[str, str]:
        return self.user, self.password

    def get(
        self, url: str, error_msg: str, expected_status_codes: typing.Optional[typing.List[int]] = None,
        allow_redirect=False
    ) -> Response:
        response = self.session.get(url, auth=self.base_auth, verify=False, timeout=self.requests_timeout,
                                    allow_redirects=allow_redirect)
        self.__verify_response(response, error_msg, expected_status_codes)
        return response

    def post(
        self, url: str, error_msg: str, body: typing.Optional[dict] = None, params: typing.Optional[dict] = None,
        allow_redirect=False
    ) -> Response:
        body_data = self.to_json(body) if body else None
        response = self.session.post(url, body_data, params=params, auth=self.base_auth, headers=self.JSON_HEADERS,
                                     allow_redirects=allow_redirect)

        self.__verify_response(response, error_msg)
        return response

    def put(
        self, url: str, error_msg: str, body: dict = None, params: typing.Optional[dict] = None,
        allow_redirect=False
    ) -> Response:
        body_data = self.to_json(body) if body else None
        response = self.session.put(url, body_data, params=params, auth=self.base_auth, headers=self.JSON_HEADERS,
                                    allow_redirects=allow_redirect)

        self.__verify_response(response, error_msg)
        return response

    def __verify_response(
        self, response: Response, error_msg: str, expected_status_codes: typing.Optional.typing.List[int] = None
    ):
        if response.is_redirect:
            raise Exception("Redirect detected.\n "
                            "Please check config.yml file (application_hostname, application_port, "
                            "application_protocol, application_postfix).")
        if response.ok or (expected_status_codes and response.status_code in expected_status_codes):
            return

        status_code = response.status_code
        if status_code == 403:
            denied_reason: str = response.headers.get('X-Authentication-Denied-Reason')
            if denied_reason and denied_reason.startswith('CAPTCHA_CHALLENGE'):
                raise Exception(f"User name [{self.user}] is in Captcha Mode. " +
                                "Please login via Web UI first and re-run tests.")
        elif status_code == 404:
            raise Exception(f"The URL or content are not found for {response.url}. "
                            f"Please check environment variables in "
                            f"config.yml file (application_hostname, application_port, application_protocol, "
                            f"application_postfix).")
        raise Exception(f"{error_msg}. Response code:[{response.status_code}], response text:[{response.text}]")
