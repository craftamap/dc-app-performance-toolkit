import yaml
import typing

from util.project_paths import JIRA_YML, CONFLUENCE_YML, BITBUCKET_YML

TOOLKIT_VERSION = '4.0.0'


def read_yml_file(file) -> typing.Dict[str, typing.Any]:
    with file.open(mode='r') as file:
        return yaml.load(file, Loader=yaml.FullLoader)


class AppSettings:

    def __init__(self, config_yml):
        obj = read_yml_file(config_yml)
        env_settings = obj['settings']['env']
        self.hostname = env_settings['application_hostname']
        self.protocol = env_settings['application_protocol']
        self.port = env_settings['application_port']
        self.postfix = env_settings['application_postfix'] or ""
        self.admin_login = env_settings['admin_login']
        self.admin_password = env_settings['admin_password']
        self.concurrency = env_settings['concurrency']
        self.duration = env_settings['test_duration']
        self.analytics_collector = env_settings['allow_analytics']
        self.load_executor = env_settings['load_executor']
        self.webdriver_visible = env_settings['WEBDRIVER_VISIBLE']
        self.secure = env_settings['secure']

    @property
    def server_url(self) -> str:
        return f'{self.protocol}://{self.hostname}:{self.port}{self.postfix}'


class AppSettingsExtLoadExecutor(AppSettings):

    def __init__(self, config_yml):
        super().__init__(config_yml)
        obj = read_yml_file(config_yml)
        self.env = obj['settings']['env']
        self.verbose = obj['settings']['verbose']
        self.total_actions_per_hour = self.env['total_actions_per_hour']
        self.custom_dataset_query = self.env['custom_dataset_query']


JIRA_SETTINGS = AppSettingsExtLoadExecutor(config_yml=JIRA_YML)
CONFLUENCE_SETTINGS = AppSettingsExtLoadExecutor(config_yml=CONFLUENCE_YML)
BITBUCKET_SETTINGS = AppSettings(config_yml=BITBUCKET_YML)
