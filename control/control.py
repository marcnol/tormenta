# -*- coding: utf-8 -*-
"""
Created on Mon Jun 16 18:19:24 2014

@authors: Federico Barabas, Luciano Masullo
"""

import numpy as np
import os
import datetime
import time

from PyQt4 import QtGui, QtCore

import pyqtgraph as pg
import pyqtgraph.ptime as ptime
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.dockarea import Dock, DockArea
from pyqtgraph.console import ConsoleWidget

import h5py as hdf
import tifffile as tiff     # http://www.lfd.uci.edu/~gohlke/pythonlibs/#vlfd
from lantz import Q_

# Tormenta imports
from instruments import Laser, Camera, ScanZ, DAQ
from lasercontrol import LaserWidget
from focus import FocusWidget
from viewboxtools import Grid, Crosshair


# Check for same name conflict
def getUniqueName(name):

    n = 1
    while os.path.exists(name):
        if n > 1:
            name = name.replace('_{}.'.format(n - 1), '_{}.'.format(n))
        else:
            name = insertSuffix(name, '_{}'.format(n))
        n += 1

    return name


def insertSuffix(filename, suffix):
    names = os.path.splitext(filename)
    return names[0] + suffix + names[1]


class RecordingWidget(QtGui.QFrame):

    def __init__(self, main, *args, **kwargs):
        super(RecordingWidget, self).__init__(*args, **kwargs)

        self.main = main
        self.dataname = 'data'      # In case I need a QLineEdit for this
        self.shape = self.main.shape

        recTitle = QtGui.QLabel('<h2><strong>Recording settings</strong></h2>')
        recTitle.setTextFormat(QtCore.Qt.RichText)
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Raised)

        self.currentFrame = QtGui.QLabel('0 /')
        self.numExpositionsEdit = QtGui.QLineEdit('100')
        self.folderEdit = QtGui.QLineEdit(os.getcwd())
        openFolder = QtGui.QPushButton('Open Folder')
        self.filenameEdit = QtGui.QLineEdit('filename')
        self.formatBox = QtGui.QComboBox()
        self.formatBox.addItems(['hdf5', 'tiff'])

        self.snapButton = QtGui.QPushButton('Snap')
        self.snapButton.setEnabled(False)
        self.snapButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                      QtGui.QSizePolicy.Expanding)
        self.snapButton.clicked.connect(self.snap)
        self.recButton = QtGui.QPushButton('REC')
        self.recButton.setCheckable(True)
        self.recButton.setEnabled(False)
        self.recButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                     QtGui.QSizePolicy.Expanding)
        self.recButton.clicked.connect(self.startRecording)

        zeroTime = datetime.timedelta(seconds=0)
        self.tElapsed = QtGui.QLabel('Elapsed: {}'.format(zeroTime))
        self.tRemaining = QtGui.QLabel()
        self.numExpositionsEdit.textChanged.connect(self.nChanged)
        self.updateRemaining()

        recGrid = QtGui.QGridLayout()
        self.setLayout(recGrid)
        recGrid.addWidget(recTitle, 0, 0, 1, 3)
        recGrid.addWidget(QtGui.QLabel('Number of expositions'), 5, 0)
        recGrid.addWidget(self.currentFrame, 5, 1)
        recGrid.addWidget(self.numExpositionsEdit, 5, 2)
        recGrid.addWidget(QtGui.QLabel('Folder'), 1, 0)
        recGrid.addWidget(openFolder, 1, 1, 1, 2)
        recGrid.addWidget(self.folderEdit, 2, 0, 1, 3)
        recGrid.addWidget(QtGui.QLabel('Filename'), 3, 0, 1, 2)
        recGrid.addWidget(self.filenameEdit, 4, 0, 1, 2)
        recGrid.addWidget(self.formatBox, 4, 2)
        recGrid.addWidget(self.snapButton, 1, 3, 2, 1)
        recGrid.addWidget(self.recButton, 3, 3, 4, 1)
        recGrid.addWidget(self.tElapsed, 6, 0)
        recGrid.addWidget(self.tRemaining, 6, 1, 1, 2)

        recGrid.setColumnMinimumWidth(0, 200)

        self._editable = True

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, value):
        self.snapButton.setEnabled(value)
        self.folderEdit.setEnabled(value)
        self.filenameEdit.setEnabled(value)
        self.numExpositionsEdit.setEnabled(value)
        self.formatBox.setEnabled(value)
        self._editable = value

    def nChanged(self):
        self.updateRemaining()
        self.limitExpositions(9)

    def updateRemaining(self):
        rSecs = self.main.t_acc_real.magnitude * self.n()
        rTime = datetime.timedelta(seconds=np.round(rSecs))
        self.tRemaining.setText('Remaining: {}'.format(rTime))

    def nPixels(self):
        return self.shape[0] * self.shape[1]

    def fileSizeGB(self):
        # self.nPixels() * self.nExpositions * 16 / (8 * 1024**3)
        return self.nPixels() * self.n() / 2**29

    # Setting a xGB limit on file sizes to be able to open them in Fiji
    def limitExpositions(self, xGB):
        # nMax = xGB * 8 * 1024**3 / (pixels * 16)
        nMax = xGB * 2**29 / self.nPixels()
        if self.n() > nMax:
            self.numExpositionsEdit.setText(str(np.round(nMax).astype(int)))

    def n(self):
        text = self.numExpositionsEdit.text()
        if text == '':
            return 0
        else:
            return int(text)

    def folder(self):
        return self.folderEdit.text()

    def filename(self):
        return self.filenameEdit.text()

    def saveFormat(self):
        return self.formatBox.currentText()

    def snap(self):

        image = andor.most_recent_image16(self.shape)

        # Data storing
        self.savename = (os.path.join(self.folder(), self.filename()) + '.' +
                         self.format)

        if self.saveFormat() == 'hdf5':
            self.store_file = hdf.File(getUniqueName(self.savename))
            self.store_file.create_dataset(name=self.dataname + '_snap',
                                           data=image)
            self.store_file.close()

        elif self.saveFormat() == 'tiff':
            splitted = os.path.splitext(self.savename)
            snapname = splitted[0] + '_snap' + splitted[1]
            tiff.imsave(getUniqueName(snapname), image,
                        description=self.dataname, software='Tormenta')

    def startRecording(self):

        if self.recButton.isChecked():

            self.editable = False
            self.main.tree.editable = False
            self.main.liveviewButton.setEnabled(False)

            self.savename = (os.path.join(self.folder(), self.filename()) +
                             '.' + self.saveFormat())
            self.savename = getUniqueName(self.savename)

            # Attributes saving
            self.attrs = self.main.tree.attrs()
            self.attrs.extend([('Date', time.strftime("%Y-%m-%d")),
                               ('Start time', time.strftime("%H:%M:%S")),
                              ('element_size_um', (1, 0.133, 0.133))])
