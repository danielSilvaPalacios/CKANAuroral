import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanapi
from ckanapi import RemoteCKAN
import os
import requests
import time
import json
import re
import random
import multiprocessing
import yaml
import traceback  # Import the traceback module



# Setting Global Variables
# Common headers
headers_get = {'accept': 'application/json'}
headers_post = {'accept': 'application/json', 'Content-Type': 'text/plain'}

# API base URL
net_ckan_node = "http://aur-1695287971-proxy-1:8080"




base_url = f"{net_ckan_node}/api/discovery"
base_url_post = f"{net_ckan_node}/api/discovery/remote/semantic"

# Variables to access the ckan api
ckan_url = os.getenv('CKAN_SITE_URL')
ckan_key = os.getenv('CKAN_API_KEY')




import logging

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')





def make_api_request(url, headers, method="GET", payload=None):
    """Make an API request and return the JSON response.

    Parameters:
        url (str): The URL for the API endpoint.
        headers (dict): The HTTP headers.
        method (str, optional): The HTTP method ("GET", "POST", etc.). Defaults to "GET".
        payload (dict, optional): The payload for POST requests. Defaults to None.

    Returns:
        dict: The JSON response from the API or None if an error occurred.
    """
    try:
        response = requests.request(method, url, headers=headers, data=payload)
        response.raise_for_status()

        if response.status_code == 200:
            return response.json()

    except requests.Timeout:
        logging.error(f"Timeout error for request {url}")
    except requests.TooManyRedirects:
        logging.error(f"TooManyRedirects error for request {url}")
    except requests.RequestException as e:
        logging.error(
            f"An error occurred while making the API request to {url}: {e}")

    return None


def get_community_ids(base_url, headers):
    """Fetch and return community IDs.

    Parameters:
        base_url (str): The base URL for the API.
        headers (dict): The HTTP headers.

    Returns:
        list: The list of community IDs.
    """
    urlcommId = f"{base_url}/api/collaboration/communities"
    response = make_api_request(urlcommId, headers)

    if response:
        community_ids = [community['commId']
                        for community in response['message']]
        return community_ids
    else:
        logging.error("Failed to obtain Community IDs")
        return []


def get_comunities():

    # Get Community IDs
    community_ids = get_community_ids(net_ckan_node, headers_get)

    if community_ids:
        logging.error(f"Community IDs obtained: {community_ids}")
    else:
        logging.error("No Community IDs obtained.")

    return community_ids


def process_string(input_string):
    """
    Process a string to avoid special characters and ensure it conforms to the required format to
    avoid the error: ust be purely lowercase alphanumeric (ascii) characters and these symbols: -_
    when registering datasets and organizations in CKAN.

    Parameters:
    - input_string: The input string to be processed.

    Returns:
    - The processed string with special characters removed.
    """

    # Remove whitespace
    processed_string = input_string.replace(" ", "")

    # Convert to lowercase
    processed_string = processed_string.lower()

    # Apply regular expression to remove unwanted characters
    processed_string = re.sub(r"[^a-z0-9\-_'']", "", processed_string)

    logging.error(f"____3____ unique_id_string{processed_string}")

    return processed_string


# _______________SEPARATE ITEMS OIDS______________

def get_unique_ids(array):
    """
    Obtain the OIDs (object IDs) of the objects contained in the nodes to separate the metadata.

    Parameters:
    - array: The input array containing the objects.

    Returns:
    - A tuple containing a list of unique IDs and a list of unique ID strings.
    """

    unique_ids = []
    unique_id_strings = []
    for item in array:
        # Obtain the ID after "graph:"
        _, id_value = item.split('https://oeg.fi.upm.es/wothive/')

        # Verify if the ID is in the list of unique_ids
        if id_value not in unique_ids:
            unique_ids.append(id_value)
            unique_id_strings.append(
                "https://oeg.fi.upm.es/wothive/" + id_value)
    logging.error(f"____2____ unique_id_string{unique_ids}")

    return unique_ids, unique_id_strings




