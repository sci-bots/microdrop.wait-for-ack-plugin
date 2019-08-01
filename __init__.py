from asyncio_helpers import sync
from logging_helpers import _L
from microdrop.plugin_manager import (PluginGlobals, Plugin, IPlugin,
                                      implements)
from pygtkhelpers.gthreads import gtk_threadsafe
import gtk
import microdrop as md
import trollius as asyncio

from ._version import get_versions

__version__ = get_versions()['version']
del get_versions

PluginGlobals.push_env('microdrop.managed')


class WaitForAckPlugin(Plugin):
    implements(IPlugin)

    plugin_name = 'wait_for_ack_plugin'
    version = __version__

    @property
    def name(self):
        return self.plugin_name

    @name.setter
    def name(self, value):
        pass

    @asyncio.coroutine
    def on_step_run(self, plugin_kwargs, signals):
        '''Wait for operator to manually acknowledge that step is complete.

        Display a GTK dialog with **OK** and **Cancel** buttons.  If **Cancel**
        is pressed, raise a ``RuntimeError`` exception is raised.  If **OK** is
        pressed, finish step execution.

        Parameters
        ----------
        message : str
            Message displayed to user in dialog.
        description : str, optional
            Title of the prompt (if specified).

        Raises
        ------
        RuntimeError
            If **Cancel** button is pressed.
        '''
        message = 'Click OK to continue or Cancel to stop protocol'

        # Use `asyncio_helpers.sync` decorator to:
        #  1. Launch dialog from main GTK thread (through `gtk_threadsafe`)
        #  2. Provide an asyncio wrapper around async GTK call, which returns
        #     only after the scheduled call has finished executing. This makes
        #     it possible to coordinate between UI code and protocol asyncio code.
        @sync(gtk_threadsafe)
        def _acknowledge():
            app = md.app_context.get_app()
            parent_window = app.main_window_controller.view
            dialog = gtk.MessageDialog(parent=parent_window,
                                       message_format=message,
                                       type=gtk.MESSAGE_OTHER,
                                       buttons=gtk.BUTTONS_OK_CANCEL)
            # Increase default dialog size.
            dialog.props.title = 'Wait for acknowledgement'
            dialog.props.use_markup = True

            response_code = dialog.run()
            dialog.destroy()
            return response_code

        _L().debug('wait for user to acknowledge step completion')

        # Queue dialog to be launched in GTK thread and wait for response.
        response = yield asyncio.From(_acknowledge())
        if response != gtk.RESPONSE_OK:
            raise RuntimeError('Cancelled in response to message `%s`.' % message)
        else:
            _L().debug('user acknowledged step completion')


PluginGlobals.pop_env()
