'''
Base class for the Cloud cleaners
'''
class CleanerBase:
    def __init__(self, callback):
        self.callback = callback


    def handle_action(self, action_name, result):
        raise NotImplemented


    # Convert AnsibleUnsafeText into a real str (needed for the YAML dumper)
    def _to_text(self, value):
        return super(type(value), value).__str__()

# EOF