def obtain_metadata(response):
    dataset_descriptions=[]
    organization_descriptions=[]

    logging.error("----")
    logging.error("ENTRA EN EL OBTAIN METADATA")
    logging.error("----")
    logging.error("The response es")
    logging.error(response)
    organization_data = {
        'name': '',
        'title': '',
        'description': ''
    }
    

    # Check if the response contains 'bindings' and if 'bindings' is empty
    bindings = response.get('message', {}).get('results', {}).get('bindings', [])
    if not bindings:
        print("Empty bindings received in response.")
        # Return the initialized empty values
        return dataset_descriptions, [organization_data]



    # Step 1: Obtain a list of all "sub" values
    subs = [binding['sub']['value'] for binding in response['message']['results']['bindings'] if binding['sub']['value'].startswith('https://oeg.fi.upm.es/wothive/')]
    oids, oids_sub=get_unique_ids(subs) 
    #print(oids, oids_sub)
    #print(oids_sub)
    print("Number of Datasets: "+str(len(oids_sub)))
    
    #Create a list of datasets
    thing_descriptions = []
    
    # Step 2-4: Iterate over the "sub" values and create the thing descriptions
    for sub in oids_sub:  # Using set to obtain unique values
        # Step 2: Filter the triples for the current object
        print("OID Resource: "+str(sub))
        filtered_results = [binding for binding in response['message']['results']['bindings'] if sub.__contains__(binding['sub']['value'])]
        
        # Define the dictionary for the dataset information
        dataset_data = {
            'name': '',
            'title': '',
            'groups': [
                {   
                    'name': ''
                }
            ],
            'owner_org': '',
            'description': '',
            'resources': [
                {
                    'name': '',
                    'url': '',
                }
            ]
        }
        


        # Iterate over the triples and obtain the metadata values
        for triple in filtered_results:
            subject = triple['sub']['value']
            predicate = triple['p']['value']
            object_type = triple['o']['type']
            object_value = triple['o']['value']

            # Update dataset_data based on the triple and the information from the WoT TD
            if predicate == 'https://www.w3.org/2019/wot/td#title': #NAME
                dataset_data['name'] = process_string(object_value)
            elif predicate == 'https://www.w3.org/2019/wot/td#serviceName': # RESOURCE - TITLE
                dataset_data['title'] = object_value
                dataset_data['resources'][0]['name'] = object_value
            elif predicate == 'https://www.w3.org/2019/wot/td#hasURL': #RESOURCE - URL
                dataset_data['resources'][0]['url'] = object_value
            elif predicate == 'https://www.w3.org/2019/wot/td#provider': #OWNER ORG
                dataset_data['owner_org'] = process_string(object_value)
                organization_data['name'] = process_string(object_value)
                organization_data['title'] = object_value
                organization_data['description'] = str(object_value) + " description"

            if predicate == 'https://www.w3.org/2019/wot/td#serviceDescription': #DESCRIPTION
                dataset_data['description'] = object_value
            elif predicate == 'https://www.w3.org/2019/wot/td#hasDomain':
                dataset_data['domain'] = object_value
            elif predicate == 'https://www.w3.org/2019/wot/td#hasDomain':
                dataset_data['groups'][0]['name'] = process_string(object_value)

        #append datasets and organization to a single dictionary   
        dataset_descriptions.append(dataset_data) 
        organization_descriptions.append(organization_data) 
        
        logging.error(f"__A__dataset_descriptions{dataset_descriptions}")
        logging.error(f"__B__organization_descriptions{organization_descriptions}")
        logging.error(f"__C__organization_data{organization_data}")
        
   
    # Step 5: Return the list of datasets
    return dataset_descriptions, organization_descriptions



def data_org(commId):
    logging.error("base_url: "+str(base_url))
    logging.error("commId: "+str(commId))
    # Request to obtain the AGIDs
    response_data = make_api_request(
        f"{base_url}/nodes/community/{commId}", headers_get)

    datasets = []
    organization = []

    list_datasets = []
    list_organizations = []

    if response_data is not None:
        logging.error("____0____Request to obtain the AGIDs: OK")
        logging.error("Print response data:")
        logging.error(response_data)
        data = response_data
        messages = data.get('message', [])

        # Iterar a través de cada mensaje para obtener el agid
        num_items=0
        for message in messages:
            agid = message.get('agid')
            logging.error(f"Processing AGID: {agid}")

            # Realizar una nueva solicitud GET para cada agid
            oids_data = make_api_request(
                f"{base_url}/remote/semantic/predefined/getOids?agids={agid}", headers_get)

            if oids_data is not None:
                oids_data = oids_data
                bindings = oids_data.get('message', {}).get(
                    'results', {}).get('bindings', [])
                logging.error("bindings: "+str(bindings))

                # Contar y mostrar el número de oids
                num_oids = len(bindings)
                logging.error(f"Number of OIDs: {num_oids}")

                # Extract and print the names of each oid
                for binding in bindings:
                    logging.error("Entra a bucle de OIDS")
                    oid_value = binding.get('oid', {}).get('value', '')
                    oid_name = binding.get('name', {}).get('value', '')
                    logging.error(f"OID: {oid_value}, Name: {oid_name}")

                # Realizar una solicitud POST para cada agid
                query = '''
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
                PREFIX wot: <https://www.w3.org/2019/wot/td#> 
                SELECT distinct ?p ?o ?sub WHERE { 
                ?sub rdf:type wot:Service . 
                ?sub ?p ?o .}
                '''
                service_data = make_api_request(
                    f"{base_url_post}?agids={agid}", headers_post, method="POST", payload=query)

                # Verificar si la solicitud POST fue exitosa
                if service_data is not None:
                    post_data = service_data
                    # Obtain the metadata of all the datasets
                    datasets, organization = obtain_metadata(post_data)

                    list_datasets.append(datasets)
                    list_organizations.append(organization)

                    for data in datasets:
                        name = data["name"]
                        title = data["title"]
                        domain = data["domain"]
                        description = data["description"]
                        owner_org = data["owner_org"]
                        resources_name = data["resources"][0]["name"]
                        resources_url = data["resources"][0]["url"]

                        logging.error(json.dumps(data, indent=4))

                    num_items = len(datasets)

                    # logging.error(f"POST response for agid {agid}: {post_data}")

            else:
                logging.error(f"Failed to fetch OIDs for agid {agid}")

        logging.error(f"Total number of datasets: " + str(num_items))

    else:
        logging.error(f"Failed to fetch community data for commId {commId}")

    logging.error(f"datasets: {list_datasets}")
    logging.error(f"organization: {list_organizations}")
    return list_datasets, list_organizations


