import operator
import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import cartopy.feature as cfeature
import json
import pandas as pd
import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg, NavigationToolbar2WxAgg
import urllib.request
from pypinyin import lazy_pinyin
import math

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class Frame_main(wx.Frame):
    def __init__(self):
        super().__init__(None, -1, title='控制窗口', size=(300, 200))
        self.panel = wx.Panel(self, size=(300, 200))
        self.city_list = ['北京', '天津', '石家庄', '呼和浩特', '沈阳', '大连', '长春', '哈尔滨', '上海', '南京', '无锡', '徐州', '常州', '苏州', '杭州',
                          '宁波', '温州', '合肥', '福州', '厦门', '南昌', '济南', '青岛', '武汉', '郑州', '长沙', '广州', '深圳', '佛山', '东莞',
                          '南宁', '重庆', '成都', '贵州', '昆明', '西安', '兰州', '乌鲁木齐', '香港']
        self.selected_city_name, self.selected_city_name_pinyin = '', ''
        self.button_download_data = wx.Button(self.panel, -1, '下载数据')
        self.button_download_data.Bind(wx.EVT_BUTTON, dl_data)
        self.title = wx.StaticText(self.panel, label='地铁路线图', style=wx.ALIGN_CENTER)
        self.title.SetFont(wx.Font(18, wx.DECORATIVE, wx.NORMAL, wx.NORMAL))
        self.input_city_tiptext = wx.StaticText(self.panel, label='城市名：', style=wx.ALIGN_CENTER)
        self.city_list_choice = wx.Choice(self.panel, choices=self.city_list)
        self.city_list_choice.Bind(wx.EVT_CHOICE, self.select_city)
        self.button_set_city = wx.Button(self.panel, -1, '确定')
        self.button_set_city.Bind(wx.EVT_BUTTON, self.enter_city)

        self.box_h1 = wx.BoxSizer()
        self.gridsizer_v = wx.GridSizer(cols=1, rows=3, vgap=10, hgap=5)

        self.box_h1.Add(self.input_city_tiptext, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_h1.Add(self.city_list_choice, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_h1.Add(self.button_set_city, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)

        self.gridsizer_v.AddMany([(self.title, 0, wx.EXPAND), (self.button_download_data, 0, wx.EXPAND),
                                  (self.box_h1, 0, wx.EXPAND)])
        self.panel.SetSizer(self.gridsizer_v)
        self.load_metro_data()  # 加载地铁数据

    def select_city(self, event):  # 更新选中城市名称
        self.selected_city_name = self.city_list_choice.GetStringSelection()
        city_name_pinyin = ''
        for pinyin in lazy_pinyin(self.selected_city_name):
            city_name_pinyin += pinyin
        self.selected_city_name_pinyin = city_name_pinyin
        print(city_name_pinyin)

    def enter_city(self, event):  # 进入城市
        if self.selected_city_name != '':
            lng, lat = 0, 0
            for item_coordinate in coordinate_data:  # 更新坐标
                if item_coordinate['area'] == '' and (
                        item_coordinate['city'] == self.selected_city_name or item_coordinate[
                    'province'] == self.selected_city_name):
                    lat = float(item_coordinate['lat'])
                    lng = float(item_coordinate['lng'])
            enter_city_map(self.selected_city_name, self.selected_city_name_pinyin, lng, lat)

    def load_metro_data(self):
        global city_metro_data
        if os.path.exists('city_metro_data.json'):
            with open('city_metro_data.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.set_load_data_tiptext(True)
        else:
            data = {}
            self.set_load_data_tiptext(False)
        city_metro_data = data

    def set_load_data_tiptext(self, state):
        if state:
            self.button_download_data.SetLabelText('地铁数据加载成功')
        else:
            self.button_download_data.SetLabelText('未找到地铁数据，点击下载数据')


class Frame_control(wx.Frame):  # 控制窗口
    def __init__(self, cityname, city_name_pinyin, lng, lat):
        super().__init__(None, -1, title='控制窗口 ' + cityname, size=(950, 500))
        self.lines_data = {}  # 线路数据
        self.lines_list = []  # 全部线路  用于初始化checklist内选项
        self.stations_list = {}  # 全部站点
        self.routine=[]
        self.extent, self.translation_extent = 0.2, 0.02
        self.cityname, self.city_name_pinyin, self.lng, self.lat = cityname, city_name_pinyin, lng, lat
        self.prepare_city_metro_data()
        self.shp0 = shpreader.Reader('city_border.shp')

        self.panel = wx.Panel(self, size=(700, 500))
        # self.city_name_text = wx.StaticText(self.panel, label=cityname+'市',style=wx.ALIGN_CENTER)
        # self.city_name_text.SetFont(wx.Font(36, wx.DECORATIVE, wx.NORMAL, wx.NORMAL))
        self.button_zoom_up = wx.Button(self.panel, -1, '放大')
        self.button_zoom_up.Bind(wx.EVT_BUTTON, self.zoom_up)
        self.button_zoom_down = wx.Button(self.panel, -1, '缩小')
        self.button_zoom_down.Bind(wx.EVT_BUTTON, self.zoom_down)
        self.button_translation_up = wx.Button(self.panel, -1, '↑')
        self.button_translation_up.Bind(wx.EVT_BUTTON, self.translation_up)
        self.button_translation_down = wx.Button(self.panel, -1, '↓')
        self.button_translation_down.Bind(wx.EVT_BUTTON, self.translation_down)
        self.button_translation_left = wx.Button(self.panel, -1, '←')
        self.button_translation_left.Bind(wx.EVT_BUTTON, self.translation_left)
        self.button_translation_right = wx.Button(self.panel, -1, '→')
        self.button_translation_right.Bind(wx.EVT_BUTTON, self.translation_right)

        self.checklistbox_lines = wx.CheckListBox(self.panel, choices=self.lines_list)
        self.checklistbox_lines.SetCheckedItems(range(0, self.checklistbox_lines.GetCount()))
        self.checklistbox_lines.Bind(wx.EVT_CHECKLISTBOX, self.set_lines)
        self.button_check_all_lines = wx.Button(self.panel, -1, '选中全部线路')
        self.button_check_all_lines.Bind(wx.EVT_BUTTON, self.check_all_lines)
        self.button_clear_checked_lines = wx.Button(self.panel, -1, '清空选中线路')
        self.button_clear_checked_lines.Bind(wx.EVT_BUTTON, self.clear_checked_lines)
        self.grid_check_lines = wx.GridSizer(cols=1, rows=2, vgap=2, hgap=2)
        self.grid_check_lines.AddMany(
            [(self.button_check_all_lines, 0, wx.EXPAND), (self.button_clear_checked_lines, 0, wx.EXPAND)])
        self.box_check_line = wx.BoxSizer()
        self.box_check_line.Add(self.checklistbox_lines, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_check_line.Add(self.grid_check_lines, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)

        self.start_station_text = wx.StaticText(self.panel, label='出发地：')
        self.input_start_station = wx.TextCtrl(self.panel)
        self.destination_station_text = wx.StaticText(self.panel, label='目的地：')
        self.input_destination_station = wx.TextCtrl(self.panel)
        self.route_text = wx.TextCtrl(self.panel,style=wx.TE_MULTILINE)
        self.box_start_station = wx.BoxSizer()
        self.box_start_station.Add(self.start_station_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_start_station.Add(self.input_start_station, proportion=2, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_destination_station = wx.BoxSizer()
        self.box_destination_station.Add(self.destination_station_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_destination_station.Add(self.input_destination_station, proportion=2, flag=wx.EXPAND | wx.ALL,
                                         border=3)

        self.button_search_route = wx.Button(self.panel, -1, '确定')
        self.button_search_route.Bind(wx.EVT_BUTTON, self.search_station)
        self.gridsizer_station = wx.GridSizer(cols=1, rows=3, vgap=10, hgap=5)
        self.gridsizer_station.AddMany(
            [(self.box_start_station, 0, wx.EXPAND), (self.box_destination_station, 0, wx.EXPAND),
             (self.button_search_route, 0, wx.EXPAND)])

        self.figure = plt.figure()
        self.ax = plt.axes(projection=ccrs.PlateCarree())
        # self.ax.coastlines()
        self.ax.set_extent(
            [self.lng - self.extent, self.lng + self.extent, self.lat - self.extent, self.lat + self.extent])
        self.canvas = FigureCanvasWxAgg(self.panel, -1, self.figure)
        # self.toolbar = NavigationToolbar2WxAgg(self.canvas)

        self.box_h = wx.BoxSizer()
        self.gridsizer_v = wx.GridSizer(cols=1, rows=4, vgap=10, hgap=5)

        self.controller_gridsizer = wx.GridSizer(cols=3, rows=2, vgap=10, hgap=5)
        self.controller_gridsizer.AddMany(
            [(self.button_zoom_up, 0, wx.EXPAND), (self.button_translation_up, 0, wx.EXPAND),
             (self.button_zoom_down, 0, wx.EXPAND), (self.button_translation_left, 0, wx.EXPAND),
             (self.button_translation_down, 0, wx.EXPAND), (self.button_translation_right, 0, wx.EXPAND)])

        self.gridsizer_v.AddMany([(self.box_check_line, 0, wx.EXPAND), (self.gridsizer_station, 0, wx.EXPAND),(self.route_text, 0, wx.EXPAND),(self.controller_gridsizer, 0, wx.EXPAND)])
        # self.gridsizer_v.AddMany([(self.box_check_line, 0, wx.EXPAND), (self.gridsizer_station, 0, wx.EXPAND),(self.route_text, 0, wx.EXPAND),(self.controller_gridsizer, 0, wx.EXPAND), (self.toolbar, 0, wx.EXPAND)])

        self.box_h.Add(self.canvas, proportion=3, flag=wx.EXPAND | wx.ALL, border=3)
        self.box_h.Add(self.gridsizer_v, proportion=1, flag=wx.EXPAND | wx.ALL, border=3)
        self.panel.SetSizer(self.box_h)
        self.draw_lines()

    def update_canvas(self):
        self.ax.set_extent(
            [self.lng - self.extent, self.lng + self.extent, self.lat - self.extent, self.lat + self.extent])
        self.canvas.draw()

    def zoom_up(self, event):
        if self.extent - 0.02 > 0.01:
            self.extent -= 0.02
            # self.translation_extent *= 0.8
        # print(self.extent)
        self.update_canvas()

    def zoom_down(self, event):
        self.extent += 0.02
        # self.translation_extent /= 0.8
        # print(self.extent)
        self.update_canvas()

    def translation_up(self, event):
        self.lat += self.translation_extent
        # print(self.lng, self.lat)
        self.update_canvas()

    def translation_down(self, event):
        self.lat -= self.translation_extent
        # print(self.lng, self.lat)
        self.update_canvas()

    def translation_left(self, event):
        self.lng -= self.translation_extent
        # print(self.lng, self.lat)
        self.update_canvas()

    def translation_right(self, event):
        self.lng += self.translation_extent
        # print(self.lng, self.lat)
        self.update_canvas()

    def set_lines(self, event):  # 选中线路
        self.draw_lines()
        self.canvas.draw()

    def clear_checked_lines(self, event):  # 清空选中线路
        self.checklistbox_lines.SetCheckedItems([])
        self.draw_lines()
        self.canvas.draw()

    def check_all_lines(self, event):  # 选中全部线路
        self.checklistbox_lines.SetCheckedItems(range(0, self.checklistbox_lines.GetCount()))
        self.draw_lines()
        self.canvas.draw()

    def draw_lines(self):  # 画线路
        checked_lines = self.checklistbox_lines.GetCheckedStrings()
        for line_name in self.lines_data.keys():
            if line_name in checked_lines:  # 选中线路
                if len(self.lines_data[line_name][3]) == 0:  # 线路plot为空
                    for i in range(0, len(self.lines_data[line_name][2]) - 1):
                        line_plot = []
                        stations = self.lines_data[line_name][2]
                        line_plot.append(plt.plot([float(stations[i][1][0]), float(stations[i + 1][1][0])],
                                                  [float(stations[i][1][1]), float(stations[i + 1][1][1])],
                                                  color='#' + self.lines_data[line_name][0], linewidth=3)[0])
                        line_plot.append(
                            plt.plot(float(stations[i][1][0]), float(stations[i][1][1]), marker='o', color='black',
                                     markersize=5)[0])
                        line_plot.append(
                            plt.plot(float(stations[i][1][0]), float(stations[i][1][1]), marker='o', color='white',
                                     markersize=3)[0])
                        line_plot.append(
                            plt.text(float(stations[i][1][0]), float(stations[i][1][1]), stations[i][0], fontsize=8))
                        if i == len(stations) - 2:  # 最后站点
                            if self.lines_data[line_name][1] == '1':  # 环线
                                print(1)
                                line_plot.append(plt.plot([float(stations[i + 1][1][0]), float(stations[0][1][0])],
                                                          [float(stations[i + 1][1][1]), float(stations[0][1][1])],
                                                          color='#' + self.lines_data[line_name][0], linewidth=3)[0])
                                line_plot.append(
                                    plt.plot(float(stations[0][1][0]), float(stations[0][1][1]), marker='o',
                                             color='black', markersize=5)[0])
                                line_plot.append(
                                    plt.plot(float(stations[0][1][0]), float(stations[0][1][1]), marker='o',
                                             color='white', markersize=3)[0])
                            line_plot.append(
                                plt.plot(float(stations[i + 1][1][0]), float(stations[i + 1][1][1]), marker='o',
                                         color='black', markersize=5)[0])
                            line_plot.append(
                                plt.plot(float(stations[i + 1][1][0]), float(stations[i + 1][1][1]), marker='o',
                                         color='white', markersize=3)[0])
                            line_plot.append(
                                plt.text(float(stations[i + 1][1][0]), float(stations[i + 1][1][1]), stations[i + 1][0],
                                         fontsize=8))
                        self.lines_data[line_name][3].extend(line_plot)
            else:  # 未选中线路
                if len(self.lines_data[line_name][3]) != 0:  # 线路plot不为空
                    for plot_item in self.lines_data[line_name][3]:
                        plot_item.remove()
                    self.lines_data[line_name][3].clear()

    def prepare_city_metro_data(self):  # 加载数据
        global city_metro_data
        self.lines_data = {}  # lines_data{ 线路名 : [颜色，是否环线，站点信息，plot]......}
        self.stations_list = {}  # stations_list{站名:[[经,纬],[线路名,..],[邻接站,..]]}
        for line in city_metro_data[self.city_name_pinyin][
            'l']:  # 站点列表：city_metro_data[cityname_pinyin]['l'][lineno]['st']   ['sl'] 坐标
            stations_in_1line = []  # 每条线路的地铁站集合    #stations_in_1line[ [站名，[经，纬]],[站名，[经，纬]]...... ]
            for station_no in range(0, len(line['st'])):
                station = line['st'][station_no]
                # stations_in_1line
                stations_in_1line.append([station['n'], station['sl'].split(',')])
                # self.stations_list
                if station['n'] not in self.stations_list.keys():
                    self.stations_list[station['n']] = [station['sl'].split(','), [], []]
                # 添加所属线路名
                if line['ln'] not in self.stations_list[station['n']][1]:
                    self.stations_list[station['n']][1].append(line['ln'])
                # 添加邻接站点
                if station_no - 1 >= 0:  # 上一站
                    if line['st'][station_no - 1]['n'] not in self.stations_list[station['n']][2]:
                        self.stations_list[station['n']][2].append(line['st'][station_no - 1]['n'])
                else:
                    if line['lo'] == '1' and line['st'][len(line['st']) - 1]['n'] not in \
                            self.stations_list[station['n']][2]:  # 环线
                        self.stations_list[station['n']][2].append(line['st'][len(line['st']) - 1]['n'])
                if station_no + 1 < len(line['st']):  # 下一站
                    if line['st'][station_no + 1]['n'] not in self.stations_list[station['n']][2]:
                        self.stations_list[station['n']][2].append(line['st'][station_no + 1]['n'])
                else:
                    if line['lo'] == '1' and line['st'][0]['n'] not in self.stations_list[station['n']][2]:  # 环线
                        self.stations_list[station['n']][2].append(line['st'][0]['n'])

            # self.lines_list
            self.lines_list.append(line['ln'])  # 保存线路名
            # self.lines_data
            self.lines_data[line['ln']] = [line['cl'], line['lo'], stations_in_1line, []]

    def search_station(self, event):
        global city_metro_data
        start, destination = self.input_start_station.GetValue(), self.input_destination_station.GetValue()
        if start != '' and destination != '':
            start_coordinator = []
            destination_coordinator = []
            if start in self.stations_list.keys():
                start_coordinator = self.stations_list[start][0]
                if destination in self.stations_list.keys():
                    destination_coordinator = self.stations_list[destination][0]
                print(start_coordinator, destination_coordinator)


        self.route_text.SetValue(A_alogrithm(self.stations_list, start, destination,self.routine))
        self.update_canvas()



def dl_data(event):  # 下载数据
    global city_metro_data
    if city_metro_data == {}:
        citys = [['1100', 'beijing'], ['1200', 'tianjin'], ['1301', 'shijiazhuang'], ['1501', 'huhehaote'],
                 ['2101', 'shenyang'], ['2102', 'dalian'], ['2201', 'changchun'], ['2301', 'haerbin'],
                 ['3100', 'shanghai'],
                 ['3201', 'nanjing'], ['3202', 'wuxi'], ['3203', 'xuzhou'], ['3204', 'changzhou'], ['3205', 'suzhou'],
                 ['3301', 'hangzhou'], ['3302', 'ningbo'], ['3303', 'wenzhou'], ['3401', 'hefei'], ['3501', 'fuzhou'],
                 ['3502', 'xiamen'], ['3601', 'nanchang'], ['3701', 'jinan'], ['3702', 'qingdao'], ['4201', 'wuhan'],
                 ['4101', 'zhengzhou'], ['4301', 'changsha'], ['4401', 'guangzhou'], ['4403', 'shenzhen'],
                 ['4406', 'foshan'], ['4419', 'dongguan'], ['4501', 'nanning'], ['5000', 'chongqing'],
                 ['5101', 'chengdu'],
                 ['5201', 'guizhou'], ['5301', 'kunming'], ['6101', 'xian'], ['6201', 'lanzhou'], ['6501', 'wulumuqi'],
                 ['8100', 'xianggang']]
        data = {}
        for city in citys:
            url = 'http://map.amap.com/service/subway?_1591337090344&srhdata=' + city[0] + '_drw_' + city[1] + '.json'
            html = urllib.request.urlopen(url)
            city_json = json.loads(html.read().decode('utf-8'))
            data[city[1]] = city_json
        with open('city_metro_data.json', 'w') as file:
            json.dump(data, file)
        frame1.set_load_data_tiptext(True)
        city_metro_data = data




def enter_city_map(cityname, city_name_pinyin, lng, lat):
    app = wx.App()
    frame0 = Frame_control(cityname, city_name_pinyin, lng, lat)
    frame0.Center()
    frame0.Show()
    app.MainLoop()


def get_two_station_distance(station_list, station_name1, station_name2):
    lng1 = float(station_list[station_name1][0][0]),
    lat1 = float(station_list[station_name1][0][1]),
    lng2 = float(station_list[station_name2][0][0]),
    lat2 = float(station_list[station_name2][0][1]),
    rad_lng1 = math.radians(lng1[0])
    rad_lat1 = math.radians(lat1[0])
    rad_lng2 = math.radians(lng2[0])
    rad_lat2 = math.radians(lat2[0])
    dlng = rad_lng1 - rad_lng2
    dlat = rad_lat1 - rad_lat2
    distance = 2 * math.asin(math.sqrt(
        math.sin(dlat / 2) ** 2 + math.cos(rad_lat1) * math.cos(rad_lat2) * math.sin(dlng / 2) ** 2)) * 6371
    return distance


class node:
    def __init__(self, station_name, pre_station, g, h,coordinate, near_station):  # g:已走出距离 h:到终点的直线距离 near_station:邻接站点
        self.station_name = station_name
        self.pre_station = pre_station
        self.f = g + h
        self.coordinate=coordinate
        self.near_station = near_station


# 判断是否在open表中，返回位置，若不在返回-1
def inOpen(open, station_name):
    loc = -1
    for i in range(0, len(open)):
        if open[i].station_name == station_name:
            loc = i
            break
    return loc


# 判断是否在closed表中，返回位置，若不在返回-1
def inClosed(closed, station_name):
    loc = -1
    for i in range(0, len(closed)):
        if closed[i].station_name == station_name:
            loc = i
            break
    return loc

def get_line_name(station_list,before_station,next_station):
    return list(set(station_list[before_station][1]).intersection(set(station_list[next_station][1])))

def A_alogrithm(station_list, start_station_name, destination_station_name,routine):
    # 清空route内容
    if len(routine)>0:
        for plot_item in routine:
            plot_item.remove()
        routine.clear()

    open = []  # open表
    closed = []  # closed表
    res = []  # 解路径

    start_node = node(start_station_name, 0, 0,
                      get_two_station_distance(station_list, start_station_name, destination_station_name),
                      station_list[start_station_name][0],
                      station_list[start_station_name][2])
    open.append(start_node)
    while (len(open) > 0):  # open不为空
        nowstation = open.pop(0)  # 弹出首节点
        if nowstation.station_name == destination_station_name:  # 判断是否为目标节点
            res.append(nowstation)  # 加入解路径列表
            pre_node = nowstation.pre_station
            while True:
                res.append(pre_node)
                if pre_node.station_name == start_station_name:  # 初始节点
                    break
                pre_node = pre_node.pre_station
            break

        # 生成所有子节点
        if len(nowstation.near_station) > 0:
            for next_station_name in nowstation.near_station:
                new_node = node(next_station_name, nowstation,
                                get_two_station_distance(station_list, nowstation.station_name, next_station_name),
                                get_two_station_distance(station_list, next_station_name, destination_station_name),
                                station_list[next_station_name][0],
                                station_list[next_station_name][2])
                if inOpen(open, next_station_name) == -1 and inClosed(closed,
                                                                      next_station_name) == -1:  # 不在open和closed列表
                    open.append(new_node)
                elif inOpen(open, next_station_name) != -1:  # 在open列表
                    if new_node.f < open[inOpen(open, next_station_name)].f:  # 记录更短路径
                        open[inOpen(open, next_station_name)].f = new_node.f
                        open[inOpen(open, next_station_name)].pre_station = nowstation
        closed.append(nowstation)  # 加入closed表
        open.sort(key=lambda x: x.f)

    # 输出结果
    res.reverse()
    line_name=''    # 线路名称
    res_route_text=''    # 输出结果
    for i in range(0,len(res)):
        if i <len(res)-1:
            coordinator0 = [res[i].coordinate[0], res[i].coordinate[1]]
            coordinator1 = [res[i + 1].coordinate[0], res[i + 1].coordinate[1]]
            routine.append(plt.plot([float(coordinator0[0]), float(coordinator1[0])],
                                    [float(coordinator0[1]), float(coordinator1[1])], color='red', linewidth=5)[0])
            routine.append(plt.plot(float(coordinator0[0]), float(coordinator0[1]), marker='o', color='black',
                                    markersize=9)[0])
            routine.append(plt.plot(float(coordinator0[0]), float(coordinator0[1]), marker='o', color='red',
                                    markersize=7)[0])
            routine.append(plt.plot(float(coordinator1[0]), float(coordinator1[1]), marker='o',
                                    color='black', markersize=9)[0])
            routine.append(plt.plot(float(coordinator1[0]), float(coordinator1[1]), marker='o', color='red',
                                    markersize=7)[0])
            if not operator.eq(line_name,get_line_name(station_list,res[i].station_name,res[i+1].station_name)):  #线路变化
                line_name=get_line_name(station_list,res[i].station_name,res[i+1].station_name)
                if res_route_text=='':
                    res_route_text+='-----在 '+res[i].station_name+'站 乘坐'
                else:
                    res_route_text +='↓'+res[i].station_name + '\n'
                    res_route_text+='\n-----在 '+res[i].station_name+'站 换乘'
                for item in line_name:
                    res_route_text+=' '+item
                res_route_text+='-----\n'
        res_route_text+='↓'+res[i].station_name+'\n'
        if i==len(res)-1:
            res_route_text += '\n到达目的地 ' + res[i].station_name + '\n'

    return res_route_text

if __name__ == '__main__':
    coordinate_file = open('coordinate_data.json', encoding='utf-8')
    coordinate_data = json.load(coordinate_file)
    city_metro_data = {}  # 地铁数据
    # shp

    app = wx.App()
    frame1 = Frame_main()
    frame1.Center()
    frame1.Show()
    app.MainLoop()