#            TODO:
#            self.attrs.append(self.main.lasersWidgets.attrs())

            # Acquisition preparation
            self.main.viewtimer.stop()
            if andor.status != 'Camera is idle, waiting for instructions.':
                andor.abort_acquisition()
            else:
                andor.shutter(0, 1, 0, 0, 0)

            self.iPart = 0
            if self.fileSizeGB() < 2:
                self.chunkMode = False
                self.recordSingle(self.n(), self.savename)
                self.nn = np.zeros(1)

            else:
                self.chunkMode = True

                nn = np.zeros(np.ceil(self.fileSizeGB() / 2))
                nn[:np.floor(self.fileSizeGB() / 2)] = 2
                if nn[-1] == 0:
                    nn[-1] = self.fileSizeGB() - np.sum(nn)
                self.nn = (self.n() * nn / self.fileSizeGB()).astype(int)
                suffix = '_part{}'.format(self.iPart)
                partName = insertSuffix(self.savename, suffix)

                self.recordSingle(self.nn[self.iPart], partName)

    def recordSingle(self, n, name):

        # Frame counter
        self.j = 0

        andor.free_int_mem()
        andor.acquisition_mode = 'Kinetics'
        andor.set_n_kinetics(n)
        andor.start_acquisition()
        time.sleep(np.min((5 * self.main.t_exp_real.magnitude, 1)))

        self.stack = np.zeros((n, self.shape[0], self.shape[1]),
                              dtype=np.uint16)

        self.startTime = ptime.time()
        QtCore.QTimer.singleShot(1, lambda: self.updateWhileRec(n, name))

    def updateWhileRec(self, n, name):

        time.sleep(self.main.t_exp_real.magnitude)
        if andor.n_images_acquired > self.j:
            i, self.j = andor.new_images_index
            self.stack[i - 1:self.j] = andor.images16(i, self.j, self.shape, 1,
                                                      n)
            self.main.img.setImage(np.transpose(self.stack[self.j - 1]),
                                   autoLevels=False)
            if self.main.crosshair.showed:
                xcoord = int(np.round(self.main.crosshair.hLine.pos()[1]))
                ycoord = int(np.round(self.main.crosshair.hLine.pos()[0]))
                self.main.xProfile.setData(self.stack[self.j - 1][xcoord])
                self.main.yProfile.setData(self.stack[self.j - 1][:, ycoord])

            # fps calculation
            self.main.fpsMath()

            # Elapsed and remaining times and frames
            eSecs = np.round(ptime.time() - self.startTime)
            eText = 'Elapsed: {}'.format(datetime.timedelta(seconds=eSecs))
            self.tElapsed.setText(eText)
            nframe = int(self.j + np.sum(self.nn[:self.iPart]))
            rFrames = self.n() - nframe
            rSecs = np.round(self.main.t_acc_real.magnitude * rFrames)
            rText = 'Remaining: {}'.format(datetime.timedelta(seconds=rSecs))
            self.tRemaining.setText(rText)
            self.currentFrame.setText(str(nframe) + ' /')

        if self.j < n and self.recButton.isChecked():
            QtCore.QTimer.singleShot(0, lambda: self.updateWhileRec(n, name))

        else:
            self.endRecording(name)

    def endRecording(self, name):

        if self.saveFormat() == 'hdf5':
            self.store_file = hdf.File(name, "w")
            self.store_file.create_dataset(name=self.dataname,
                                           data=self.stack[0:self.j])
            # Saving parameters
            for item in self.attrs:
                self.store_file[self.dataname].attrs[item[0]] = item[1]

            self.store_file.close()

        elif self.saveFormat() == 'tiff':
            tiff.imsave(name, self.stack[0:self.j], description=self.dataname,
                        software='Tormenta')

        if self.chunkMode and self.iPart + 1 < len(self.nn):
            self.iPart += 1
            suffix = '_part{}'.format(self.iPart)
            partName = insertSuffix(self.savename, suffix)

            self.recordSingle(self.nn[self.iPart], partName)

        else:

            if self.main.focusWidget.focusDataBox.isChecked():
                self.main.focusWidget.exportData()

            else:
                self.main.focusWidget.graph.savedDataSignal = []

            self.recButton.setChecked(False)
            self.editable = True
            self.main.tree.editable = True
            self.main.liveviewButton.setEnabled(True)
            self.main.liveview(update=False)


