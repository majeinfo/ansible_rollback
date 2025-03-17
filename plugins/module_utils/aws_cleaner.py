# Only for Python3
# Driver for AWS Resources

import sys
from .cleaner_base import CleanerBase


class AWSCleaner(CleanerBase):
    def __init__(self, callback):
        super().__init__(callback)
        callback._debug("AWSCleaner __init__")

        # List of handled actions
        self.aws_actions = {
            'amazon.aws.ec2_instance': self._ec2_instance,
            'amazon.aws.ec2_vol': self._ec2_vol,
            'amazon.aws.ec2_vpc_net': self._ec2_vpc_net,
            'amazon.aws.ec2_vpc_subnet': self._ec2_vpc_subnet,
            'amazon.aws.ec2_security_group': self._ec2_security_group,
            'amazon.aws.ec2_eip': self._ec2_eip,
        }

    # handle an Action
    def handle_action(self, action_name, result):
        if action_name in self.aws_actions:
            if (action := self.aws_actions[action_name](action_name, result)) is not None:
                return self._ec2_generate_action(action, action_name, result)

        return None

    # Called upon ec2 instance creation
    def _ec2_instance(self, module_name, result):
        changed_ids = result._result.get('changed_ids')
        instance_ids = result._result.get('instance_ids')
        self.callback._debug(f"instances created: {instance_ids}, instances changed: {changed_ids}")
        if changed_ids is not None:
            instance_ids = changed_ids

        self.callback._debug(f"created instances: {instance_ids}")

        # Generate amazon.aws.ec2_instance delete !
        return ({
            module_name: {
                'state': 'terminated',
                'instance_ids': list(instance_ids)
            }
        })

    # Called upon Volume creation
    def _ec2_vol(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        state = module_args.get('state')
        if state != 'present':
            return None

        volume = result._result.get('volume')
        volume_id = self._to_text(volume.get('id'))
        self.callback._debug(f"volume {volume_id}")

        # Generate amazon.aws.ec2_vol delete !
        return ({
            module_name: {
                'state': 'absent',
                'id': volume_id,
            }
        })

    # Called upon VPC creation
    def _ec2_vpc_net(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        state = module_args.get('state')
        if state != 'present':
            return None

        vpc = result._result.get('vpc')
        vpc_id = self._to_text(vpc.get('id'))
        self.callback._debug(f"vpc {vpc_id}")

        # Generate amazon.aws.ec2_vpc_net delete !
        return ({
            module_name: {
                'state': 'absent',
                'vpc_id': vpc_id
            }
        })

    # Called upon VPC subnet creation
    def _ec2_vpc_subnet(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        state = module_args.get('state')
        if state != 'present':
            return None

        subnet = result._result.get('subnet')
        subnet_id = self._to_text(subnet.get('id'))
        vpc_id = self._to_text(subnet.get('vpc_id'))
        cidr_block = self._to_text(subnet.get('cidr_block'))
        self.callback._debug(f"subnet {subnet_id}")

        # Generate amazon.aws.ec2_subnet_net delete !
        return ({
            module_name: {
                'state': 'absent',
                'vpc_id': vpc_id,
                'cidr': cidr_block,
            }
        })

    # Called upon Security Group creation
    def _ec2_security_group(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        state = module_args.get('state')
        if state != 'present':
            return None

        group_id = result._result.get('group_id')
        self.callback._debug(f"security_group {group_id}")

        # Generate amazon.aws.ec2_security_group delete !
        return ({
            module_name: {
                'state': 'absent',
                'group_id': self._to_text(group_id),
            }
        })

    # Called upon EIP creation
    def _ec2_eip(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        state = module_args.get('state')
        if state != 'present':
            return None

        in_vpc = module_args.get('in_vpc')
        allocation_id = result._result.get('allocation_id')
        public_ip = result._result.get('public_ip')
        self.callback._debug(f"EIP allocation_id {allocation_id}")

        # Generate amazon.aws.ec2_eip delete !
        return ({
            module_name: {
                'state': 'absent',
                'public_ip': self._to_text(public_ip),
                'in_vpc': in_vpc,
                'release_on_disassociation': True,
            }
        })

    # Generate the rollback action
    def _ec2_generate_action(self, action, module_name, result):
        task_name = result._task_fields.get('name')
        # create a new dict to make sure the 'name' key will be the first one at dump time
        final_action = {
            'name': "(UNDO) " + str(task_name) if task_name else "empty",
        }
        final_action |= action

        module_args = result._result.get('invocation').get('module_args')
        for key in ('access_key', 'secret_key', 'region', 'aws_config', 'profile'):
            if value := module_args.get(key):
                final_action[module_name][key] = self._to_text(value)

        return final_action

# EOF
