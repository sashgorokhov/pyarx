import ctypes
import logging
import os
import platform
import time

logger = logging.getLogger(__name__)


class ArxControlError(Exception):
    pass


class ArxControlShutdownError(ArxControlError):
    pass


class DEF:
    ORIENTATION_PORTRAIT = 0x01
    ORIENTATION_LANDSCAPE = 0x10

    EVENT_FOCUS_ACTIVE = 0x01
    EVENT_FOCUS_INACTIVE = 0x02
    EVENT_TAP_ON_TAG = 0x04
    EVENT_MOBILEDEVICE_ARRIVAL = 0x08
    EVENT_MOBILEDEVICE_REMOVAL = 0x10

    DEVICETYPE_IPHONE = 0x01
    DEVICETYPE_IPAD = 0x02
    DEVICETYPE_ANDROID_SMALL = 0x03
    DEVICETYPE_ANDROID_NORMAL = 0x04
    DEVICETYPE_ANDROID_LARGE = 0x05
    DEVICETYPE_ANDROID_XLARGE = 0x06
    DEVICETYPE_ANDROID_OTHER = 0x07

    CALLBACK_DEFINITION = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_void_p)

    ERROR_CODE_SUCCESS = 0
    ERROR_CODE_WRONG_PARAM_FORMAT = 1
    ERROR_CODE_NULL_NOT_SUPPORTED = 2
    ERROR_CODE_WRONG_FILE_PATH = 3
    ERROR_CODE_SDK_NOT_INITIALIZED = 4
    ERROR_CODE_SDK_INITIALIZED = 5
    ERROR_CODE_CONN_BROKEN = 6
    ERROR_CODE_FAILED_CREATE_THREAD = 7
    ERROR_CODE_FAILED_COPY_MEMORY = 8


def get_default_arx_dll():
    """
    Return default arx dll path at installed logitech gaming software

    :rtype: None|str
    """
    system_arch = 'x86' if platform.architecture()[0] == '32bit' else 'x64'

    try:
        program_files_path = os.environ['ProgramW6432']
    except KeyError:
        program_files_path = os.environ['ProgramFiles']

    dll_path = os.path.join(program_files_path, 'Logitech Gaming Software',
                            'SDK', 'Arx Control', system_arch, 'LogitechGArxControl.dll')

    if os.path.exists(dll_path):
        return dll_path

    return None


def _text_limit(text, limit=128):
    if len(text) > 128:
        logger.warning('Truncating too long text(%s): %s', limit, text)
    return text[:128]