# _______________CREATE DATASETS ON CKAN______________

data={'name': 'service_bifrost', 'title': 'Datasets', 'groups': [{'name': ''}], 
      'owner_org': 'universityofdeusto', 'description': '', 
      'resources': [{'name': 'Datasets', 'url': 'http://127.0.0.1:4000/get_data'}], 
      'domain': 'Mobility', 'notes': 'Encontrar Datasets'}
 
org={'name': 'service_bifrost', 'title': 'Datasets', 
      'description': 'University of Deusto description'}


def create_datasets_CKAN(organization_data, dataset_data):
    logging.error("Entra a create_datasets_CKAN")
    logging.error(f"organization_data: {organization_data}")
    

    # Connect with ckan
    ckan = ckanapi.RemoteCKAN(ckan_url, apikey=ckan_key)

    logging.error(f"CKAN_CREATE_DATASETS: dataset_data {dataset_data}")
    # Manage organizations
    try:
        # Check if the organization exists
        if len(dataset_data) > 0:
            logging.error(f"Dataset data: {dataset_data}")
            val = dataset_data['owner_org']
            logging.error(f"val is: {val}")

            ckan.action.organization_show(id=val)
            logging.error('____8____Organization already exists!')
            

    except ckanapi.NotFound:
        # If the organization doesn't exist, create it.
        try:
            if organization_data['name'] != '':
                logging.error(f"Try to create organization***")
                logging.error(f"organization_data: {organization_data}")
                ckan.action.organization_create(**organization_data)
                logging.error('____9____Organization created successfully!')
        except Exception as e:
            error_traceback = traceback.format_exc()  # Get the traceback of the exception
            logging.error(f"An error occurred creation of the  dataset: {e}\n{error_traceback}")  
            logging.error('Organization wasnt created because it exists!!')
    # except ValidationError as e:
    #     logging.error('____10____Failed to create organization:', e)

    # Create a new dataset on CKAN
    try:
        # If it does note exists, create it
        logging.error(f"Try to create dataset***")
        logging.error(f"datasets_data: {dataset_data}")
        ckan.action.package_create(**dataset_data)
        logging.error('____11____Dataset created successfully')
    except ckanapi.errors.ValidationError:
        # If it trows an error, it means that the dataset already exists. Do nothing.
        logging.error('____12____Dataset already exists')
    except Exception as e:
        logging.error('____13____Failed to create dataset: %s', e)

    return dataset_data


# ______________DELETE DATASETS FROM CKAN______________

def delete_dataset_CKAN(dataset_name):
    """
    Deletes a dataset from CKAN.

    Parameters:
    - dataset_name: The name or ID of the dataset to be deleted.

    Returns:
    - None
    """

    # Create a CKAN API client
    ckan = ckanapi.RemoteCKAN(ckan_url, apikey=ckan_key)

    try:
        # Delete the dataset
        ckan.action.package_delete(id=dataset_name)
        logging.error(f"____17____Dataset '{dataset_name}' deleted from CKAN.")
    except ckanapi.CKANAPIError as e:
        logging.error(
            f"____18____An error occurred while deleting dataset '{dataset_name}': {e}")


# ______________UPDATE DATASETS ON CKAN BASED ON THE REGISTERED ITEMS IN THE NODES______________

