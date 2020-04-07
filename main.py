import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib import dates
import numpy as np
import pandas as pd
from iss_client import *
import json
from pandas.plotting import register_matplotlib_converters
import os
register_matplotlib_converters()


class MyData(object):
    """
    Container that will be used by the handler to store and use data.
    """
    def __init__(self):
        self.name_columns = []
        self.history = {}
        # Checker if already count
        self.check_bollinger = False
        self.name = ''

    def fill_fields(self, market_data):
        """
        Fill DataFrame
        """

        self.history = pd.DataFrame(market_data, columns=self.name_columns)
        self.history['TRADEDATE'] = pd.to_datetime(self.history['TRADEDATE'], format='%Y-%m-%d', errors='ignore')

    def check_share(self):
        """
        Check share on bollinger factor
        :return: bool
        """

        check = False

        self.lines_bollinger()
        # Check last trade day(today)
        try:
            close_price = self.history['CLOSE'].iloc[-1]
            price_upper = self.history['Upper Band'].iloc[-1]
            price_lower = self.history['Lower Band'].iloc[-1]
            if close_price is not None and not all(map(np.isnan, [price_upper, price_lower])):
                if close_price > price_upper or close_price < price_lower:
                    check = True
        except IndexError:
            # If DataFrame is empty
            print(self.name)

        return check

    def lines_bollinger(self):
        """
        Calculate 30 Day Moving Average, Std Deviation,
        Upper Band and Lower Band, 30 Day Moving Volume Average,
        10 Day Moving Volume Average
        """

        if isinstance(self.history, dict):
            print('data is empty')
            raise

        if self.check_bollinger is False:
            self.history['30 Day MA'] = self.history['CLOSE'].rolling(window=20).mean()
            self.history['VOLUME 30 MA'] = self.history['VOLUME'].rolling(window=20).mean()
            self.history['VOLUME 10 MA'] = self.history['VOLUME'].rolling(window=10).mean()
            self.history['30 Day STD'] = self.history['CLOSE'].rolling(window=20).std()
            self.history['Upper Band'] = self.history['30 Day MA'] + (self.history['30 Day STD'] * 2)
            self.history['Lower Band'] = self.history['30 Day MA'] - (self.history['30 Day STD'] * 2)
            self.check_bollinger = True

    def plot_lines_bollinger(self, mode):
        """
        plot lines Bollinder
        """
        index = -40 if mode == 'm' else 0

        self.lines_bollinger()

        plt.style.use('dark_background')
        fig = plt.figure(figsize=(12, 6))
        fig.patch.set_facecolor('black')
        gs = GridSpec(5, 1, figure=fig, hspace=0)

        ax1 = fig.add_subplot(gs[:-1, 0])

        temp_df = self.history[index:]
        # Get dates for the X axis
        x_axis = temp_df['TRADEDATE']

        # Plot shaded Bollinger zones
        ax1.fill_between(x_axis, temp_df['Upper Band'], temp_df['30 Day MA'], color='#fa927a')
        ax1.fill_between(x_axis, temp_df['30 Day MA'], temp_df['Lower Band'], color='#9fc9f5')

        # Plot Adjust Closing Price and Moving Averages
        ax1.plot(x_axis, temp_df['30 Day MA'], color='green', label='30 Day MA')
        ax1.plot(x_axis, temp_df['Upper Band'], color='#c42525')
        ax1.plot(x_axis, temp_df['Lower Band'], color='#2f7ed8')
        ax1.plot(x_axis, temp_df['CLOSE'], color='white', label='CLOSE')

        # Set Title & Show the Image
        ax1.set_title(f'Lines Bollinger for {self.name}')
        ax1.axes.get_xaxis().set_visible(False)
        ax1.set_ylabel('Price(RUB)')
        ax1.legend()

        # move mouse
        if mode == 'm':
            cursor = CursorHover(ax1, x_axis, temp_df['Lower Band'], {i: i._color for i in ax1.get_lines()})
            fig.canvas.mpl_connect('motion_notify_event', cursor.on_plot_hover)

        ax2 = fig.add_subplot(gs[-1:, 0])
        ax2.bar(x_axis, temp_df['VOLUME'], width=0.8)
        ax2.plot(x_axis, temp_df['VOLUME 30 MA'], color='#2f7ed8', label='VOLUME 30 MA')
        ax2.plot(x_axis, temp_df['VOLUME 10 MA'], color='#c42525', label='VOLUME 10 MA')
        ax2.set_ylabel('Shares')
        ax2.set_xlabel('Date')
        ax2.legend()

        plt.show()


