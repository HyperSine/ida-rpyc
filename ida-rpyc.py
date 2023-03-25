#!/usr/bin/env python3
from __future__ import annotations

import threading

import idaapi
from PyQt5 import QtWidgets, QtGui

import rpyc
import rpyc.utils.server
import rpyc.utils.authenticators

class IdaRPyCService(rpyc.SlaveService):

    def on_connect(self, conn: rpyc.Connection):
        super().on_connect(conn)

        def _handle_call(self, obj, args, kwargs = ()):
            retval = [None]

            def trampoline():
                retval[0] = obj(*args, **dict(kwargs))
                return 1

            idaapi.execute_sync(trampoline, idaapi.MFF_WRITE)

            return retval[0]

        def _handle_callattr(self, obj, name, args, kwargs = ()):
            obj = self._handle_getattr(obj, name)
            return _handle_call(obj, args, kwargs)

        conn._HANDLERS[rpyc.core.protocol.consts.HANDLE_CALL] = _handle_call
        conn._HANDLERS[rpyc.core.protocol.consts.HANDLE_CALLATTR] = _handle_callattr

    def on_disconnect(self, conn):
        pass

class IdaRPyCPluginForm(idaapi.PluginForm):

    def __init__(self, hostname: str = 'localhost', port: int = 54444):
        super().__init__()

        self._direct_hostname = hostname
        self._direct_port = port

        self._ssl_hostname = hostname
        self._ssl_port = port
        self._ssl_cert = ''
        self._ssl_key = ''

    def OnCreate(self, form):
        self._form_parent = self.FormToPyQtWidget(form)

        self._tab_main = QtWidgets.QTabWidget()
        self._tabpage_direct = QtWidgets.QWidget()
        self._tabpage_ssl = QtWidgets.QWidget()

        self._tab_main.addTab(self._tabpage_direct, 'direct')
        self._tab_main.addTab(self._tabpage_ssl, 'SSL')

        self._edit_direct_hostname = QtWidgets.QLineEdit()
        self._edit_direct_hostname.setText(self._direct_hostname)
        self._edit_direct_hostname.textChanged.connect(self.OnDirectHostnameChange)

        self._edit_direct_port = QtWidgets.QLineEdit()
        self._edit_direct_port.setValidator(QtGui.QIntValidator(1, 65535))
        self._edit_direct_port.setText(str(self._direct_port))
        self._edit_direct_port.textChanged.connect(self.OnDirectPortChange)

        self._edit_ssl_hostname = QtWidgets.QLineEdit()
        self._edit_ssl_hostname.setText(self._ssl_hostname)
        self._edit_ssl_hostname.textChanged.connect(self.OnSslHostnameChange)

        self._edit_ssl_port = QtWidgets.QLineEdit()
        self._edit_ssl_port.setValidator(QtGui.QIntValidator(1, 65535))
        self._edit_ssl_port.setText(str(self._ssl_port))
        self._edit_ssl_port.textChanged.connect(self.OnSslPortChange)

        self._edit_ssl_cert = QtWidgets.QLineEdit()
        self._edit_ssl_cert.setReadOnly(True)
        self._edit_ssl_cert.setText(self._ssl_cert)

        self._edit_ssl_key = QtWidgets.QLineEdit()
        self._edit_ssl_key.setReadOnly(True)
        self._edit_ssl_key.setText(self._ssl_key)

        self._button_ssl_cert = QtWidgets.QPushButton('...')
        self._button_ssl_cert.setStyleSheet('padding: 5px;')
        self._button_ssl_cert.clicked.connect(self.OnSslCertClicked)

        self._button_ssl_key = QtWidgets.QPushButton('...')
        self._button_ssl_key.setStyleSheet('padding: 5px;')
        self._button_ssl_key.clicked.connect(self.OnSslKeyClicked)

        self._button_start_stop_cancel = \
            QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Yes | QtWidgets.QDialogButtonBox.StandardButton.No | QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Yes).setText('Start')
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Yes).clicked.connect(self.OnStartClicked)

        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.No).setText('Stop')
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.No).setEnabled(False)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.No).clicked.connect(self.OnStopClicked)

        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText('Close')
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.OnCloseClicked)

        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel('IDA-RPyC over direct connection.<br><font color=red>DATA ARE TRANSMITTED WITHOUT ENCRYPTION!</font>'))
        layout.addRow('Hostname', self._edit_direct_hostname)
        layout.addRow('Port', self._edit_direct_port)
        self._tabpage_direct.setLayout(layout)

        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel('IDA-RPyC over SSL connection.'))
        layout.addRow('Hostname', self._edit_ssl_hostname)
        layout.addRow('Port', self._edit_ssl_port)

        layout1 = QtWidgets.QHBoxLayout()
        layout1.addWidget(self._edit_ssl_cert)
        layout1.addWidget(self._button_ssl_cert)

        layout2 = QtWidgets.QHBoxLayout()
        layout2.addWidget(self._edit_ssl_key)
        layout2.addWidget(self._button_ssl_key)

        layout.addRow('SSL certificate file', layout1)
        layout.addRow('SSL key file', layout2)
        self._tabpage_ssl.setLayout(layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._tab_main)
        layout.addWidget(self._button_start_stop_cancel)

        self._form_parent.setLayout(layout)

    def OnDirectHostnameChange(self, text: str):
        self._direct_hostname = text

    def OnDirectPortChange(self, text: str):
        self._direct_port = int(text)

    def OnSslHostnameChange(self, text: str):
        self._ssl_hostname = text

    def OnSslPortChange(self, text: str):
        self._ssl_port = int(text)

    def OnSslCertClicked(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self._form_parent, 'Select a SSL certificate file')
        self._ssl_cert = filename
        self._edit_ssl_cert.setText(filename)

    def OnSslKeyClicked(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self._form_parent, 'Select a SSL key file')
        self._ssl_key = filename
        self._edit_ssl_key.setText(filename)

    def OnStartClicked(self):
        if self._tab_main.currentWidget() is self._tabpage_direct:
            self._server = rpyc.utils.server.ThreadedServer(IdaRPyCService, hostname = self._direct_hostname, port = self._direct_port)
            self._server_thread = threading.Thread(target = self._server.start)
            self._server_thread.start()
            print('IDA-RPyC: Server has started with direct mode')
            print('IDA-RPyC: Server is listening at ({}, {})'.format(self._direct_hostname, self._direct_port))
        elif self._tab_main.currentWidget() is self._tabpage_ssl:
            self._server = rpyc.utils.server.ThreadedServer(IdaRPyCService, hostname = self._ssl_hostname, port = self._ssl_port, authenticator = rpyc.utils.authenticators.SSLAuthenticator(self._ssl_key, self._ssl_cert))
            self._server_thread = threading.Thread(target = self._server.start)
            self._server_thread.start()
            print('IDA-RPyC: Server has started with SSL mode')
            print('IDA-RPyC: Server is listening at ({}, {})'.format(self._ssl_hostname, self._ssl_port))
        else:
            raise RuntimeError('Unexpected!')

        self._tab_main.setEnabled(False)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Yes).setEnabled(False)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.No).setEnabled(True)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setEnabled(False)

    def OnStopClicked(self):
        self._server.close()
        self._server_thread.join()

        delattr(self, '_server')
        delattr(self, '_server_thread')

        print('IDA-RPyC: Server has stopped')

        self._tab_main.setEnabled(True)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Yes).setEnabled(True)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.No).setEnabled(False)
        self._button_start_stop_cancel.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setEnabled(True)

    def OnCloseClicked(self):
        self.Close(idaapi.PluginForm.WCLS_DELETE_LATER)

    def OnClose(self, form):
        if hasattr(self, '_server') and hasattr(self, '_server_thread'):
            self._server.close()
            self._server_thread.join()

            delattr(self, '_server')
            delattr(self, '_server_thread')

            print('IDA-RPyC: Server has stopped')

    def ShowFloating(self, caption: str):
        idaapi.plgform_show(self.__clink__, self, caption, idaapi.PluginForm.WOPN_DP_FLOATING)

class IdaRPyCPlugin(idaapi.plugin_t):
    flags = idaapi.PLUGIN_KEEP
    comment = ''
    help = ''
    wanted_name = "IDA-RPyC plugin"
    wanted_hotkey = ''

    def init(self):
        return idaapi.PLUGIN_OK

    def run(self, arg):
        form = IdaRPyCPluginForm()
        form.ShowFloating('IDA-RPyC')

    def term(self):
        pass

def PLUGIN_ENTRY():
    return IdaRPyCPlugin()
