import os
os.environ["KIVY_NO_ARGS"] = "1"

import logging
import threading
import requests

logger = logging.getLogger(__name__)

try:
    import kivy
    from kivy.app import App
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.recycleview import RecycleView
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.popup import Popup
    from kivy.clock import Clock
    from kivy.lang import Builder
    from kivy.properties import BooleanProperty
    from kivy.uix.recycleview.views import RecycleDataViewBehavior
    from kivy.uix.recycleboxlayout import RecycleBoxLayout
    from kivy.uix.behaviors import FocusBehavior
    from kivy.uix.recycleview.layout import LayoutSelectionBehavior
    from kivy.uix.floatlayout import FloatLayout
    from kivy.factory import Factory
    from kivy.properties import ObjectProperty
    from kivy.uix.image import AsyncImage
    from .utils import OrderedRawConfigParser, extract_firmware_file_from_dfu, extract_params_from_config_file
    from pylinkit import Tracker, Scanner
    KIVY_AVAILABLE = True
except ImportError:
    KIVY_AVAILABLE = False


def run():
    if not KIVY_AVAILABLE:
        print("Error: Kivy is not installed. Install it with: pip install pylinkit[gui]")
        raise SystemExit(1)
    GUIApp().run()


def write_csv(file, data):
    file.write(data)


def save_system_log(tracker, filename):
    with open(filename, 'w') as f:
        write_csv(f, tracker.dumpd('system'))
        f.close()


def save_params(filename, data):
    with open(filename, 'w') as f:
        d = {}
        d['PARAM'] = data
        cfg = OrderedRawConfigParser()
        cfg.optionxform = lambda option: option
        cfg.read_dict(dictionary=d)
        cfg.write(f)
        f.close()


class AsyncOperation(threading.Thread):
    def __init__(self, method, on_result, *args, **kwargs):
        super().__init__()
        self.daemon = True
        self._method = method
        self._args = args
        self._kwargs = kwargs
        self._on_result = on_result
        self.start()

    def run(self):
        try:
            self._on_result(self._method(*self._args, **self._kwargs))
        except Exception as e:
            self._on_result(e)


class AsyncScanner(AsyncOperation):
    def __init__(self, on_result):
        super().__init__(Scanner().scan, on_result)


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class SelectableLabel(RecycleDataViewBehavior, Label):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            #print("selection changed to {0}".format(rv.data[index]))
            rv._selected = index
        else:
            #print("selection removed for {0}".format(rv.data[index]))
            rv._selected = None


Builder.load_string('''
<SelectableLabel>:
    # Draw a background to indicate selection
    canvas.before:
        Color:
            rgba: (.0, 0.9, .1, .3) if self.selected else (0, 0, 0, 1)
        Rectangle:
            pos: self.pos
            size: self.size
<DeviceSelector>:
    viewclass: 'SelectableLabel'
    SelectableRecycleBoxLayout:
        default_size: None, dp(18)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        multiselect: False
        touch_multiselect: False
''')
class DeviceSelector(RecycleView):
    def __init__(self, result):
        super().__init__()
        self._selected = None
        self.data = [{'text': x.address} for x in result]

    def get_selected(self):
        return self.data[self._selected]['text'] if self._selected is not None else None


Builder.load_string('''
<SelectableLabel>:
    # Draw a background to indicate selection
    canvas.before:
        Color:
            rgba: (.0, 0.9, .1, .3) if self.selected else (0, 0, 0, 1)
        Rectangle:
            pos: self.pos
            size: self.size
<DeviceConfig>:
    viewclass: 'SelectableLabel'
    SelectableRecycleBoxLayout:
        default_size: None, dp(18)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        multiselect: False
        touch_multiselect: False
''')
class DeviceConfig(RecycleView):
    def __init__(self, config):
        super().__init__()
        self._selected = None
        self.data = [{'text': str(x) + ' ' + str(config[x])} for x in config.keys()]

    def get_selected(self):
        return self.data[self._selected]['text'] if self._selected is not None else None

    def update_config(self, config):
        self.data = [{'text': str(x) + ' ' + str(config[x])} for x in config.keys()]