def update_datasets(commId):

    logging.error("Entra a update_datasets")

    existing_datasets = get_ckan_datasets()

    # Create a list of existing dataset names
    logging.error("____19____Existing dataset names: " + str(existing_datasets))

    datasets, organizations = data_org(commId)


    # Flatten the datasets list to get all dictionaries in one list
    flattened_datasets = [data for sublist in datasets for data in sublist if isinstance(data, dict)]

    # Check if the dataset exists in CKAN and delete if not found in the obtained results
    for dataset_name in existing_datasets:
        if dataset_name not in [data['name'] for data in flattened_datasets]:
            logging.error(f"____20____Dataset '{dataset_name}' not found in the obtained results. Deleting from CKAN...")
            delete_dataset_CKAN(dataset_name)

    # # Check if the dataset exists in CKAN and delete if not found in the obtained results
    # for dataset_name in existing_datasets:
    #     if dataset_name not in [data['name'] for data in datasets]:
    #         logging.error(
    #             f"____20____Dataset '{dataset_name}' not found in the obtained results. Deleting from CKAN...")
    #         delete_dataset_CKAN(dataset_name)

    logging.error("____21____Dataset deletion completed.")

    logging.error("datasets: "+str(datasets))
    logging.error("organizations: "+str(organizations))
    # #For every dataset obtained from the query to the community, call to the funtion create_datasets_CKAN to create the datasets on CKAN
    for data, orga in zip(datasets, organizations):
        logging.error("data: "+str(data))
        logging.error("orga: "+str(orga))
        # Check if the sublists are not empty
        if data != []:
            for data_sub,org_sub in zip(data,orga):
           
                logging.error("data_sub: "+str(data_sub))
                logging.error("org_sub: "+str(org_sub))

                create_datasets_CKAN(org_sub, data_sub)
        else:
            print("The list is empty.")
        
            

            


def get_ckan_datasets():
    """
    #Retrieves datasets from a CKAN database using the CKAN API.    
    #Returns a list of dataset dictionaries retrieved from the CKAN database.

    Returns:
    - The list of datasets names retrieved from the CKAN database.
    """
    # Create a CKAN API client
    logging.error(f"ckan: {ckan_url} {ckan_key}")

    ckan = ckanapi.RemoteCKAN(ckan_url, apikey=ckan_key)

    try:
        # Retrieve the list of datasets
        datasets = ckan.action.package_list()
        # logging.error(datasets)
        logging.error(f"RECUPERA LA LISTA DE DATASETS CKAN ___{datasets}")
        return datasets

    except ckanapi.NotFound:
        logging.error("____14____CKAN instance not found.")
    except ckanapi.NotAuthorized:
        logging.error("____15____Not authorized to access CKAN API.")
    except ckanapi.CKANAPIError:
        logging.error("____16____An error occurred while retrieving datasets.")

    return []

     





class AuroralIntegrationPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    #plugins.implements(plugins.IPluginObserver)

    # IPluginObserver
    def update_config(self, config_):
        logging.error("update config")
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'auroral_integration')
        




def get_or_create_yaml(file_path):
    # If the file doesn't exist, create it with the initial value
    if not os.path.exists(file_path):
        # Initialize the data
        data = {"val": 0}

        # Write the data to the YAML file
        with open(file_path, 'w') as file:
            yaml.dump(data, file)
    else:
        # If the file exists, read its contents
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file) or {}

    return data


def updateControl(data):
    try:
        with open(file_path, 'w') as file:
            yaml.dump(data, file)
    except PermissionError:
        # Handle the permission error
        logging.error("Permission error occurred while saving control.yaml")
    except Exception as e:
        # Handle other exceptions
        logging.error(f"An error occurred while saving control.yaml: {e}")


def executeUpdate():


    logging.error('COMIENZA EL HILO DE EJECUCION')
    logging.error(f"El valor yml es:{control['val']}")
  
        
    logging.error("_____________________Scheduler started")


    time.sleep(2) #Espero que el servidor inicie
    
    logging.error('Comienza HILO EJECUCION')
    
    commIds = None
    
   
    logging.error('Te comminity id is:'+str(commIds))
    if commIds == None:            
        commIds = get_comunities()
    
    logging.error('Te comminity id 2 is:'+str(commIds))

    for commId in commIds:
        try:
            update_datasets(commId)
            logging.error("Updated datasets successfully.")
        except Exception as e:  # Catching all exceptions for this example
            error_traceback = traceback.format_exc()  # Get the traceback of the exception
            logging.error(f"An error occurred during dataset update: {e}\n{error_traceback}")  # Log the error along with its traceback
        
    logging.error("Sleeping for 60 seconds...")
    time.sleep(60)

    toolkit.enqueue_job(executeUpdate, rq_kwargs={"timeout": 900})
        
    #logging.error(f"Termina el hilo de ejecucion!!!")

file_path = 'control.yaml'
control = get_or_create_yaml(file_path) #Iniciate in 0 if dont exists
if control["val"] == 0:
    logging.error(f"Envia el proceso al hilo")

    # Using a large number to represent a long timeout (e.g., 15 min = 900 seg)
    toolkit.enqueue_job(executeUpdate, rq_kwargs={"timeout": 900})

    logging.error(f"Set value to 1")
    data = {"val": 1}     
    updateControl(data)

    