class TemperatureStabilizer(QtCore.QObject):

    def __init__(self, parameter, *args, **kwargs):

        global andor

        super(TemperatureStabilizer, self).__init__(*args, **kwargs)
        self.parameter = parameter
        self.setPointPar = self.parameter.param('Set point')
        self.setPointPar.sigValueChanged.connect(self.updateTemp)

    def updateTemp(self):
        andor.temperature_setpoint = Q_(self.setPointPar.value(), 'degC')

    def start(self):
        self.updateTemp()
        andor.cooler_on = True
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1)

    def update(self):
        stable = 'Temperature has stabilized at set point.'
        if andor.temperature_status != stable:
            CurrTempPar = self.parameter.param('Current temperature')
            CurrTempPar.setValue(np.round(andor.temperature.magnitude, 1))
            self.parameter.param('Status').setValue(andor.temperature_status)
            time.sleep(10)
        else:
            self.timer.stop()


class CamParamTree(ParameterTree):
    """ Making the ParameterTree for configuration of the camera during imaging
    """

    global andor

    def __init__(self, *args, **kwargs):
        super(CamParamTree, self).__init__(*args, **kwargs)

        # Parameter tree for the camera configuration
        params = [{'name': 'Camera', 'type': 'str',
                   'value': andor.idn.split(',')[0]},
                  {'name': 'Image frame', 'type': 'group', 'children': [
                      {'name': 'Size', 'type': 'list',
                       'values': ['Full chip', '256x256', '128x128', '64x64',
                                  'Custom']},
                      {'name': 'Apply', 'type': 'action'}]},
                  {'name': 'Timings', 'type': 'group', 'children': [
                      {'name': 'Frame Transfer Mode', 'type': 'bool',
                       'value': False},
                      {'name': 'Horizontal readout rate', 'type': 'list',
                       'values': andor.HRRates},
                      {'name': 'Vertical pixel shift', 'type': 'group',
                       'children': [
                           {'name': 'Speed', 'type': 'list',
                            'values': andor.vertSpeeds[::-1],
                            'value':andor.vertSpeeds[1]},
                           {'name': 'Clock voltage amplitude',
                            'type': 'list', 'values': andor.vertAmps}]},
                      {'name': 'Set exposure time', 'type': 'float',
                       'value': 0.1, 'limits': (0,
                                                andor.max_exposure.magnitude),
                       'siPrefix': True, 'suffix': 's'},
                      {'name': 'Real exposure time', 'type': 'float',
                       'value': 0, 'readonly': True, 'siPrefix': True,
                       'suffix': 's'},
                      {'name': 'Real accumulation time', 'type': 'float',
                       'value': 0, 'readonly': True, 'siPrefix': True,
                       'suffix': 's'},
                      {'name': 'Effective frame rate', 'type': 'float',
                       'value': 0, 'readonly': True, 'siPrefix': True,
                       'suffix': 'Hz'}]},
                  {'name': 'Gain', 'type': 'group', 'children': [
                      {'name': 'Pre-amp gain', 'type': 'list',
                       'values': list(andor.PreAmps)},
                      {'name': 'EM gain', 'type': 'int', 'value': 1,
                       'limits': (0, andor.EM_gain_range[1])}]},
                  {'name': 'Temperature', 'type': 'group', 'children': [
                      {'name': 'Set point', 'type': 'int', 'value': -50,
                       'suffix': 'º', 'limits': (-80, 0)},
                      {'name': 'Current temperature', 'type': 'int',
                       'value': andor.temperature.magnitude, 'suffix': 'ºC',
                       'readonly': True},
                      {'name': 'Status', 'type': 'str', 'readonly': True,
                       'value': andor.temperature_status}]}]

        self.p = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.p, showTop=False)
        self._editable = True

        self.p.param('Image frame').param('Size')

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, value):
        self._editable = value
        value = not(value)
        self.p.param('Image frame').param('Size').setReadonly(value)
        timeParams = self.p.param('Timings')
        timeParams.param('Frame Transfer Mode').setReadonly(value)
        timeParams.param('Horizontal readout rate').setReadonly(value)
        timeParams.param('Set exposure time').setReadonly(value)
        vpsParams = timeParams.param('Vertical pixel shift')
        vpsParams.param('Speed').setReadonly(True)
        vpsParams.param('Clock voltage amplitude').setReadonly(value)
        gainParams = self.p.param('Gain')
        gainParams.param('Pre-amp gain').setReadonly(value)
        gainParams.param('EM gain').setReadonly(value)

    def attrs(self):
        attrs = []
        for ParName in self.p.getValues():
            Par = self.p.param(str(ParName))
            if not(Par.hasChildren()):
                attrs.append((str(ParName), Par.value()))
            else:
                for sParName in Par.getValues():
                    sPar = Par.param(str(sParName))
                    if sPar.type() != 'action':
                        if not(sPar.hasChildren()):
                            attrs.append((str(sParName), sPar.value()))
                        else:
                            for ssParName in sPar.getValues():
                                ssPar = sPar.param(str(ssParName))
                                attrs.append((str(ssParName), ssPar.value()))
        return attrs


