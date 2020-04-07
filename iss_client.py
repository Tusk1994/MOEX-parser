import requests


class MicexISSDataHandler(object):
    """
    Data handler which will be called
    by the ISS client to handle downloaded data.
    """
    def __init__(self, container):
        """
        The handler will have a container to store received data.
        """
        self.data = container()

    def save_data(self, market_data, name_columns, share):
        """
        This handler method should be overridden to perform
        the processing of data returned by the server.
        Name column:
        ["BOARDID", "TRADEDATE", "SHORTNAME", "SECID", "NUMTRADES",
        "VALUE", "OPEN", "LOW", "HIGH", "LEGALCLOSEPRICE", "WAPRICE",
        "CLOSE", "VOLUME", "MARKETPRICE2", "MARKETPRICE3",
        "ADMITTEDQUOTE", "MP2VALTRD", "MARKETPRICE3TRADESVALUE",
        "ADMITTEDVALUE", "WAVAL"]
        """
        pass


class MicexISSClient(object):
    """
    Methods for interacting with the MICEX ISS server.
    """

    def __init__(self, handler, container):
        """
        handler: user's handler class inherited from MicexISSDataHandler
        container: user's container class

        """

        self.handler = handler(container)
        self.requests = {
            'list_share': 'http://iss.moex.com/iss/history/engines/'
                          'stock/markets/shares/boards/tqbr/securities.json?start={0}',
            'history_secs_test': 'http://iss.moex.com/iss/history/engines/'
                                 '{0}/markets/{1}/boards/{2}/securities/{3}.json?from={4}&start={5}'
        }

    def get_history_securities(self, engine, market, board, share):
        """
        Get and parse historical data for current share
        and add with old data
        """

        new_data = []
        data_old, last_data = self.handler.get_old_data(share)

        # start with date +1 if exists
        index = 0 if last_data == 0 else 1
        while True:
            url = self.requests['history_secs_test'].format(engine, market, board, share, last_data, index)
            json_response = requests.get(url)

            data_hist = json_response.json()['history']

            # out if empty data
            if not data_hist['data']:
                break

            close_index = data_hist['columns'].index('CLOSE')

            for row in data_hist['data']:
                # Check not trade date
                if row[close_index] is not None:
                    new_data.append([self.__del_null(i) for i in row])

            index += len(data_hist['data'])

        # get index for column
        name_columns = data_hist['columns']
        data_old.extend(new_data)
        # save data if is not empty
        if data_old:
            self.handler.save_data(data_old, name_columns, share)

        return True

    def list_shares(self, index=0):

        list_shares = []
        while True:
            url = self.requests['list_share'].format(index)
            json_response = requests.get(url)

            data_hist = json_response.json()['history']

            json_cols = data_hist['columns']
            short_name_idx = json_cols.index('SHORTNAME')
            sec_id_idx = json_cols.index('SECID')

            # out if empty data
            if not data_hist['data']:
                break

            for row in data_hist['data']:
                list_shares.append([row[short_name_idx], row[sec_id_idx]])

            index += len(data_hist['data'])

        return list_shares

    def save_list_shares(self):
        """
        Print shares names into file

        :return: file.txt
        """
        with open("list_shares.txt", "w") as output:
            for short_name, sec_id in self.list_shares():
                output.write(f'{short_name} - {sec_id}\n')

        return True

    @staticmethod
    def del_null(field):
        """
        Replace null string with zero
        """
        return 0 if field is None else field

    __del_null = del_null

