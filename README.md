# Akamai Property Manager Ansible Module Example

This is a very simple example module for Ansible that updates and activates and Akamai configuration to staging and/or production networks.
The code follows Ansible's [Developing Modules](https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html) documentation.

## Playbook Parameters
Description: create a new property version based on the production version, updata it with a local rule tree JSON file and activate to staging and/or production

### Options
```    
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
```

## Examples

### Only update the property
```
    - name: Updating Property
    my_namespace.my_collection.property_manager:
        name: 'example-property-name'
        version_notes: 'Created by Ansible Run'
```
### Update and activate the property to staging
```
    - name: Updating and Activating Property to Staging
    my_namespace.my_collection.property_manager:
        name: 'example-property-name'
        activate_staging: true
        version_notes: 'Created by Ansible Run'
```
### Update and activate the property to staging and production
```
    - name: Updating and Activating Property to Staging and Production
    my_namespace.my_collection.property_manager:
        name: 'example-property-name'
        activate_staging: true
        activate_production: true
        version_notes: 'Created by Ansible Run'
```

## Return Values
The response from the API calls.
```
api_*_response:
    description: The responses from the Akamai API calls.
    type: str
    returned: always
    sample: {
            "activationLink": "/papi/v1/properties/prp_123456/activations/atv_12339328"
        }
```

The current property version.
```
current_version:
    description: The current property version active on production.
    type: int
    returned: always
    sample: 399
```
The new version of the property.
```
new_version:
    description: The newly created property version.
    type: str
    returned: always
    sample: '400'
```
The ID of the property.
```
propertyId:
    description: The ID of the property (This is different from the property name).
    type: str
    returned: always
    sample: 'prp_123456'
```

## Playbook Execution
Edit the playbook as needed and then to run it just run:
```
$ ansible-playbook playbook.yml
```

## Resources
- [Akamai OPEN Edgegrid API Clients](https://developer.akamai.com/libraries)
- [Akamai Property Manager API](https://techdocs.akamai.com/cloudlets/v2/reference/api-workflow)