class TormentaGUI(QtGui.QMainWindow):

    def __init__(self, *args, **kwargs):

        global andor
        self.shape = andor.detector_shape

        super(TormentaGUI, self).__init__(*args, **kwargs)
        self.setWindowTitle('Tormenta')
        self.cwidget = QtGui.QWidget()
        self.setCentralWidget(self.cwidget)

        self.s = Q_(1, 's')
        self.lastTime = ptime.time()
        self.fps = None

        self.tree = CamParamTree()

        # Frame signals
        frameParam = self.tree.p.param('Image frame')
        frameParam.param('Size').sigValueChanged.connect(self.updateFrame)

        # Exposition signals
        changeExposure = lambda: self.changeParameter(self.setExposure)
        TimingsPar = self.tree.p.param('Timings')
        self.ExpPar = TimingsPar.param('Set exposure time')
        self.ExpPar.sigValueChanged.connect(changeExposure)
        self.FTMPar = TimingsPar.param('Frame Transfer Mode')
        self.FTMPar.sigValueChanged.connect(changeExposure)
        self.HRRatePar = TimingsPar.param('Horizontal readout rate')
        self.HRRatePar.sigValueChanged.connect(changeExposure)
        vertShiftPar = TimingsPar.param('Vertical pixel shift')
        self.vertShiftSpeedPar = vertShiftPar.param('Speed')
        self.vertShiftSpeedPar.sigValueChanged.connect(changeExposure)
        self.vertShiftAmpPar = vertShiftPar.param('Clock voltage amplitude')
        self.vertShiftAmpPar.sigValueChanged.connect(changeExposure)
        changeExposure()    # Set default values

        # Gain signals
        self.PreGainPar = self.tree.p.param('Gain').param('Pre-amp gain')
        updateGain = lambda: self.changeParameter(self.setGain)
        self.PreGainPar.sigValueChanged.connect(updateGain)
        self.GainPar = self.tree.p.param('Gain').param('EM gain')
        self.GainPar.sigValueChanged.connect(updateGain)
        updateGain()        # Set default values

        # Image Widget
        self.fpsBox = QtGui.QLabel()
        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)
        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)

        # HistogramLUT
        self.hist = pg.HistogramLUTItem()
        self.hist.gradient.loadPreset('yellowy')
        self.hist.setImageItem(self.img)
