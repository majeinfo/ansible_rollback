# Only for Python3
'''
A rollback playbook SHOULD NOT create another rollback playbook because it SHOULD NOT create any resources !
'''

__metaclass__ = type

DOCUMENTATION = '''
    author: J.Delamarche
    name: resource_cleaner
    type: notification
    requirements:
      - whitelist in configuration
    short_description: Intercepts Cloud resources creation
    description:
        - This is an ansible callback plugin that registers Cloud resources creation and generates a playbook to destroy them
    options:
      playbook_output_path:
        required: False
        default: .
        description: directory where playbooks must be created
        env:
          - name: RESOURCE_CLEANER_OUTPUT_PATH
        ini:
          - section: resource_cleaner
            key: playbook_output_path

'''

import sys
import time
import json
import yaml
import os
import os.path
import pprint

from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.callback import CallbackBase

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')
)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Here, add other Cleaner (in the future)
from plugins.module_utils.aws_cleaner import AWSCleaner


# Parameters and their default values
PLAYBOOK_OUTPUT_PATH = '.'


class CallbackModule(CallbackBase):
    """
    This is an ansible callback plugin that registers resource creation.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'resource_cleaner'
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self, display=None):
        super().__init__(display=display)
        self.disabled = False   # True if rollback playbook cannot be generated
        self.playbook_output_path = PLAYBOOK_OUTPUT_PATH
        self.playbook_full_name = None  # fullname
        self.playbook_name =  None      # basename
        self.play = None                # current play
        self.actions = []               # recorded actions for a Play

        # List of handled Cloud providers
        self.providers = {
            'amazon.aws': AWSCleaner(self),
        }

    def set_options(self, task_keys=None, var_options=None, direct=None):
        '''
        First callback to be called
        '''
        super().set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        self._debug("set_options")
        self.playbook_output_path = self.get_option('playbook_output_path')

        if not os.path.isdir(self.playbook_output_path):
            self._display.warning(f'The path given by playbook_output_path parameter is not a directory: {self.playbook_output_path}.')
            self.disabled = True

    # Now the playbook starts !
    def v2_playbook_on_start(self, playbook):
        self._debug("v2_playbook_on_start")
        super().v2_playbook_on_start(playbook)
        self.playbook_fullname = playbook._file_name
        self.playbook_name = os.path.basename(playbook._file_name)

    # Each Play of the Playbook starts now
    def v2_playbook_on_play_start(self, play):
        self._debug("v2_playbook_on_play_start")
        super().v2_playbook_on_play_start(play)
        self._debug(play)
        self.play = play
        self.actions = []

    # A task is started now
    def v2_playbook_on_task_start(self, task, is_conditional, handler=False):
        self._debug("v2_playbook_on_start_task")
        super().v2_playbook_on_task_start(task, is_conditional)

    # A task is executed by a runner
    def v2_runner_on_start(self, host, task):
        # v2_runner_on_start was added in 2.8 so this doesn't get run for Ansible 2.7 and below.
        self._debug("v2_runner_on_start")
        super().v2_runner_on_start(host, task)

    # The runner succeeded
    def v2_runner_on_ok(self, result):
        self._debug("v2_runner_on_ok")
        self._debug(pprint.pformat(result))
        self._debug(result._result)
        super().v2_runner_on_ok(result)

        self._debug(f"is_changed={result.is_changed()}, "
                          f"is_failed={result.is_failed()}, "
                          f"is_skipped={result.is_skipped()}, "
                          f"is_unreachable={result.is_unreachable()}, "
                          f"task_name={result.task_name}")

        # Actions executed in a loop are handled by v2_runner_item_on_ok
        if result._task.loop:
            return

        self._handle_action(result)

    # The runner succeeded to apply an item in a loop
    def v2_runner_item_on_ok(self, result):
        self._debug("v2_runner_item_on_ok")
        self._debug(pprint.pformat(result))
        self._debug(result._result)
        super().v2_runner_item_on_ok(result)
        self._handle_action(result)

    # handle an Action
    def _handle_action(self, result):
        # If nothing changed, there is nothing to rollback
        if not result._result.get('changed', False):
            return

        # AnsibleUnicode to str otherwise the YAML dump will fail...
        action_name = str(result._task_fields.get('action'))
        for key, cleaner in self.providers.items():
            # Look for a Provide (AWS, GCP, ...)
            if action_name.startswith(key):
                provider = self.providers[key]
                if (action := provider.handle_action(action_name, result)) is not None:
                    self._insert_action(action, result, action_name)
     
    # The runner failed
    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._debug("v2_runner_on_failed")
        super().v2_runner_on_failed(result, ignore_errors)

    # The runner could not reach the remote host
    def v2_runner_on_unreachable(self, result):
        self._debug("v2_runner_on_unreachable")
        super().v2_runner_on_unreachable(result)

    # The task has been skipped
    def v2_runner_on_skipped(self, result):
        self._debug("v2_runner_on_skipped")
        super().v2_runner_on_skipped(result)

    # A Handler has been called and must be started
    def v2_playbook_on_handler_task_start(self, task):
        self._debug("v2_playbook_on_handler_task_start")
        super().v2_playbook_on_handler_task_start(task)

    # This is the final call
    def v2_playbook_on_stats(self, stats):
        self._debug("v2_playbook_on_stats")
        super().v2_playbook_on_stats(stats)
        if self.disabled:
            return

        hosts = sorted(stats.processed.keys())
        self.rollback_playbook()

    # Add an action at the head of the list (assume a reverse order)
    def _insert_action(self, action, result, module_name):
        '''
        action: can be a single Playook action or a list of actions
        '''
        self._debug("_insert_action")
        self._debug(action)
        task_name = result._task_fields.get('name')
        # create a new dict to make sure the 'name' key will be the first one at dump time
        final_action_name = {
            'name': "(UNDO) " + str(task_name) if task_name else "empty",
        }
        if type(action) == list:
            for act in action:
                self.actions.insert(0, final_action_name | act)
        else:
            self.actions.insert(0, final_action_name | action)

    # Generate the rollback playbook
    def rollback_playbook(self):
        # Do not generate empty playbook
        if not len(self.actions):
            return 

        playbook = [
            { 
                'name': str(self.play.name),
                'hosts': str(self.play.hosts[0]),
                'connection': str(self.play.connection),
                'gather_facts': self.play.gather_facts,
                'tasks': self.actions, 
            }
        ]

        with open(os.path.join(self.playbook_output_path, self.playbook_name + '.rollback'), 'w') as f:
            yaml.dump(playbook, f, Dumper=IndentDumper, sort_keys=False)

    # Convert AnsibleUnsafeText into a real str (needed for the YAML dumper)
    def _to_text(self, value):
        return super(type(value), value).__str__()

    # Display message if display mode and verbosity is sufficient
    def _info(self, msg):
        if self._display.display:
            self._display.display("[Cleaner Callback] " + str(msg))

    # Display message if verbosity is sufficient
    def _debug(self, msg):
        if self._display.verbosity >= 1:
            self._info(msg)


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

# EOF