class CursorHover(object):
    """
    Hover cursor

    ax: subplot
    x: DataFame
    y: DataFame
    lines: dict
    """
    def __init__(self, ax, x, y, lines):
        self.ax = ax
        self.lines = lines
        # Convert to np.float64
        self.x = x.dt.date.apply(dates.date2num)
        self.y = y
        self.lx = ax.axhline(y=max(y), linestyle='--', color='y')  # the horizontal line
        self.ly = ax.axvline(x=max(x), linestyle='--', color='y',)  # the vertical line
        self.marker, = ax.plot([max(x)], [max(y)], marker="o", color="y", markersize=4, zorder=3)
        # text location in axes coordinates
        self.txt = ax.text(0.4, 0.05, '', transform=ax.transAxes)

    def on_plot_hover(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        index_x = self.x.searchsorted(x)

        # List is filled value each line
        data_each_lines = {}

        try:
            for line, color in self.lines.items():
                data_each_lines[line.get_ydata()[index_x]] = color
        except IndexError:
            # If cursor out of plot
            return

        data_each_lines = sorted(data_each_lines.items(), key=lambda i: i[0])
        value_lines = [i[0] for i in data_each_lines]
        colors = [i[1] for i in data_each_lines]
        # Search nearest index
        index_y = np.searchsorted(value_lines, [y])[0]

        try:
            # Get nearest value
            x = self.x.iloc[index_x]
            y = value_lines[index_y]
            # Update text
            self.txt.set_text(f'{dates.num2date(x, tz=None).date()}, {y:.2f}')
            # Set cross lines
            self.ly.set_xdata(x)
            self.lx.set_ydata(y)
            self.marker.set_data([x], [y])
            # change color for marker according to line
            self.marker.set_color(colors[index_y])
            # Redraw
            self.ax.figure.canvas.draw_idle()
        except IndexError:
            pass


class MyDataHandler(MicexISSDataHandler):
    """
    This handler will be receiving pieces of data from the ISS client.
    """
    def save_data(self, market_data, name_columns, share):
        """
        Save data in json format
        """

        self.data.check_bollinger = False
        self.data.name_columns = name_columns
        self.data.fill_fields(market_data)
        self.data.name = share

        if len(market_data):
            if not os.path.exists('shares'):
                os.makedirs('shares')
            with open(f'shares/{share}.json', 'w') as f:
                json.dump(market_data, f)

    @staticmethod
    def get_old_data(share):
        """
        get old saved data
        return: list, str
        """

        last_date = 0
        data_old = []
        try:
            with open(f'shares/{share}.json', 'r') as data_file:
                data_old = json.load(data_file)
                # Get last date
                last_date = data_old[-1][1]
        except FileNotFoundError:
            pass

        return data_old, last_date


def check_all_shares(client):
    """
    Check all share on Bollinger factor

    :param client: MicexISSClient object
    :return: [str, str]
    """
    list_alert = []
    for short_name, sec_id in client.list_shares()[54:]:
        client.get_history_securities('stock', 'shares', 'tqbr', sec_id)
        if client.handler.data.check_share():
            list_alert.append([short_name, sec_id])

    print(list_alert)


def plot_share(client, share, mode='a'):
    """
    Plot Bollinger's lines

    :param client: MicexISSClient object
    :param share: str
    :param mode: 'a' or 'm'
    """
    client.get_history_securities('stock', 'shares', 'tqbr', share)
    client.handler.data.plot_lines_bollinger(mode)


def main():
    iss = MicexISSClient(MyDataHandler, MyData)
    # check_all_shares(iss)
    # Put your share name without 'ALRS'
    plot_share(iss, 'ALRS', 'a')


if __name__ == '__main__':
    main()
