# Ansible Collection - majeinfo.resource_cleaner

This collection installs a callback plugins that generates 
rollback playbook when a playbook generates dynamic resources in the Cloud.

In this version, only some of AWS resources types are supported:
EC2 instance, VPC, VPC Subnet, TAG, AMI, Security Group, EIP, ENI, KEY, Volume
(see the list os supported modules below)

In order to enable this Callback Plugin, add the following parameters
in your ansible.cfg file :

```
[defaults]
callbacks_enabled = resource_cleaner
callback_plugins = majeinfo/resource_cleaner/plugins/callback

[resource_cleaner]
playbook_output_path = ./rollback
log_level = debug
```

Now, if you run a Playbook, a rollback Playbook will be created
under the ./rollback directory. This rollback Playbook can then be
played to delete the resources previously created.

LIMITS AND BUGS:

- amazon.aws.ec2_vpc_nat_gateway: 
  when creating a NAT Gateway with a dynamically created EIP, the EIP is not deleted on rollback

- amazon.aws.s3_object:
  when creating a directory in a S3 bucket, it is not deleted when using "mode: delobj" on rollback

SUPPORTED MODULES:

For AWS:

amazon.aws.ec2_ami
amazon.aws.ec2_eip
amazon.aws.ec2_eni
amazon.aws.ec2_instance
amazon.aws.ec2_key
amazon.aws.ec2_launch_template_
amazon.aws.ec2_placement_group
amazon.aws.ec2_security_group
amazon.aws.ec2_snapshot
amazon.aws.ec2_tag
amazon.aws.ec2_vol
amazon.aws.ec2_vpc_dhcp_option
amazon.aws.ec2_vpc_endpoint
amazon.aws.ec2_vpc_igw
amazon.aws.ec2_vpc_nat_gateway
amazon.aws.ec2_vpc_net
amazon.aws.ec2_vpc_route_table
amazon.aws.ec2_vpc_subnet
amazon.aws.s3_bucket
amazon.aws.s3_object

