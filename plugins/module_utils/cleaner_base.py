'''
Base class for the Cloud cleaners
'''
from ansible.utils.display import Display

display = Display()


class CleanerBase:
    def __init__(self, callback):
        self.callback = callback
        self.actions = {}   # must be defined in children classes

    # handle an Action
    def handle_action(self, action_name, result):
        if action_name in self.actions:
            if (action := self.actions[action_name](action_name, result)) is not None:
                return self._generate_action(action, action_name, result)

        return None

    def _generate_action(self, action, action_name, result):
        return NotImplemented

    # Convert AnsibleUnsafeText into a real str (needed for the YAML dumper)
    def _to_text(self, value):
        return super(type(value), value).__str__()


# Decorator for unsupported module
def not_supported(func):
    def _not_supported(self, module_name, result):
        display.warning(f"Module {module_name} not supported yet !")
        return None

    return _not_supported

# EOF
