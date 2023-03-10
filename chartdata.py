import json
try:
    import pandas
    pandas_imported = True
except ImportError:
    pandas_import = False
from constants import constants, BASE_URL
from base import Base


class ChartData:
    """Grab json chartdata and output as pandas DataFrame"""

    @staticmethod
    def get_overview_chartdata(time_period='one_month'):
        """Returns chartdata from overview page
        Args:
            time_period (str): time period
        Returns:
            pandas.core.frame.DataFrame: Fallback to dict if pandas is not imported
        Note:
            Authentication necessary
        """
        time_period = time_period.upper()
        path = f"{BASE_URL}{constants['paths']['CHARTDATA_OVERVIEW']}"
        url = path.format(time_period)
        if Base()._check_time_period(time_period):
            r = Base()._request(url, auth=True)
            if pandas_imported:
                if 'absoluteSeries' in r:
                    data_series = []
                    for serie in r['absoluteSeries']:
                        point = {'timestamp': serie['timestamp']}
                        point.update(serie['performance'])
                        point.pop('decimalPrecision')
                        data_series.append(point)
                return pandas.read_json(json.dumps(data_series))
            return r
        else:
            raise Exception("Invalid time_period!")

    @staticmethod
    def get_distribution_chartdata():
        """Returns values from account distribution pie chart
        Returns:
            pandas.core.frame.DataFrame: Fallback to dict if pandas is not imported
        Note:
            Authentication necessary\n
            Will "unpack" original drilldown
        """
        url = f"{BASE_URL}{constants['paths']['CHARTDATA_DISTRIBUTION']}"
        r = Base()._request(url, auth=True)
        if pandas_imported:
            pie_dict_list = []
            for x in r:
                if x['drilldownSeries']:
                    for drilldown in x['drilldownSeries']:
                        pie_dict_list.append(drilldown)
                else:
                    x.pop('drilldownSeries', None)
                    pie_dict_list.append(x)
            return pandas.read_json(json.dumps(pie_dict_list))
        return r

    @staticmethod
    def get_ticker_chartdata(orderbook_id, **kwargs):
        """Returns chartdata from overview page
        Args:
            orderbook_id (int): Id of ticker
            time_period (str): time period
            chart_type (str): The kind of chartdata to retrieve
                    - area: Data for typical line chart (default)
                    - candlestick: Data for candlestick/ohlc chart
                    - ohlc: Produces same result as candlestick
            chart_resolution (str): resolution of chart
        Returns:
            pandas.core.frame.DataFrame: Fallback to dict if pandas is not imported
        Note:
            Authentication necessary
        """
        chart_type = kwargs.pop('chart_type', 'AREA').upper()
        chart_resolution = kwargs.pop('chart_resolution', 'TEN_MINUTES').upper()
        time_period = kwargs.pop('time_period', 'month').lower()
        assert not kwargs
        url = f"{BASE_URL}{constants['paths']['CHARTDATA_PATH']}"
        p = {
            "orderbookId": orderbook_id,
            "chartType": chart_type,
            "chartResolution": chart_resolution,
            "timePeriod": time_period
            }
        h = {"Content-Type": "application/json"}

        from datetime import datetime
        r = Base()._request(url, params=p, headers=h, method="POST")
        if pandas_imported:
            if 'dataPoints' in r:
                data_series = r['dataPoints']
                for x in data_series:
                    x[0] = datetime.fromtimestamp(x[0]/1000).isoformat()
                df = pandas.read_json(json.dumps(data_series))
                if chart_type == "AREA":
                    df.columns = ['time', 'value']
                else:
                    df.columns = ['time', 'opens', 'highs', 'lows', 'closes']
                return df
        return r