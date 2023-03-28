#!/usr/bin/python3

# Copyright: (c) 2023, Jaime Escalona <jaescalo@akamai.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
import time
import re
import json
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
import os
from urllib.parse import urljoin
from ansible.module_utils.basic import AnsibleModule
__metaclass__ = type

#  Ansible's online module documentation is generated from the DOCUMENTATION blocks
DOCUMENTATION = r'''
---
module: property_manager

short_description: Updates Akamai Properties in Property Manager

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: create a new property version based on the production version, updata it with a local rule tree JSON file and activate to staging and/or production

options:
    name:
        description: This is the property name to send update.
        required: true
        type: str
    activate_staging:
        description: Activate the property on the STAGING network.
        required: false
        type: bool
    activate_production:
        description: Activate the property on the PRODUCTION network.
        required: false
        type: bool
    version_notes:
        description: These are the property version notes.
        required: true
        type: str

author:
    - Jaime Escalona (@jaescalo)
'''

# Examples for the documentation
EXAMPLES = r'''
# Only update the property
- name: Updating Property
  my_namespace.my_collection.property_manager:
    name: 'example-property-name'
    version_notes: 'Created by Ansible Run'

# Update and activate the property to staging
- name: Updating and Activating Property to Staging
  my_namespace.my_collection.property_manager:
    name: 'example-property-name'
    activate_staging: true
    version_notes: 'Created by Ansible Run'

# Update and activate the property to staging and production
- name: Updating and Activating Property to Staging and Production
  my_namespace.my_collection.property_manager:
    name: 'example-property-name'
    activate_staging: true
    activate_production: true
    version_notes: 'Created by Ansible Run'
'''

# Document the information the module returns for use by other modules.
RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
api_*_response:
    description: The responses from the Akamai API calls.
    type: str
    returned: always
    sample: {
            "activationLink": "/papi/v1/properties/prp_123456/activations/atv_12339328"
        }

current_version:
    description: The current property version active on production.
    type: int
    returned: always
    sample: 399

new_version:
    description: The newly created property version.
    type: str
    returned: always
    sample: '400'

propertyId:
    description: The ID of the property (This is different from the property name).
    type: str
    returned: always
    sample: 'prp_123456'
'''


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(type='str', required=True),
        version_notes=dict(type='str', required=True),
        activate_staging=dict(type='bool', default=False),
        activate_production=dict(type='bool', default=False)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    global result
    result = dict(
        changed=False,
        failed=False,
        propertyId='',
        current_version='',
        new_version=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    global module
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    search_property(module.params['name'])
    create_new_property_version(
        result['propertyId'], result['current_version'])
    update_property(module.params['name'],
                    result['propertyId'], result['new_version'])

    if module.params['activate_staging']:
        activate_property(result['propertyId'], network='STAGING')
    if module.params['activate_production']:
        activate_property(result['propertyId'], network='PRODUCTION')

    # use whatever logic you need to determine whether or not this module
    # made any modifications to your target
    # if module.params['new']:
    #    result['changed'] = True

    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    if module.params['name'] == 'fail me':
        module.fail_json(msg='You requested this to fail', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def error_handling(response, action):
    if response.status_code not in [200, 201, 204]:
        module.fail_json(
            msg='Error Response Received from API Endpoint', **result)
    elif action == 'search' and not json.loads(response.text)['versions']['items']:
        module.fail_json(msg='Property Not Found', **result)
    return


def search_property(property_name):
    headers = {'content-type': 'application/json'}
    # The accounSwitchKey query param is used to manage multiple accounts with a single API credentials. You must remove it if this is not the case.
    request_body = {
        'propertyName': property_name
    }
    response = session.post(urljoin(baseurl, 'papi/v1/search/find-by-value'),
                            headers=headers, json=request_body)
    response_json_object = json.loads(response.text)
    result['api_search_response'] = response_json_object
    error_handling(response, action='search')

    for activation in response_json_object['versions']['items']:
        if activation['productionStatus'] == 'ACTIVE':
            result['current_version'] = activation['propertyVersion']
            result['propertyId'] = activation['propertyId']
    return


def create_new_property_version(property_id, version):
    headers = {'content-type': 'application/json'}
    request_body = {
        'createFromVersion': version
    }
    response = session.post(urljoin(baseurl, 'papi/v1/properties/{}/versions'.format(
        property_id)), headers=headers, json=request_body)
    response_json_object = json.loads(response.text)
    result['api_creation_response'] = response_json_object
    error_handling(response, action='create')

    new_version = re.findall(
        '.+\/(\d+)\?.+', response_json_object['versionLink'])
    result['new_version'] = new_version[0]
    result['changed'] = True
    return


def update_property(property_name, property_id, new_version):
    # Function to load request body in JSON format

    with open('./ruletree/' + property_name + '.ruletree.json', "r") as body:
        request_body = json.load(body)

    request_body['comments'] = module.params['version_notes']
    headers = {'content-type': 'application/json'}

    response = session.put(urljoin(baseurl, 'papi/v1/properties/{}/versions/{}/rules'.format(
        property_id, new_version)), headers=headers, json=request_body)
    response_json_object = json.loads(response.text)
    #result['api_update_response'] = response_json_object
    error_handling(response, action='update')

    return


def activate_property(property_id, network):
    headers = {'content-type': 'application/json'}
    request_body = {
        'acknowledgeAllWarnings': 'true',
        'network': network,
        'notifyEmails': ['noreply@example.com'],
        'propertyVersion': result['new_version'],
        'note': module.params['version_notes']
    }
    response = session.post(urljoin(baseurl, 'papi/v1/properties/{}/activations'.format(
        property_id)), headers=headers, json=request_body)
    response_json_object = json.loads(response.text)
    result['api_activation_response'] = response_json_object
    error_handling(response, action='activate')

    activation_link = response_json_object['activationLink']

    while (True):
        response = session.get(urljoin(baseurl, activation_link))
        response_json_object = json.loads(response.text)
        if response_json_object['activations']['items'][0]['status'] == 'ACTIVE':
            break
        time.sleep(10)
    return

# Initialize the authorization parameters for the API calls
def config_init():
    rc_path = os.path.expanduser('~/.edgerc')
    # EdgeRc builds the Akamai API Authorization header based on the credentials stored in the ~/.edgerc
    edgerc = EdgeRc(rc_path)

    global baseurl
    baseurl = 'https://%s' % edgerc.get('default', 'host')

    global session
    session = requests.Session()
    session.auth = EdgeGridAuth.from_edgerc(edgerc, 'default')

    return


def main():
    config_init()
    run_module()


if __name__ == '__main__':
    main()

# To run the module: $ ansible-playbook playbook.yml
