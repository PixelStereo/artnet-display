#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a universe groupbox that display universe attributes and DMX values
"""

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from PyQt5.QtWidgets import QGroupBox, QGridLayout, QTableView, QSpinBox, QLabel, QLineEdit, \
                            QPushButton, QMenu, QHeaderView, QRadioButton
from PyQt5.QtGui import QColor, QBrush, QFont

debug = 1

class UniverseModel(QAbstractTableModel):
    """
    Table Model of a DMX universe (512 values 0/255)
    """
    def __init__(self, parent):
        super(UniverseModel, self).__init__(parent)
        # define the proportion of the table
        self.columns = 32
        self.rows = (512/self.columns)
        if int(self.rows)*self.columns < 512:
            self.rows = self.rows + 1
        # initialize the list of 512 values
        self.dmx_list = []
        for row in range(self.rows):
            # set each list item at 0 to be sure index exists
            # we can do this because we are sure that a universe has a constant length
            self.dmx_list.append([0 for i in range(self.columns)])
            # check to know if the last line will be full or not
            if self.rows-1 == row:
                delta = self.columns * self.rows
                delta = delta - 512
                delta = self.columns - delta
                self.dmx_list[row] = self.dmx_list[row][:delta]
        # main window object is need here to access to ola signal
        self.parent = parent

    def rowCount(self, index=QModelIndex()):
        """
        return the number of rows of the table
        """
        return self.rows

    def columnCount(self, index=QModelIndex()):
        """
        return the number of columns of the table
        """
        return self.columns

    def data(self, index, role=Qt.DisplayRole):
        """
        return value for an index
        """
        rows = index.row()
        columns = index.column()
        index_number = rows - 1
        index_number = index_number * columns
        index_number = index_number + columns
        if index.isValid():
            if role == Qt.DisplayRole:
                try:
                    value = self.dmx_list[rows][columns]
                    if value == 255:
                        value = 'FF'
                    elif value == 0:
                        value = ''
                    return QVariant(value)
                except IndexError:
                    if debug:
                        # these cells does not exists
                        print(rows,columns,'is out of dmx_list')
            elif role == Qt.BackgroundRole:
                try:
                    value =  self.dmx_list[rows][columns]
                    green = 255 - value
                    color = QColor(green,255,green)
                    return QBrush(color)
                except IndexError:
                    # these cells does not exists
                    return QVariant()
            elif role == Qt.FontRole:
                try:
                    font = QFont()
                    font.setFamily('Helvetica')
                    #font.setStretch('UltraCondensed')
                    font.setFixedPitch(True)
                    font.setPointSize(10)
                    return font
                except:
                    return QVariant()
            else:
                return QVariant()
        else:
            return QVariant()


    def new_frame(self, RequestStatus, universe, data):
        """
        receive the dmx_list when ola sends new data
        """
        if debug:
            print 'refresh universe', universe
            print 'new frame received :', len(data), data
        # if data: does not work because the data list can be empty when fetching DMX
        if data != None:
            for index,value in enumerate(data):
                column = index%self.columnCount()
                row = int(index/self.columnCount())
                self.dmx_list[row][column] = value
                self.model_index = self.index(row, column)
                if value != self.model_index.data:
                    # yes : value has changed
                    self.setData(self.model_index, value)
                else:
                    pass
            # if value is 0, OLA does not send the value
            if len(data) < 512:
                for index in range(len(data),512):
                    column = index%self.columns
                    row = int(index/self.columns)
                    self.dmx_list[row][column] = 0
                    self.model_index = self.index(row, column)
                    if self.model_index.data != 0:
                        self.setData(self.model_index, 0)
            # this is send only once for a dmx_list
            # This is where the update is send to the GUI
            self.parent.ola.universeChanged.emit()


class Universe(QGroupBox):
    """
    Handle Universe and display its attributes
    Only one is created and display universe_selected attributes
    """
    def __init__(self, parent):
        super(Universe, self).__init__()
        # make it available for the whole instance
        self.ola = parent.ola
        # intialize variable used in ola_connect method
        self.old = None
        # Create universe attributes
        self.create_attributes()
        # Create the view to display values
        self.create_tableview()
        # Add the previous UI stuffs to a layout
        grid = self.create_layout()
        self.setLayout(grid)
        parent.vbox.addWidget(self)
        self.parent = parent

    def create_attributes(self):
        """
        create attributes widget for the universe
        """
        self.id_label = QLabel('Universe ID')
        self.id = QSpinBox()
        self.name_label = QLabel('Name')
        self.name = QLineEdit()
        self.name.textEdited.connect(self.edit_name)
        self.name.setFixedWidth(200)
        self.merge_mode_label = QLabel('Merge Mode')
        self.merge_mode_htp_label = QLabel('HTP')
        self.merge_mode_htp = QRadioButton()
        self.merge_mode_ltp_label = QLabel('LTP')
        self.merge_mode_ltp = QRadioButton()
        self.inputs = QPushButton('Inputs')
        self.outputs = QPushButton('Outputs')
        self.inputsMenu = QMenu()
        self.outputsMenu = QMenu()
        self.inputs.setMenu(self.inputsMenu)
        self.outputs.setMenu(self.outputsMenu)

    def edit_name(self, name):
        if self.ola.client.SetUniverseName(self.universe_selected.id, name):
            print self.parent
            self.parent.universes_refresh()
        else:
            self.parent.status("edit failed")
            if debug:
                "edit universe name failed"

    def create_tableview(self):
        """
        create the table view for DMX values
        """
        self.view = QTableView()
        self.model = UniverseModel(self)
        self.view.setModel(self.model)
        # set up headers of the QTableView
        v_headers = QHeaderView(Qt.Vertical)
        self.view.setVerticalHeader(v_headers)
        h_headers = QHeaderView(Qt.Horizontal)
        self.view.setHorizontalHeader(h_headers)
        if debug : 
            print 'how many lines : ', v_headers.count()
            print 'how many columns : ', h_headers.count()
        # set up rows and columns
        for col in range(self.model.columnCount()):
            self.view.setColumnWidth(col, 28)
        for row in range(self.model.rowCount()):
            self.view.setRowHeight(row, 20)

    def create_layout(self):
        """
        create the layout for the universe display
        """
        grid = QGridLayout()
        grid.addWidget(self.id, 0, 0, 1, 1)
        grid.addWidget(self.name, 0, 1, 1, 1)
        grid.addWidget(self.merge_mode_htp_label, 0, 2, 1, 1)
        grid.addWidget(self.merge_mode_htp, 0, 3, 1, 1)
        grid.addWidget(self.merge_mode_ltp_label, 0, 4, 1, 1)
        grid.addWidget(self.merge_mode_ltp, 0, 5, 1, 1)
        grid.addWidget(self.inputs, 0, 7, 1, 1)
        grid.addWidget(self.outputs, 0, 9, 1, 1)
        grid.addWidget(self.view,1, 0, 15, 10)
        return grid

    def selection_changed(self, universe):
        """
        universe selected has just changed
        disconnect old universe from ola dmx_frame update
        and connect the new universe
        """
        if self.ola.client:
            if universe.id != self.old:
                if self.old:
                    # unregister the previous universe (self.old)
                    if debug:
                        print 'disconnect universe :', self.old
                    self.ola.client.RegisterUniverse(self.old, self.ola.client.UNREGISTER, self.model.new_frame)
                # register the selected universe (new)
                # ask about universe values, in case no new frame is sent
                if debug:
                    print 'connect universe :', universe.id
                self.ola.client.RegisterUniverse(universe.id, self.ola.client.REGISTER, self.model.new_frame)
                self.ola.universeChanged.connect(self.model.layoutChanged.emit)
                self.ola.client.FetchDmx(universe.id, self.model.new_frame)
                self.display_attributes(universe)
                self.display_ports(universe)
                self.old = universe.id
                self.universe_selected = universe
                return True
            else:
                # ola wants to connect again to the universe it's already binding to
                if debug:
                    print 'universe already connected'
                return False
        else:
            return False

    def display_ports(self, universe):
        """display ports"""
        self.ola.client.GetCandidatePorts(self.GetCandidatePortsCallback, universe.id)

    def GetCandidatePortsCallback(self, status, devices):
        """
        Function that fill-in universe menus with candidate devices/ports
        We need to make menus checkable to be able to patch ports
        """
        if status.Succeeded():
            for device in devices:
                print('Device {d.alias}: {d.name}'.format(d=device))

                print('Candidate input ports:')
                for port in device.input_ports:
                    s = '  port {p.id}, {p.description}, supports RDM: ' \
                        '{p.supports_rdm}'
                    print(s.format(p=port))

                    print('Candidate output ports:')
                for port in device.output_ports:
                    s = '  port {p.id}, {p.description}, supports RDM: ' \
                        '{p.supports_rdm}'
                    print(s.format(p=port))
        else:
            print('Error: ' % status.message)

    def display_attributes(self, universe):
        """
        display universe attributes
        """
        self.id.setValue(universe.id)
        self.name.setText(universe.name)
        if universe.merge_mode == 1:
            self.merge_mode_htp.setChecked(True)
            self.merge_mode_ltp.setChecked(False)
        else:
            self.merge_mode_htp.setChecked(False)
            self.merge_mode_ltp.setChecked(True)
