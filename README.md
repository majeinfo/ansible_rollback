# Ansible Collection - majeinfo.resource_cleaner

This collection installs a callback plugins that generates 
rollback playbook when a playbook generates dynamic resources
in the Cloud.

In this version, only some of AWS resources types are supported:
EC2 instance, VPC, VPC Subnet, TAG, AMI, Security Group, EIP, ENI, KEY, Volume

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