Builder.load_string('''
<FileLoadDialog>:
    BoxLayout:
        size: root.size
        pos: root.pos
        orientation: "vertical"
        FileChooserListView:
            id: filechooser
            dirselect: True

        BoxLayout:
            size_hint_y: None
            height: 30
            Button:
                text: "Cancel"
                on_release: root.cancel()

            Button:
                text: "Load"
                on_release: root.load(filechooser.path, filechooser.selection)
''')
class FileLoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


Builder.load_string('''
<ImageViewDialog>:
    BoxLayout:
        size: root.size
        pos: root.pos
        orientation: "vertical"
        AsyncImage:
            source: 'camera.jpeg'
            size: self.texture_size
            nocache: True
        BoxLayout:
            size_hint_y: None
            height: 30
            Button:
                text: "Dismiss"
                on_release: root.cancel()
''')
class ImageViewDialog(FloatLayout):
    cancel = ObjectProperty(None)


class MainMenu(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation='vertical')
        self.spacing=5
        self._buttons = GridLayout(cols=3, spacing=5)
        self.add_widget(self._buttons)
        self._app = app
        self._btn_scan = Button(text='Scan')
        self._btn_scan.bind(on_press=self._scan_pressed)
        self._btn_quit = Button(text='Quit')
        self._btn_quit.bind(on_press=self._quit_pressed)
        self._buttons.add_widget(self._btn_scan)
        self._buttons.add_widget(self._btn_quit)
        self._childmenu = None

    def _scan_pressed(self, _):
        self._popup = Popup(title='Scan', content=Label(text='Scanning for BLE devices, please wait...'), auto_dismiss=True)
        self._popup.open()
        AsyncScanner(self._scan_result)

    def _scan_result(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Scan', content=Label(text=f'Could not scan: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return
        elif result:
            if self._childmenu:
                self.remove_widget(self._childmenu)
                self._buttons.remove_widget(self._btn_connect)
            self._childmenu = DeviceSelector(result)
            self.add_widget(self._childmenu)
            self._btn_connect = Button(text='Connect')
            self._btn_connect.bind(on_press=self._connect_pressed)
            self._buttons.add_widget(self._btn_connect)
        else:
            p = Popup(title='Scan', content=Label(text=f'No devices found'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return

    def _connect_pressed(self, _):
        device = self._childmenu.get_selected()
        if device is not None:
            logger.info(f'Connecting to {device}...')
            self._popup = Popup(title='Connect', content=Label(text=f'Connecting to device {device}...'), auto_dismiss=True)
            self._popup.open()
            AsyncOperation(Tracker, self._on_connected, device)

    def _on_connected(self, result):
        self._popup.dismiss()
        if type(result) is not Tracker:
            p = Popup(title='Connect', content=Label(text=f'{result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return
        else:
            logger.info('Connect success')
            self._tracker = result
            self._btn_scan.disabled = True
            self.remove_widget(self._childmenu)
            self._childmenu = None
            self._buttons.remove_widget(self._btn_connect)
            self._btn_disconnect = Button(text='Disconnect')
            self._btn_disconnect.bind(on_press=self._disconnect_pressed)
            self._buttons.add_widget(self._btn_disconnect)
            self._fetch_device_config()
    def _fetch_device_config(self, cb=None):
        def fetch_params():
            self._tracker.sync()
            return self._tracker.get()
        self._popup = Popup(title='Sync', content=Label(text=f'Fetching device config...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(fetch_params, self._on_fetch_device_config if cb is None else cb)

    def _on_fetch_device_config(self, result):
        self._popup.dismiss()
        if type(result) is not dict:
            self._disconnect_pressed(None)
            p = Popup(title='Sync', content=Label(text=f'Error: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return

        self._config = result
        self._btn_refresh = Button(text='Refresh', disabled=False)
        self._btn_refresh.bind(on_press=self._refresh_pressed)
        self._buttons.add_widget(self._btn_refresh)
        self._ph_btn_calibrate = Button(text='PH Reset Calibration')
        self._ph_btn_calibrate.bind(on_press=self._ph_calibrate_pressed)
        self._buttons.add_widget(self._ph_btn_calibrate)
        self._rtd_btn_calibrate = Button(text='RTD Reset Calibration')
        self._rtd_btn_calibrate.bind(on_press=self._rtd_calibrate_pressed)
        self._buttons.add_widget(self._rtd_btn_calibrate)
        self._btn_fw_update = Button(text='Firmware Update')
        self._btn_fw_update.bind(on_press=self._fw_update_pressed)
        self._buttons.add_widget(self._btn_fw_update)
        self._btn_param_update = Button(text='Params Update')
        self._btn_param_update.bind(on_press=self._param_update_pressed)
        self._buttons.add_widget(self._btn_param_update)
        self._btn_sync_paspw = Button(text='Sync PASPW')
        self._btn_sync_paspw.bind(on_press=self._paspw_pressed)
        self._buttons.add_widget(self._btn_sync_paspw)
        self._btn_deploy = Button(text='Deploy')
        self._btn_deploy.bind(on_press=self._deploy_pressed)
        self._buttons.add_widget(self._btn_deploy)
        self._btn_factw = Button(text='Factory Reset')
        self._btn_factw.bind(on_press=self._factw_pressed)
        self._buttons.add_widget(self._btn_factw)
        self._btn_dumpl = Button(text='Dump Log')
        self._btn_dumpl.bind(on_press=self._dumpl_pressed)
        self._buttons.add_widget(self._btn_dumpl)
        self._btn_dumpp = Button(text='Dump Params')
        self._btn_dumpp.bind(on_press=self._dumpp_pressed)
        self._buttons.add_widget(self._btn_dumpp)
        self._btn_rstvw = Button(text='Reset Counters')
        self._btn_rstvw.bind(on_press=self._rstvw_pressed)
        self._buttons.add_widget(self._btn_rstvw)
        self._btn_reset = Button(text='Reset')
        self._btn_reset.bind(on_press=self._reset_pressed)
        self._buttons.add_widget(self._btn_reset)
        self._childmenu = DeviceConfig(self._config)
        self.add_widget(self._childmenu)

    def _disconnect_pressed(self, _):
        self._btn_disconnect.disabled = True
        AsyncOperation(self._tracker._device.disconnect, self._on_disconnect)
        self._popup = Popup(title='Device', content=Label(text=f'Disconnecting...'), auto_dismiss=True)
        self._popup.open()

    def _on_disconnect(self, _):
        self._popup.dismiss()
        self._btn_scan.disabled = False
        if self._childmenu:
            self._buttons.remove_widget(self._btn_disconnect)
            self._buttons.remove_widget(self._btn_refresh)
            self._buttons.remove_widget(self._ph_btn_calibrate)
            self._buttons.remove_widget(self._rtd_btn_calibrate)
            self._buttons.remove_widget(self._btn_fw_update)
            self._buttons.remove_widget(self._btn_param_update)
            self._buttons.remove_widget(self._btn_sync_paspw)
            self._buttons.remove_widget(self._btn_deploy)
            self._buttons.remove_widget(self._btn_rstvw)
            self._buttons.remove_widget(self._btn_reset)
            self._buttons.remove_widget(self._btn_factw)
            self._buttons.remove_widget(self._btn_dumpl)
            self._buttons.remove_widget(self._btn_dumpp)
            self.remove_widget(self._childmenu)
            self._childmenu = None
        else:
            self._buttons.remove_widget(self._btn_disconnect)

    def _fw_update_pressed(self, _):
        content = FileLoadDialog(load=self._fw_update_apply, cancel=lambda: self._popup.dismiss())
        self._popup = Popup(title="Firmware Update", content=content, auto_dismiss=True)
        self._popup.open()

    def _fw_update_apply(self, path, filename):
        self._popup.dismiss()
        try:
            self._popup = Popup(title="Firmware Update", content=Label(text=f'Applying update (this may take 4-5 minutes)...'),
                                auto_dismiss=True)
            self._popup.open()
            if filename[0].endswith('.zip'):
                data = extract_firmware_file_from_dfu(os.path.join(path, filename[0]))
            else:
                with open(os.path.join(path, filename[0]), 'rb') as f:
                    data = f.read()
                    f.close()
            AsyncOperation(self._tracker.firmware_update, self._on_fw_update_done, data)
        except Exception as e:
            self._popup.dismiss()
            p = Popup(title='Firmware Update', content=Label(text=f'Error: {e}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return

    def _on_fw_update_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Firmware Update', content=Label(text=f'Error: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return
        else:
            self._reset_pressed(False)

    def _reset_pressed(self, _):
        self._on_disconnect(False)
        self._popup = Popup(title='Device', content=Label(text=f'Resetting...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.rstbw, self._on_reset)

    def _on_reset(self, _):
        self._on_disconnect(False)

    def _ph_calibrate_pressed(self, _):
        sensor = 'ph'
        if 'Mid' in self._ph_btn_calibrate.text:
            step = 1
        elif 'Low' in self._ph_btn_calibrate.text:
            step = 2
        elif 'High' in self._ph_btn_calibrate.text:
            step = 3
        elif 'Reset' in self._ph_btn_calibrate.text:
            step = 0
        logger.info('Sending calibration sensor=%s step=%s', sensor, step)
        self._popup = Popup(title='PH Calibration', content=Label(text=f'Calibrating...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.scalw, self._on_ph_calibration_done, sensor, step)

    def _on_ph_calibration_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='PH Calibration', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        else:
            # Switch calibration to next step
            if 'Mid' in self._ph_btn_calibrate.text:
                self._ph_btn_calibrate.text = 'PH Low Calibration'
            elif 'Low' in self._ph_btn_calibrate.text:
                self._ph_btn_calibrate.text = 'PH High Calibration'
            elif 'High' in self._ph_btn_calibrate.text:
                self._ph_btn_calibrate.text = 'PH Reset Calibration'
                self._ph_btn_calibrate.disabled = True
            elif 'Reset' in self._ph_btn_calibrate.text:
                self._ph_btn_calibrate.text = 'PH Mid Calibration'

    def _rtd_calibrate_pressed(self, _):
        sensor = 'rtd'
        if 'Reset' in self._rtd_btn_calibrate.text:
            step = 0
        elif '0C' in self._rtd_btn_calibrate.text:
            step = 1
        logger.info('Sending calibration sensor=%s step=%s', sensor, step)
        self._popup = Popup(title='RTD Calibration', content=Label(text=f'Calibrating...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.scalw, self._on_rtd_calibration_done, sensor, step)

    def _on_rtd_calibration_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='RTD Calibration', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        else:
            # Switch calibration to next step
            if 'Reset' in self._rtd_btn_calibrate.text:
                self._rtd_btn_calibrate.text = 'RTD 0C Calibration'
            elif '0C' in self._rtd_btn_calibrate.text:
                self._rtd_btn_calibrate.text = 'RTD Reset Calibration'
                self._rtd_btn_calibrate.disabled = True

    def _on_config_updated(self, result):
        self._popup.dismiss()
        if type(result) is not dict:
            self._disconnect_pressed(None)
            p = Popup(title='Sync', content=Label(text=f'Error: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return
        self._config = result
        self._childmenu.update_config(self._config)

    def _refresh_pressed(self, _):
        self._fetch_device_config(self._on_config_updated)

    def _on_config_applied(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Config', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return

    def _camera_pressed(self, _):
        self._popup = Popup(title='Camera', content=Label(text=f'Fetching image...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.scamr, self._on_camera_done)

    def _on_camera_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception or len(result) == 0:
            if type(result) is not Exception:
                result = 'No response'
            p = Popup(title='Camera', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        with open('camera.jpeg', 'wb') as f:
            f.write(result)
            f.flush()
            f.close()
            # FIXME: The ImageViewDialog has to be created twice since the first one
            # will cache the old image (for some unknown reason)
            _ = ImageViewDialog(cancel=lambda: self._popup.dismiss())
            content = ImageViewDialog(cancel=lambda: self._popup.dismiss())
            self._popup = Popup(title="Camera Test", content=content, auto_dismiss=True)
            self._popup.open()

    def _sync_pass_predict(self, url='http://uda-argos.cls.fr/uda/resources/allcast?login=LIAM_ICOTEQ&password=LIAM&application=allcast-app'):
        r = requests.get(url, allow_redirects=True)
        self._tracker.paspw(r.content)

    def _paspw_pressed(self, _):
        self._popup = Popup(title='PASPW', content=Label(text=f'Synchronizing PASPW...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._sync_pass_predict, self._on_paspw_done)

    def _on_paspw_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='PASPW', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        self._fetch_device_config(self._on_config_updated)

    def _postime_pressed(self, _):
        self._popup = Popup(title='POS/TIME', content=Label(text=f'Synchronizing POS/TIME...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._sync_pos_time, self._on_postime_done)

    def _on_postime_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='POS/TIME', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        self._fetch_device_config(self._on_config_updated)

    def _deploy_pressed(self, _):
        self._popup = Popup(title='Deploy', content=Label(text=f'Deploying...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.deplw, self._on_deploy_done)

    def _on_deploy_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Deploy', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        self._on_disconnect(False)

    def _rstvw_pressed(self, _):
        self._popup = Popup(title='Reset Counters', content=Label(text=f'Resetting counters...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.rstvw, self._on_rstvw_done)

    def _on_rstvw_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Reset Counters', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        self._fetch_device_config(self._on_config_updated)

    def _param_update_pressed(self, _):
        content = FileLoadDialog(load=self._param_update_apply, cancel=lambda: self._popup.dismiss())
        self._popup = Popup(title="Params Update", content=content, auto_dismiss=True)
        self._popup.open()

    def _param_update_apply(self, path, filename):
        self._popup.dismiss()
        try:
            self._popup = Popup(title="Params Update", content=Label(text=f'Applying params...'),
                                auto_dismiss=True)
            self._popup.open()
            data = extract_params_from_config_file(os.path.join(path, filename[0]))
            AsyncOperation(self._tracker.set, self._on_param_update_done, data)
        except Exception as e:
            self._popup.dismiss()
            p = Popup(title='Params Update', content=Label(text=f'Error: {e}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return

    def _on_param_update_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Params Update', content=Label(text=f'Error: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return
        self._fetch_device_config(self._on_config_updated)

    def _factw_pressed(self, _):
        self._popup = Popup(title='Factory Reset', content=Label(text=f'Resetting to factory defaults...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(self._tracker.factw, self._on_factw_done)

    def _on_factw_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Factory Reset', content=Label(text=f'Failed: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 3)
            return
        self._on_disconnect(False)

    def _dumpl_pressed(self, _):
        board_id = self._config['ARGOS_DECID'] if 'Linkit ' in self._config['DEVICE_MODEL'] else self._config['DEVICE_DECID']
        filename = f'sys_log_{board_id}.txt'
        self._popup = Popup(title='Dump Log', content=Label(text=f'Saving log file to {filename}...'), auto_dismiss=True)
        self._popup.open()
        AsyncOperation(save_system_log, self._on_dumpl_fetch_done, self._tracker, filename)

    def _on_dumpl_fetch_done(self, result):
        self._popup.dismiss()
        if type(result) is Exception:
            p = Popup(title='Dump Log', content=Label(text=f'Error: {result}'), auto_dismiss=True)
            p.open()
            Clock.schedule_once(lambda _: p.dismiss(), 1)
            return

    def _dumpp_pressed(self, _):
        board_id = self._config['ARGOS_DECID'] if 'Linkit ' in self._config['DEVICE_MODEL'] else self._config['DEVICE_DECID']
        filename = f'params_{board_id}.txt'
        save_params(filename, self._config)
        self._popup = Popup(title='Dump Params', content=Label(text=f'Saving params to {filename}...'), auto_dismiss=True)
        self._popup.open()
        Clock.schedule_once(lambda _: self._popup.dismiss(), 1)

    def _quit_pressed(self, _):
        logger.debug('Quitting application')
        self._app.stop()


class GUIApp(App):

    def build(self):
        return MainMenu(self)