#        self.hist.plot.setLogMode(False, True)  # this breakes the LUT update
        self.hist.vb.setLimits(yMin=0, yMax=20000)
        imageWidget.addItem(self.hist, row=1, col=2)

        # x and y profiles
        xPlot = imageWidget.addPlot(row=0, col=1)
        xPlot.hideAxis('left')
        xPlot.hideAxis('bottom')
        self.xProfile = xPlot.plot()
        imageWidget.ci.layout.setRowMaximumHeight(0, 40)
        xPlot.setXLink(self.vb)
        yPlot = imageWidget.addPlot(row=1, col=0)
        yPlot.hideAxis('left')
        yPlot.hideAxis('bottom')
        self.yProfile = yPlot.plot()
        self.yProfile.rotate(90)
        imageWidget.ci.layout.setColumnMaximumWidth(0, 40)
        yPlot.setYLink(self.vb)

        # viewBox tools
        self.gridButton = QtGui.QPushButton('Grid')
        self.gridButton.setCheckable(True)
        self.grid = Grid(self.vb, self.shape)
        self.gridButton.clicked.connect(self.grid.toggle)
        self.crosshairButton = QtGui.QPushButton('Crosshair')
        self.crosshairButton.setCheckable(True)
        self.crosshair = Crosshair(self.vb)
        self.crosshairButton.clicked.connect(self.crosshair.toggle)

        # Initial camera configuration taken from the parameter tree
        self.shape = andor.detector_shape
        andor.set_exposure_time(self.ExpPar.value() * self.s)
        self.adjustFrame()

        # Liveview functionality
        self.liveviewButton = QtGui.QPushButton('Liveview')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                          QtGui.QSizePolicy.Expanding)
        self.liveviewButton.clicked.connect(self.liveview)
        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.updateView)

        # Temperature stabilization functionality
        self.TempPar = self.tree.p.param('Temperature')
        self.stabilizer = TemperatureStabilizer(self.TempPar)
        self.stabilizerThread = QtCore.QThread()
        self.stabilizer.moveToThread(self.stabilizerThread)
        self.stabilizerThread.started.connect(self.stabilizer.start)
        self.stabilizerThread.start()

        self.recWidget = RecordingWidget(self)

        dockArea = DockArea()

        consoleDock = Dock("Console", size=(600, 200))
        console = ConsoleWidget(namespace={'pg': pg, 'np': np})
        consoleDock.addWidget(console)
        dockArea.addDock(consoleDock)

        wheelDock = Dock("Emission filters", size=(20, 20))
        tableWidget = pg.TableWidget(sortable=False)
        data = np.array([('ZET642NF',    'Notch 642nm',     4, ''),
                         ('ET700/75m',   'Bandpass 700/75', 5, 'Alexa647, '
                                                               'Atto655'),
                         ('FF01-593/40', 'Bandpass 593/40', 6, 'Atto565'),
                         ('ET575/50',    'Bandpass 575/50', 1, 'Atto550'),
                         ('FF03-525/50', 'Bandpass 525/50', 2, 'GFP'),
                         ('',            '',                3, '')],
                        dtype=[('Filtro', object), ('Descripción', object),
                               ('Antiposición', int),
                               ('Fluorósforos', object)])
        tableWidget.setData(data)
        wheelDock.addWidget(tableWidget)
        dockArea.addDock(wheelDock, 'top', consoleDock)

        focusDock = Dock("Focus Control", size=(1, 1))
        self.focusWidget = FocusWidget(DAQ, scanZ, self.recWidget)
        focusDock.addWidget(self.focusWidget)
        dockArea.addDock(focusDock, 'above', wheelDock)

        laserDock = Dock("Laser Control", size=(1, 1))
        self.laserWidgets = LaserWidget((redlaser, bluelaser, greenlaser))
        laserDock.addWidget(self.laserWidgets)
        dockArea.addDock(laserDock, 'above', focusDock)

        # Widgets' layout
        layout = QtGui.QGridLayout()
        self.cwidget.setLayout(layout)
        layout.setColumnMinimumWidth(0, 380)
        layout.setColumnMinimumWidth(1, 600)
        layout.setColumnMinimumWidth(2, 200)
        layout.setRowMinimumHeight(0, 220)
        layout.setRowMinimumHeight(1, 550)
        layout.setRowMinimumHeight(2, 20)
        layout.setRowMinimumHeight(3, 180)
        layout.setRowMinimumHeight(4, 20)
        layout.addWidget(self.tree, 0, 0, 2, 1)
        layout.addWidget(self.liveviewButton, 2, 0)
        layout.addWidget(self.recWidget, 3, 0, 2, 1)
        layout.addWidget(imageWidget, 0, 1, 4, 4)
        layout.addWidget(self.fpsBox, 4, 1)
        layout.addWidget(self.gridButton, 4, 3)
        layout.addWidget(self.crosshairButton, 4, 4)
        layout.addWidget(dockArea, 0, 5, 5, 1)

    def changeParameter(self, function):
        """ This method is used to change those camera properties that need
        the camera to be idle to be able to be adjusted.
        """
        status = andor.status
        if status != ('Camera is idle, waiting for instructions.'):
            self.viewtimer.stop()
            andor.abort_acquisition()

        function()

        if status != ('Camera is idle, waiting for instructions.'):
            andor.start_acquisition()
            time.sleep(np.min((5 * self.t_exp_real.magnitude, 1)))
            self.viewtimer.start(0)

    def setGain(self):
        """ Method to change the pre-amp gain and main gain of the EMCCD
        """
        PreAmpGain = self.PreGainPar.value()
        n = np.where(andor.PreAmps == PreAmpGain)[0][0]
        andor.preamp = n
        andor.EM_gain = self.GainPar.value()

    def setExposure(self):
        """ Method to change the exposure time setting
        """
        andor.set_exposure_time(self.ExpPar.value() * self.s)
        andor.frame_transfer_mode = self.FTMPar.value()
        n_hrr = np.where(np.array([item.magnitude for item in andor.HRRates])
                         == self.HRRatePar.value().magnitude)[0][0]
        andor.horiz_shift_speed = n_hrr

        n_vss = np.where(np.array([item.magnitude
                                  for item in andor.vertSpeeds])
                         == self.vertShiftSpeedPar.value().magnitude)[0][0]
        andor.vert_shift_speed = n_vss

        n_vsa = np.where(np.array(andor.vertAmps) ==
                         self.vertShiftAmpPar.value())[0][0]
        andor.set_vert_clock(n_vsa)

        self.updateTimings()

    def adjustFrame(self, shape=None, start=(1, 1)):
        """ Method to change the area of the CCD to be used and adjust the
        image widget accordingly.
        """
        if shape is None:
            shape = self.shape

        andor.set_image(shape=shape, p_0=start)
        self.vb.setLimits(xMin=-0.5, xMax=shape[0] - 0.5,
                          yMin=-0.5, yMax=shape[1] - 0.5,
                          minXRange=4, minYRange=4)

        self.updateTimings()

    def updateFrame(self):
        """ Method to change the image frame size and position in the sensor
        """
        frameParam = self.tree.p.param('Image frame')
        if frameParam.param('Size').value() == 'Custom':

            self.ROI = pg.ROI((0.5 * self.shape[0] - 64,
                               0.5 * self.shape[1] - 64),
                              size=(128, 128), scaleSnap=True,
                              translateSnap=True, pen='y')
            self.ROI.addScaleHandle((1, 0), (0, 1), lockAspect=True)
            self.vb.addItem(self.ROI)

            # Signals
            applyParam = frameParam.param('Apply')
            applyParam.sigStateChanged.connect(self.customFrame)

        elif frameParam.param('Size').value() == 'Full chip':
            self.shape = andor.detector_shape
            self.changeParameter(self.adjustFrame)

        else:
            side = int(frameParam.param('Size').value().split('x')[0])
            start = (int(0.5 * (andor.detector_shape[0] - side)),
                     int(0.5 * (andor.detector_shape[1] - side)))
            self.shape = (side, side)
            self.changeParameter(lambda: self.adjustFrame(self.shape, start))

        self.grid.update(self.shape)

    def customFrame(self):

        ROISize = self.ROI.size()
        self.shape = (int(ROISize[0]), int(ROISize[1]))
        startROI = self.ROI.pos()
        startROI = (int(startROI[0]), int(startROI[1]))

        self.changeParameter(lambda: self.adjustFrame(self.shape, startROI))
        self.ROI.hide()
        self.grid.update(self.shape)

    def updateTimings(self):
        """ Update the real exposition and accumulation times in the parameter
        tree.
        """
        timings = andor.acquisition_timings
        self.t_exp_real, self.t_acc_real, self.t_kin_real = timings
        timingsPar = self.tree.p.param('Timings')
        RealExpPar = timingsPar.param('Real exposure time')
        RealAccPar = timingsPar.param('Real accumulation time')
        EffFRPar = timingsPar.param('Effective frame rate')
        RealExpPar.setValue(self.t_exp_real.magnitude)
        RealAccPar.setValue(self.t_acc_real.magnitude)
        EffFRPar.setValue(1 / self.t_acc_real.magnitude)

    def liveview(self, update=True):
        """ Image live view when not recording
        """
        if self.liveviewButton.isChecked():
            if andor.status != 'Camera is idle, waiting for instructions.':
                andor.abort_acquisition()

            andor.acquisition_mode = 'Run till abort'
            andor.shutter(0, 1, 0, 0, 0)

            andor.start_acquisition()
            time.sleep(np.min((5 * self.t_exp_real.magnitude, 1)))
            self.recWidget.snapButton.setEnabled(True)
            self.recWidget.recButton.setEnabled(True)

            # Initial image
            image = andor.most_recent_image16(self.shape)
            self.img.setImage(image, autoLevels=False)
            if update:
                self.hist.setLevels(np.min(image) - np.std(image),
                                    np.max(image) + np.std(image))

            self.viewtimer.start(0)

        else:
            self.viewtimer.stop()

            # Turn off camera, close shutter
            if andor.status != 'Camera is idle, waiting for instructions.':
                andor.abort_acquisition()

            andor.shutter(0, 2, 0, 0, 0)
            self.img.setImage(np.zeros(self.shape), autoLevels=False)

    def updateView(self):
        """ Image update while in Liveview mode
        """
        try:
            image = andor.most_recent_image16(self.shape)
            self.img.setImage(np.transpose(image), autoLevels=False)

            if self.crosshair.showed:
                xcoord = int(np.round(self.crosshair.hLine.pos()[1]))
                ycoord = int(np.round(self.crosshair.hLine.pos()[0]))
                self.xProfile.setData(image[xcoord])
                self.yProfile.setData(image[:, ycoord])

            self.fpsMath()

        except:
            pass

    def fpsMath(self):
        now = ptime.time()
        dt = now - self.lastTime
        self.lastTime = now
        if self.fps is None:
            self.fps = 1.0/dt
        else:
            s = np.clip(dt * 3., 0, 1)
            self.fps = self.fps * (1 - s) + (1.0/dt) * s
        self.fpsBox.setText('%0.2f fps' % self.fps)

    def closeEvent(self, *args, **kwargs):

        # Stop running threads
        self.viewtimer.stop()
        self.stabilizer.timer.stop()
        self.stabilizerThread.terminate()

        # Turn off camera, close shutter
        if andor.status != 'Camera is idle, waiting for instructions.':
            andor.abort_acquisition()
        andor.shutter(0, 2, 0, 0, 0)

        self.laserWidgets.closeEvent(*args, **kwargs)
        self.focusWidget.closeEvent(*args, **kwargs)
        super(TormentaGUI, self).closeEvent(*args, **kwargs)


if __name__ == '__main__':

    app = QtGui.QApplication([])

    with Camera('andor.ccd.CCD') as andor, \
            Laser('mpb.vfl.VFL', 'COM11') as redlaser, \
            Laser('cobolt.cobolt0601.Cobolt0601', 'COM4') as bluelaser, \
            Laser('laserquantum.ventus.Ventus', 'COM10') as greenlaser, \
            DAQ() as DAQ, ScanZ(12) as scanZ:

        print(andor.idn)
        print(redlaser.idn)
        print(bluelaser.idn)
        print(greenlaser.idn)
        print(DAQ.idn)
        print('Prior Z stage')

        win = TormentaGUI()
        win.show()

        app.exec_()
