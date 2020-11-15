import xmlrpc.client

from lxml import html
import typing

from util.api.abstract_clients import RestClient, Client

BATCH_SIZE_SEARCH = 500


class ConfluenceRestClient(RestClient):

    def get_content(self, start=0, limit=100, type="page", expand="space") -> list:
        """
        Returns all content. This only includes pages that the user has permission to view.
        :param start: The starting index of the returned boards. Base index: 0.
        :param limit: The maximum number of boards to return per page. Default: 50.
        :param type: the content type to return. Default value: page. Valid values: page, blogpost.
        :param expand: Responds with additional values. Valid values: space,history,body.view,metadata.label
        :return: Returns the requested content, at the specified page of the results.
        """
        BATCH_SIZE_SEARCH = 200
        loop_count = limit // BATCH_SIZE_SEARCH + 1
        content = list()
        last_loop_remainder = limit % BATCH_SIZE_SEARCH
        limit = BATCH_SIZE_SEARCH if limit > BATCH_SIZE_SEARCH else limit

        while loop_count > 0:
            api_url = (
                    self.host + f'/rest/api/content/?type={type}'
                                f'&start={start}'
                                f'&limit={limit}'
                                f'&expand={expand}'
            )
            request = self.get(api_url, "Could not retrieve content")

            content.extend(request.json()['results'])
            if len(content) < 0:
                raise Exception(f"Content with type {type} is empty")

            loop_count -= 1
            if loop_count == 1:
                limit = last_loop_remainder

            start += len(request.json()['results'])

        return content

    def get_content_search(self, start=0, limit=100, cql: typing.Optional[str] = None, expand="space") -> list:
        """
        Fetch a list of content using the Confluence Query Language (CQL).
        :param start: The starting index of the returned boards. Base index: 0.
        :param limit: The maximum number of boards to return per page. Default: 50.
        :param cql: Filters results to boards of the specified type. Valid values: page, blogpost
        :param expand: Responds with additional values. Valid values: space,history,body.view,metadata.label
        :return: Returns the requested content, at the specified page of the results.
        """
        BATCH_SIZE_SEARCH = 200
        loop_count = limit // BATCH_SIZE_SEARCH + 1
        content = list()
        last_loop_remainder = limit % BATCH_SIZE_SEARCH
        limit = BATCH_SIZE_SEARCH if limit > BATCH_SIZE_SEARCH else limit

        while loop_count > 0:
            api_url = (
                    self.host + f'/rest/api/content/search?cql={cql}'
                                f'&start={start}'
                                f'&limit={limit}'
                                f'&expand={expand}'
            )
            request = self.get(api_url, "Could not retrieve content")

            content.extend(request.json()['results'])
            if len(content) < 0:
                raise Exception(f"Content with {cql} is empty")

            loop_count -= 1
            if loop_count == 1:
                limit = last_loop_remainder

            start += len(request.json()['results'])

        return content

    def get_users(self, prefix: str, count: int) -> list:
        users_list = self.search(f"user~{prefix}", limit=count)
        return users_list

    def get_confluence_version(self) -> str:
        version = ''
        api_url = f'{self.host}/rest/applinks/1.0/manifest'
        response = self.get(api_url, 'Could not get Confluence manifest')
        tree = html.fromstring(response.content)
        for child in tree:
            if child.tag == 'version':
                version = child.text
        return version

    def search(
        self, cql, cqlcontext: typing.Optional[str] = None, expand: typing.Optional[str] = None, start=0, limit=500
    ) -> list:
        """
        Fetch a list of content using the Confluence Query Language (CQL).
        :param cql: a cql query string to use to locate content
        :param cqlcontext: the context to execute a cql search in, this is the json serialized form of SearchContext
        :param expand: a comma separated list of properties to expand on the content
        :param start: the start point of the collection to return
        :param limit: the limit of the number of items to return, this may be restricted by fixed system limits
        :return:
        """
        loop_count = limit // BATCH_SIZE_SEARCH + 1
        last_loop_remainder = limit % BATCH_SIZE_SEARCH

        search_results_list = list()
        limit = BATCH_SIZE_SEARCH if limit > BATCH_SIZE_SEARCH else limit

        while loop_count > 0:
            api_url = f'{self.host}/rest/api/search?cql={cql}&start={start}&limit={limit}'
            response = self.get(api_url, "Search failed")

            search_results_list.extend(response.json()['results'])
            loop_count -= 1
            start += len(response.json())
            if loop_count == 1:
                limit = last_loop_remainder

        return search_results_list

    def is_remote_api_enabled(self) -> bool:
        api_url = f'{self.host}/rpc/xmlrpc'
        response = self.get(api_url, error_msg='Confluence Remote API (XML-RPC & SOAP) is disabled. '
                                               'For further processing enable Remote API via '
                                               'General Configuration - Further Configuration - Remote API')
        return response.status_code == 200

    def get_confluence_nodes_count(self) -> typing.Union[str, int]:
        api_url = f"{self.host}/rest/atlassian-cluster-monitoring/cluster/nodes"
        response = self.get(api_url, error_msg='Could not get Confluence nodes count via API',
                            expected_status_codes=[200, 500])
        return 'Server' if response.status_code == 500 and 'NonClusterMonitoring' in response.text\
            else len(response.json())

    def get_total_pages_count(self) -> int:
        api_url = f"{self.host}/rest/api/search?cql=type=page"
        response = self.get(api_url, 'Could not get issues count')
        return response.json().get('totalSize', 0)

    def get_collaborative_editing_status(self) -> dict:
        api_url = f'{self.host}/rest/synchrony-interop/status'
        response = self.get(api_url, error_msg='Could not get collaborative editing status')
        return response.json()

    def get_locale(self) -> str:
        language = None
        page = self.get(f"{self.host}/index.action#all-updates", "Could not get page content.").content
        tree = html.fromstring(page)
        try:
            language = tree.xpath('.//meta[@name="ajs-user-locale"]/@content')[0]
        except Exception as error:
            print(f"Warning: Could not get user locale: {error}")
        return language

    def get_groups_membership(self, username: str) -> typing.List[str]:
        api_url = f'{self.host}/rest/api/user/memberof?username={username}'
        response = self.get(api_url, error_msg='Could not get group members')
        groups = [group['name'] for group in response.json()['results']]
        return groups


class ConfluenceRpcClient(Client):

    def create_user(self, username: str = None, password: str = None) -> typing.Dict[str, typing.Dict[str, str]]:
        """
        Creates user. Uses XML-RPC protocol
        (https://developer.atlassian.com/server/confluence/confluence-xml-rpc-and-soap-apis/)
        :param username: Username to create
        :param password: Password for user
        :return: user
        """
        proxy = xmlrpc.client.ServerProxy(self.host + "/rpc/xmlrpc")
        token = proxy.confluence2.login(self.user, self.password)

        if not proxy.confluence2.hasUser(token, username):
            user_definition = {
                "email": f"{username}@test.com",
                "fullname": username.capitalize(),
                "name": username,
                "url": self.host + f"/display/~{username}"
            }
            proxy.confluence2.addUser(token, user_definition, password)
            user_definition['password'] = password
            return {'user': {'username': user_definition["name"], 'email': user_definition["email"]}}
        else:
            raise Exception(f"Can't create user {username}: user already exists.")
