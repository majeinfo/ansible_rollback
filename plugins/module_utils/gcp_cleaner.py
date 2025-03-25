# Driver for GCP Resources

import sys
from .cleaner_base import CleanerBase


class GCPCleaner(CleanerBase):
    def __init__(self, callback):
        super().__init__(callback)
        callback._debug("GCPCleaner __init__")

        # List of handled actions
        self.gcp_actions = {
        }

    # handle an Action
    def handle_action(self, action_name, result):
        if action_name in self.gcp_actions:
            if (action := self.gcp_actions[action_name](action_name, result)) is not None:
                return self._gcp_generate_action(action, action_name, result)

        return None

    # Generate the rollback action
    def _gcp_generate_action(self, action, module_name, result):
        task_name = result._task_fields.get('name')
        # create a new dict to make sure the 'name' key will be the first one at dump time
        final_action = {
            'name': "(UNDO) " + str(task_name) if task_name else "empty",
        }
        final_action |= action

        module_args = result._result.get('invocation').get('module_args')
        #for key in ('access_key', 'secret_key', 'region', 'aws_config', 'profile'):
        #    if value := module_args.get(key):
        #        final_action[module_name][key] = self._to_text(value)

        return final_action

# EOF