class ArxControl(object):
    def __init__(self, app_name, friendly_name, callback, dll_path=None):
        """
        :param str app_name: A unique identifier for the game or application
        :param str friendly_name: The name that will be displayed
            on Arx Control for applet
        :param Callable callback: This function will be called
            when an event occurs. Expected signature is:
            event_type, event_value, event_arg, context

        :param str|None dll_path: Custom path of arx control dll
        """
        self._app_name = app_name[:128]
        self._friendly_name = friendly_name[:128]
        self._callback = callback

        dll_path = dll_path or get_default_arx_dll()

        if not dll_path or not os.path.exists(dll_path):
            raise FileNotFoundError('DLL not found: %s' % dll_path)

        self._arx_dll = ctypes.cdll.LoadLibrary(dll_path)

    def init(self):
        """
        Initialize arx control connection
        """
        callback_ref = ctypes.byref(DEF.CALLBACK_DEFINITION(self._callback))
        app_name = ctypes.c_wchar_p(self._app_name)
        friendly_name = ctypes.c_wchar_p(self._friendly_name)
        ret = self._call('LogiArxInit', app_name, friendly_name, callback_ref)
        if ret:
            time.sleep(1)
        return ret

    def add_string_as(self, string, filename, mime_type=''):
        """
        Saves a string encoded in UTF8 to a file and sends it to
        Arx Control.

        :param str string: The string to be saved to file and sent
            over to Arx Control.

        :param str filename: A string that represents how the file
            will be referenced once loaded in Arx Control. Text
            length is capped to 256 characters, any string longer
            than that will be truncated.

        :param str mime_type: A string that represents the mime type to
            associate the file with. This will determine how the app
            will interpret this file in the webview.
        """
        string = ctypes.c_wchar_p(string)
        filename = ctypes.c_wchar_p(_text_limit(filename, 256))
        mime_type = ctypes.c_wchar_p(mime_type)
        return self._arx_dll.LogiArxAddUTF8StringAs(string, filename, mime_type)

    def set_index(self, filename):
        """
        Sets which page is the one to be displayed on Arx Control.

        The first time this function is called on a valid file the
        applet will be brought in the foreground on Arx Control.

        :param str filename: A string that represents how the file
            will be referenced once loaded in Arx Control. Text
            length is capped to 256 characters, any string longer
            than that will be truncated.
        """
        filename = ctypes.c_wchar_p(_text_limit(filename, 256))
        return self._arx_dll.LogiArxSetIndex(filename)

    def get_last_error(self):
        """
        Retrieves and returns the last error occurred in the SDK
        function calls. Call this function if an SDK function call
        fails to get more detailed information on the failure.
        """
        return self._arx_dll.LogiArxGetLastError()

    def add_file_as(self, filepath, filename, mime_type=''):
        """
        Sends a file from a local path to Arx Control.

        :param str filepath: A string that represents a local path.
            This can be both relative to the game executable
            or absolute. Text length is capped to 256 characters,
            any string longer than that will be truncated.

        :param str filename: A string that represents how the file
            will be referenced once loaded in Arx Control. Text
            length is capped to 256 characters, any string longer
            than that will be truncated.

        :param str mime_type: A string that represents the mime type to
            associate the file with. This will determine how the app
            will interpret this file in the webview.
        """
        filepath = ctypes.c_wchar_p(_text_limit(filepath, 256))
        filename = ctypes.c_wchar_p(_text_limit(filename, 256))
        mime_type = ctypes.c_wchar_p(mime_type)
        return self._call('LogiArxAddFileAs', filepath, filename, mime_type)

    def add_content_as(self, content, size, filename, mime_type=''):
        """
        Sends a block of memory to Arx Control.

        If the size specified is bigger than the memory allocated for
        the pointer content, the function may raise an exception.
        If the size is smaller, only the first size byte will be sent.

        :param content: Block of memory to be sent to the Arx Control.
        :param int size: The size of the block of memory.

        :param str filename: A string that represents how the file
            will be referenced once loaded in Arx Control. Text
            length is capped to 256 characters, any string longer
            than that will be truncated.

        :param str mime_type: A string that represents the mime type to
            associate the file with. This will determine how the app
            will interpret this file in the webview.
        """
        content = ctypes.c_void_p(content)
        size = ctypes.c_int(size)
        filename = ctypes.c_wchar_p(_text_limit(filename, 256))
        mime_type = ctypes.c_wchar_p(mime_type)
        return self._call('LogiArxAddContentAs', content, size, filename, mime_type)

    def set_tag_property_by_id(self, tag_id, prop, new_value):
        """
        Updates a tag property in the applet html pages.

        If the no tag with id tagId is found, the function will return
        true and no tag will be updated. If more than one tag on
        any page have the same id, each one of them will be updated.

        :param str tag_id:  The id of the tag to update the property on.
            Text length is capped to 128 characters, any string longer
            than that will be truncated.

        :param str prop: The property to update. Text length is
            capped to 128 characters, any string longer than that
            will be truncated.

        :param str new_value:  The new value to assign to the
            property prop on the tag with id tagId. Text length
            is capped to 128 characters, any string longer than
            that will be truncated.
        """
        tag_id = ctypes.c_wchar_p(_text_limit(tag_id))
        prop = ctypes.c_wchar_p(_text_limit(prop))
        new_value = ctypes.c_wchar_p(_text_limit(new_value, 256))
        return self._call('LogiArxSetTagPropertyById', tag_id, prop, new_value)

    def set_tag_propery_by_class(self, tag_class, prop, new_value):
        """
        Updates a property on a class of tags in the applet html pages.

        If the no tag with class tagClass is found, the function
        will return true and no tag will be updated.

        :param str tag_class: The class of the tags to update
            the property on. Text length is capped to 128 characters,
            any string longer than that will be truncated.

        :param str prop: The property to update. Text length is
            capped to 128 characters, any string longer than that
            will be truncated.

        :param str new_value:  The new value to assign to the
            property prop on the tag with id tagId. Text length
            is capped to 128 characters, any string longer than
            that will be truncated.
        """
        tag_class = ctypes.c_wchar_p(_text_limit(tag_class))
        prop = ctypes.c_wchar_p(_text_limit(prop))
        new_value = ctypes.c_wchar_p(_text_limit(new_value, 256))
        return self._call('LogiArxSetTagsPropertyByClass', tag_class, prop, new_value)

    def set_tag_content_by_id(self, tag_id, new_content):
        """
        Updates the content of a tag in the applet html pages.

        :param tag_id: The id of the tag to update the property on.
            Text length is capped to 128 characters, any string
            longer than that will be truncated.

        :param new_content: The new html content that will be injected in the tag.
        """
        tag_id = ctypes.c_wchar_p(_text_limit(tag_id))
        new_content = ctypes.c_wchar_p(new_content)
        return self._call('LogiArxSetTagContentById', tag_id, new_content)

    def set_tag_content_by_class(self, tag_class, new_content):
        """
        Updates the content of a class of tags in the applet html pages.


        :param tag_class: The class of the tags for which the content
            will be replaced. Text length is capped to 128 characters,
            any string longer than that will be truncated.

        :param new_content: The new html content that will be injected in the tag.
        """
        tag_class = ctypes.c_wchar_p(_text_limit(tag_class))
        new_content = ctypes.c_wchar_p(new_content)
        return self._call('LogiArxSetTagsContentByClass', tag_class, new_content)

    def _call(self, func_name, *args):
        """
        Call DLL function and check its return value and error code, of any
        """
        ret_val = getattr(self._arx_dll, func_name)(*args)
        if ret_val == 0:
            last_error = self.get_last_error()

            if last_error == DEF.ERROR_CODE_SDK_INITIALIZED:
                return ret_val

            logger.warning('Got error from arx control for %s: %s', func_name, last_error)

            if last_error == DEF.ERROR_CODE_CONN_BROKEN:
                self.shutdown()
                raise ArxControlShutdownError('Connection to arx control is broken')

        return ret_val

    def shutdown(self):
        """
        Frees the memory used by the SDK for the applet and shuts
        it down on Arx Control.
        """
        self._arx_dll.LogiArxShutdown()

    def __enter__(self):
        if not self.init():
            raise ArxControlError('Failed to initialize arx control connection')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    index = """<html>
<head>
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0, maximum-scale=1, target-densityDpi=device-dpi, user-scalable=no"/>
    <link rel="stylesheet" type="text/css" href="style.css">
</head>
<body>
<h2>Hello, world!</h2>
</body>
</html>
        """
    css = """
        body {
            background-color: cornflowerblue;
        }
    """
    callback = lambda *args: logger.debug('event_type=%s, event_value=%s, event_arg=%s, context=%s', *args)

    with ArxControl('foo.bar', 'Test Friendly Name', callback) as arx_control:
        arx_control.add_string_as(index, 'index.html', 'text/html')
        arx_control.add_string_as(css, 'style.css', 'text/css')
        arx_control.set_index('index.html')
        input('Press enter to exit:')
