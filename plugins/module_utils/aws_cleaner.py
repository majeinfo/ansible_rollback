# Only for Python3
# Driver for AWS Resources

import sys
from .cleaner_base import CleanerBase

def aws_check_state_present(func):
    '''
    Decorator that ensures the resource is created.
    There is no rollback to do if it is not !
    '''
    def _check_state_present(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        state = module_args.get('state')
        if state != 'present':
            self.callback._debug(f"module {module_name} does not create any new resource")
            return None

        return func(self, module_name, result)

    return _check_state_present


class AWSCleaner(CleanerBase):
    def __init__(self, callback):
        super().__init__(callback)
        callback._debug("AWSCleaner __init__")

        # List of handled actions
        self.aws_actions = {
            'amazon.aws.ec2_ami': self._ec2_ami,
            'amazon.aws.ec2_eip': self._ec2_eip,
            'amazon.aws.ec2_eni': self._ec2_eni,
            'amazon.aws.ec2_instance': self._ec2_instance,
            'amazon.aws.ec2_key': self._ec2_key,
            'amazon.aws.ec2_snapshot': self._ec2_snapshot,
            'amazon.aws.ec2_tag': self._ec2_tag,
            'amazon.aws.ec2_vol': self._ec2_vol,
            'amazon.aws.ec2_vpc_dhcp_option': self._ec2_vpc_dhcp_option,
            'amazon.aws.ec2_vpc_endpoint': self._ec2_vpc_endpoint,
            'amazon.aws.ec2_vpc_igw': self._ec2_vpc_igw,
            'amazon.aws.ec2_vpc_nat_gateway': self._ec2_vpc_nat_gateway,
            'amazon.aws.ec2_vpc_net': self._ec2_vpc_net,
            'amazon.aws.ec2_vpc_route_table': self._ec2_vpc_route_table,
            'amazon.aws.ec2_vpc_subnet': self._ec2_vpc_subnet,
            'amazon.aws.ec2_security_group': self._ec2_security_group,
            'amazon.aws.s3_bucket': self._s3_bucket,
            'amazon.aws.s3_object': self._s3_object,
        }

    # handle an Action
    def handle_action(self, action_name, result):
        if action_name in self.aws_actions:
            if (action := self.aws_actions[action_name](action_name, result)) is not None:
                return self._aws_generate_action(action, action_name, result)

        return None

    # Called upon ec2 AMI creation
    @aws_check_state_present
    def _ec2_ami(self, module_name, result):
        image_id = result._result.get('image_id')
        self.callback._debug(f"created AMI: {image_id}")

        # Generate amazon.aws.ec2_ami delete !
        return ({
            module_name: {
                'state': 'absent',
                'image_id': self._to_text(image_id),
            }
        })

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
                'instance_ids': list(instance_ids),
            }
        })

    # Called upon Volume creation
    @aws_check_state_present
    def _ec2_vol(self, module_name, result):
        volume = result._result.get('volume')
        volume_id = volume.get('id')
        self.callback._debug(f"volume {volume_id}")

        # Generate amazon.aws.ec2_vol delete !
        return ({
            module_name: {
                'state': 'absent',
                'id': self._to_text(volume_id),
            }
        })

    # Called upon Snapshot creation
    @aws_check_state_present
    def _ec2_snapshot(self, module_name, result):
        snapshot_id = result._result.get('snapshot_id')
        self.callback._debug(f"snapshot {snapshot_id}")

        # Generate amazon.aws.ec2_snapshot delete !
        return ({
            module_name: {
                'state': 'absent',
                'snapshot_id': self._to_text(snapshot_id),
            }
        })

    # Called upon VPC DHCP option creation
    @aws_check_state_present
    def _ec2_vpc_dhcp_option(self, module_name, result):
        dhcp_options_id = result._result.get('dhcp_options_id')
        self.callback._debug(f"dhcp options {dhcp_options_id}")

        # Generate amazon.aws.ec2_vpc_dhcp_option delete !
        return ({
            module_name: {
                'state': 'absent',
                'dhcp_options_id': self._to_text(dhcp_options_id),
            }
        })
    
    # Called upon VPC endpoint creation
    @aws_check_state_present
    def _ec2_vpc_endpoint(self, module_name, result):
        vpc_endpoint_id = result._result.get('result').get('vpc_endpoint_id')
        self.callback._debug(f"vpc endpoint {vpc_endpoint_id}")

        # Generate amazon.aws.ec2_vpc_endpoint delete !
        return ({
            module_name: {
                'state': 'absent',
                'vpc_endpoint_id': self._to_text(vpc_endpoint_id),
            }
        })
    
    # Called upon VPC igw creation
    @aws_check_state_present
    def _ec2_vpc_igw(self, module_name, result):
        gateway_id = result._result.get('gateway_id')
        vpc_id = result._result.get('vpc_id')
        self.callback._debug(f"vpc igw {gateway_id}")

        # Generate amazon.aws.ec2_vpc_igw delete !
        return ({
            module_name: {
                'state': 'absent',
                #'gateway_id': self._to_text(gateway_id),
                'vpc_id': self._to_text(vpc_id),
            }
        })
    
    # Called upon VPC NATGW creation
    @aws_check_state_present
    def _ec2_vpc_nat_gateway(self, module_name, result):
        '''
        Deleting a NAT GW is more complex: it may be needed
        to delete dynamically allocated EIP ! That's why this
        function returns a list of Ansible Playbook actions
        '''
        actions = []
        nat_gateway_id = result._result.get('nat_gateway_id')
        self.callback._debug(f"nat gateway {nat_gateway_id}")

        # if allocation_id is not se, an EIP will be allocated
        # TODO: not supported
        module_args = result._result.get('invocation').get('module_args')
        allocation_id = module_args.get('allocation_id')
        if not allocation_id:
            nat_gw_addrs = result._result.get('nat_gateway_addresses')
            for eip in nat_gw_addrs:
                allocation_id = eip['allocation_id']
                if 'public_ip' not in eip:
                    self.callback._info(f"public_ip missing for allocated_ip {allocation_id}: this EIP will not be deleted")
                    continue

                public_ip = eip['public_ip']
                action = self._ec2_eip_internal(public_ip, in_vpc=True)
                actions.append(action)

        # Generate amazon.aws.ec2_vpc_nat_gateway delete !
        actions.append({
            module_name: {
                'state': 'absent',
                'nat_gateway_id': self._to_text(nat_gateway_id),
            }
        })
        #return actions  # list not supported
        return actions[0]
    
    # Called upon VPC Route Table creation
    @aws_check_state_present
    def _ec2_vpc_route_table(self, module_name, result):
        route_table = result._result.get('route_table')
        route_table_id = route_table.get('route_table_id')
        self.callback._debug(f"route table {route_table_id}")

        # Generate amazon.aws.ec2_vpc_route_table delete !
        return ({
            module_name: {
                'state': 'absent',
                #'vpc_id': self._to_text(vpc_id),
                'route_table_id': self._to_text(route_table_id),
                'lookup': 'id',
            }
        })

    # Called upon VPC creation
    @aws_check_state_present
    def _ec2_vpc_net(self, module_name, result):
        vpc = result._result.get('vpc')
        vpc_id = vpc.get('id')
        self.callback._debug(f"vpc {vpc_id}")

        # Generate amazon.aws.ec2_vpc_net delete !
        return ({
            module_name: {
                'state': 'absent',
                'vpc_id': self._to_text(vpc_id),
            }
        })

    # Called upon VPC subnet creation
    @aws_check_state_present
    def _ec2_vpc_subnet(self, module_name, result):
        subnet = result._result.get('subnet')
        subnet_id = self._to_text(subnet.get('id'))
        vpc_id = subnet.get('vpc_id')
        cidr_block = subnet.get('cidr_block')
        self.callback._debug(f"subnet {subnet_id}")

        # Generate amazon.aws.ec2_subnet_net delete !
        return ({
            module_name: {
                'state': 'absent',
                'vpc_id': self._to_text(vpc_id),
                'cidr': self._to_text(cidr_block),
            }
        })

    # Called upon Security Group creation
    @aws_check_state_present
    def _ec2_security_group(self, module_name, result):
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
    @aws_check_state_present
    def _ec2_eip(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        in_vpc = module_args.get('in_vpc')
        allocation_id = result._result.get('allocation_id')
        public_ip = result._result.get('public_ip')
        self.callback._debug(f"EIP allocation_id {allocation_id}")

        return self._ec2_eip_internal(public_ip, in_vpc)

    def _ec2_eip_internal(self, public_ip, in_vpc):
        # Generate amazon.aws.ec2_eip delete !
        return ({
            module_name: {
                'state': 'absent',
                'public_ip': self._to_text(public_ip),
                'in_vpc': in_vpc,
                'release_on_disassociation': True,
            }
        })

    # Called upon ENI creation
    @aws_check_state_present
    def _ec2_eni(self, module_name, result):
        interface = result._result.get('interface')
        eni_id = interface.get('id')
        self.callback._debug(f"ENI eni_id {eni_id}")

        # Generate amazon.aws.ec2_eni delete !
        return ({
            module_name: {
                'state': 'absent',
                'eni_id': self._to_text(eni_id),
            }
        })
  
    # Called upon KEY creation
    @aws_check_state_present
    def _ec2_key(self, module_name, result):
        key = result._result.get('key')
        key_id = key.get('id')
        key_name = key.get('name')
        self.callback._debug(f"Key name {key_name}")

        # Generate amazon.aws.ec2_eni delete !
        return ({
            module_name: {
                'state': 'absent',
                'name': self._to_text(key_name),
            }
        })

    # Called upon TAG creation
    @aws_check_state_present
    def _ec2_tag(self, module_name, result):
        module_args = result._result.get('invocation').get('module_args')
        resource = module_args.get('resource')
        tags = module_args.get('tags')
        self.callback._debug(f"Tags on resource {resource}")

        # Generate amazon.aws.ec2_eni delete !
        tag_dict = {self._to_text(key): self._to_text(value) for key, value in tags.items()}
        return ({
            module_name: {
                'state': 'absent',
                'resource': self._to_text(resource),
                'tags': tag_dict,
            }
        })

    # Called upon S3 Bucket creation
    @aws_check_state_present
    def _s3_bucket(self, module_name, result):
        name = result._result.get('name')
        self.callback._debug(f"S3 bucket {name}")

        # Generate amazon.aws.s3_bucket delete !
        return ({
            module_name: {
                'state': 'absent',
                'name': self._to_text(name),
            }
        })

    # Called upon S3 Object creation
    def _s3_object(self, module_name, result):
        '''
        Many cases according the "mode" parameter:
        "create": used to create Bucket directories
        "copy": copy an object stored in another Bucket
        "put": upload a file
        '''
        module_args = result._result.get('invocation').get('module_args')
        mode = module_args.get('mode')
        bucket_name = module_args.get("bucket")
        self.callback._debug(f"S3 object {bucket_name}")

        if mode == "put" or mode == "copy":
            object_name = module_args.get("object")
            return ({
                module_name: {
                    'mode': 'delobj',
                    'object': self._to_text(object_name),
                    'bucket': self._to_text(bucket_name),
                }
            })

        if mode == "create":
            object_name = module_args.get("object")
            if object_name:
                # delete object
                return ({
                    module_name: {
                        'mode': 'delobj',
                        'object': self._to_text(object_name),
                        'bucket': self._to_text(bucket_name),
                    }
                })

            # delete the whole Bucket (must use another module !)
            return ({
                'amazon.aws.s3_bucket': {
                    'state': 'absent',
                    'bucket': self._to_text(bucket_name),
                }
            })

    # Generate the rollback action
    def _aws_generate_action(self, action, module_name, result):
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
