import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanapi
from ckanapi import RemoteCKAN
import os
import requests
import time
import json
import re

import threading

class AuroralIntegrationPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)

    def __init__(self,name=None):

        # Setting Global Variables
        # Common headers
        self.headers_get = {'accept': 'application/json'}
        self.headers_post = {'accept': 'application/json', 'Content-Type': 'text/plain'}

        # API base URL
        self.net_ckan_node = "http://aur-1695287971-proxy-1:8080"
        self.base_url = f"{self.net_ckan_node}/api/discovery"
        self.base_url_post = f"{self.net_ckan_node}/api/discovery/remote/semantic"

        # Variables to access the ckan api
        self.ckan_url = os.getenv('CKAN_SITE_URL')
        self.ckan_key = os.getenv('CKAN_API_KEY')

        self.commId = None

        #Inicio el hilo:
        threading.Thread(target=self.executeUpdate).start()

    

    # IPluginObserver
    def update_config(self, config_):
        print("update config")
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'auroral_integration')

   
    def executeUpdate(self):
        time.sleep(2) #Espero que el servidor inicie
        print('COMIENZA EL HILO DE EJECUCION')
        print('Comienza HILO EJECUCION')
        commId=None    

        commId = self.get_comunities()

        # cont=0
        # while True:
        #     cont=cont+1
        #     print('Entra en el while '+str(cont)+' times.')
        #     if commId == None:            
        #         commId = self.get_comunities()
            
        #     try:
        #         self.update_datasets()
        #         print("Updated datasets successfully.")
        #     except Exception as e:
        #         print(f"An error occurred during dataset update: {e}")
        #     finally:
        #         print("Sleeping for 60 seconds...")
        #         time.sleep(5)
    
 

    def make_api_request(self,url, headers, method="GET", payload=None):
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
            print(f"Timeout error for request {url}")
        except requests.TooManyRedirects:
            print(f"TooManyRedirects error for request {url}")
        except requests.RequestException as e:
            print(
                f"An error occurred while making the API request to {url}: {e}")

        return None


    def get_community_ids(self,base_url, headers):
        """Fetch and return community IDs.

        Parameters:
            base_url (str): The base URL for the API.
            headers (dict): The HTTP headers.

        Returns:
            list: The list of community IDs.
        """
        urlcommId = f"{base_url}/api/collaboration/communities"
        response = self.make_api_request(urlcommId, headers)

        if response:
            community_ids = [community['commId']
                            for community in response['message']]
            return community_ids
        else:
            print("Failed to obtain Community IDs")
            return []


    def get_comunities(self):

        # Get Community IDs
        community_ids = self.get_community_ids(self.net_ckan_node, self.headers_get)

        if community_ids:
            print(f"Community IDs obtained: {community_ids}")
        else:
            print("No Community IDs obtained.")

        return community_ids


    def process_string(self,input_string):
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

        print(f"____3____ unique_id_string{processed_string}")

        return processed_string


    # _______________SEPARATE ITEMS OIDS______________

    def get_unique_ids(self,array):
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
        print(f"____2____ unique_id_string{unique_ids}")

        return unique_ids, unique_id_strings


    def obtain_metadata(self,response):
        dataset_descriptions = []
        organization_descriptions = []
        # Step 1: Obtain a list of all "sub" values
        subs = [binding['sub']['value'] for binding in response['message']['results']
                ['bindings'] if binding['sub']['value'].startswith('https://oeg.fi.upm.es/wothive/')]
        oids, oids_sub = self.get_unique_ids(subs)
        # print(oids, oids_sub)
        # print(oids_sub)
        print("Number of Datasets: "+str(len(oids_sub)))

        # Create a list of datasets
        thing_descriptions = []

        # Step 2-4: Iterate over the "sub" values and create the thing descriptions
        for sub in oids_sub:  # Using set to obtain unique values
            # Step 2: Filter the triples for the current object
            # print("OID Dataset: "+str(sub))
            filtered_results = [binding for binding in response['message']
                                ['results']['bindings'] if sub.__contains__(binding['sub']['value'])]

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
            organization_data = {
                'name': '',
                'title': '',
                'description': ''
            }
            for triple in filtered_results:
                subject = triple['sub']['value']
                predicate = triple['p']['value']
                object_type = triple['o']['type']
                object_value = triple['o']['value']

                # Update dataset_data based on the triple and the information from the WoT TD
                if predicate == 'https://www.w3.org/2019/wot/td#title':  # NAME
                    dataset_data['name'] = self.process_string(object_value)
                    organization_data['name'] = self.process_string(object_value)
                elif predicate == 'https://www.w3.org/2019/wot/td#serviceName':  # RESOURCE - TITLE
                    dataset_data['title'] = object_value
                    organization_data['title'] = object_value
                    dataset_data['resources'][0]['name'] = object_value
                elif predicate == 'https://www.w3.org/2019/wot/td#hasURL':  # RESOURCE - URL
                    dataset_data['resources'][0]['url'] = object_value
                elif predicate == 'https://www.w3.org/2019/wot/td#provider' or predicate == 'https://www.w3.org/2019/wot/td#owner_org' or predicate == 'https://auroral.iot.linkeddata.es/def/core#provider':  # OWNER ORG
                    dataset_data['owner_org'] = self.process_string(object_value)
                    organization_data['description'] = str(
                        object_value) + " description"

                if predicate == 'https://www.w3.org/2019/wot/td#serviceDescription':  # DESCRIPTION
                    dataset_data['notes'] = object_value
                elif predicate == 'https://www.w3.org/2019/wot/td#hasDomain':
                    dataset_data['domain'] = object_value
                elif predicate == 'https://www.w3.org/2019/wot/td#hasDomain':
                    dataset_data['groups'][0]['name'] = self.process_string(
                        object_value)

            # print(json.dumps(dataset_data, indent=4))
            # append datasets to a single dictionary
            organization_descriptions.append(organization_data)
            dataset_descriptions.append(dataset_data)

        # Step 5: Return the list of datasets
        return dataset_descriptions, organization_descriptions


    def data_org(self):
        print("base_url: "+str(self.base_url))
        print("commId: "+str(self.commId))
        # Request to obtain the AGIDs
        response_data = self.make_api_request(
            f"{self.base_url}/nodes/community/{self.commId}", self.headers_get)

        datasets = []
        organization = []

        list_datasets = []
        list_organizations = []

        if response_data is not None:
            print("____0____Request to obtain the AGIDs: OK")
            data = response_data.json()
            messages = data.get('message', [])

            # Iterar a través de cada mensaje para obtener el agid
            for message in messages:
                agid = message.get('agid')
                print(f"Processing AGID: {agid}")

                # Realizar una nueva solicitud GET para cada agid
                oids_data = self.make_api_request(
                    f"{self.base_url}/remote/semantic/predefined/getOids?agids={agid}", self.headers_get)

                if oids_data is not None:
                    oids_data = oids_data.json()
                    bindings = oids_data.get('message', {}).get(
                        'results', {}).get('bindings', [])
                    print("bindings: "+str(bindings))

                    # Contar y mostrar el número de oids
                    num_oids = len(bindings)
                    print(f"Number of OIDs: {num_oids}")

                    # Extract and print the names of each oid
                    for binding in bindings:
                        print("Entra a bucle de OIDS")
                        oid_value = binding.get('oid', {}).get('value', '')
                        oid_name = binding.get('name', {}).get('value', '')
                        print(f"OID: {oid_value}, Name: {oid_name}")

                    # Realizar una solicitud POST para cada agid
                    query = '''
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
                    PREFIX wot: <https://www.w3.org/2019/wot/td#> 
                    SELECT distinct ?p ?o ?sub WHERE { 
                    ?sub rdf:type wot:Service . 
                    ?sub ?p ?o .}
                    '''
                    service_data = self.make_api_request(
                        f"{self.base_url_post}?agids={agid}", self.headers_post, method="POST", payload=query)

                    # Verificar si la solicitud POST fue exitosa
                    if service_data is not None:
                        post_data = service_data.json()
                        # Obtain the metadata of all the datasets
                        datasets, organization = self.obtain_metadata(post_data)

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

                            print(json.dumps(data, indent=4))

                        num_items = len(datasets)

                        # print(f"POST response for agid {agid}: {post_data}")

                else:
                    print(f"Failed to fetch OIDs for agid {agid}")

            print(f"Total number of datasets: " + str(num_items))

        else:
            print(f"Failed to fetch community data for commId {self.commId}")

        print(f"datasets: {list_datasets}")
        print(f"organization: {list_organizations}")
        return list_datasets, list_organizations


    # _______________CREATE DATASETS ON CKAN______________

    def create_datasets_CKAN(self,organization_data, dataset_data):
        print("Entra a create_datasets_CKAN")
        print(f"organization_data: {organization_data}")
        print(f"datasets_data: {dataset_data}")

        # Connect with ckan
        ckan = ckanapi.RemoteCKAN(self.ckan_url, apikey=self.ckan_key)

        print(f"CKAN_CREATE_DATASETS: dataset_data {dataset_data}")
        # Manage organizations
        try:
            # Check if the organization exists
            if len(dataset_data) > 0:
                print(f"Dataset data: {dataset_data}")
                val = dataset_data['owner_org']
                ckan.action.organization_show(id=val)
                print('____8____Organization already exists!')
                print()

        except ckanapi.NotFound:
            # If the organization doesn't exist, create it
            ckan.action.organization_create(**organization_data)
            print('____9____Organization created successfully!')
        # except ValidationError as e:
        #     print('____10____Failed to create organization:', e)

        # Create a new dataset on CKAN
        try:
            # If it does note exists, create it
            ckan.action.package_create(**dataset_data)
            print('____11____Dataset created successfully')
        except ckanapi.errors.ValidationError:
            # If it trows an error, it means that the dataset already exists. Do nothing.
            print('____12____Dataset already exists')
        except Exception as e:
            print('____13____Failed to create dataset:', e)

        return dataset_data


    # ______________DELETE DATASETS FROM CKAN______________

    def delete_dataset_CKAN(self,dataset_name):
        """
        Deletes a dataset from CKAN.

        Parameters:
        - dataset_name: The name or ID of the dataset to be deleted.

        Returns:
        - None
        """

        # Create a CKAN API client
        ckan = ckanapi.RemoteCKAN(self.ckan_url, apikey=self.ckan_key)

        try:
            # Delete the dataset
            ckan.action.package_delete(id=dataset_name)
            print(f"____17____Dataset '{dataset_name}' deleted from CKAN.")
        except ckanapi.CKANAPIError as e:
            print(
                f"____18____An error occurred while deleting dataset '{dataset_name}': {e}")


    # ______________UPDATE DATASETS ON CKAN BASED ON THE REGISTERED ITEMS IN THE NODES______________

    def update_datasets(self):

        print("Entra a update_datasets")

        existing_datasets = self.get_ckan_datasets()

        # Create a list of existing dataset names
        print("____19____Existing dataset names: " + str(existing_datasets))

        datasets, organizations = self.data_org()

        # Check if the dataset exists in CKAN and delete if not found in the obtained results
        for dataset_name in existing_datasets:
            if dataset_name not in [data['name'] for data in datasets]:
                print(
                    f"____20____Dataset '{dataset_name}' not found in the obtained results. Deleting from CKAN...")
                self.delete_dataset_CKAN(dataset_name)

        print("____21____Dataset deletion completed.")

        print("datasets: "+str(datasets))
        print("organizations: "+str(organizations))
        # #For every dataset obtained from the query to the community, call to the funtion create_datasets_CKAN to create the datasets on CKAN
        for data, orga in zip(datasets, organizations):
            print("Entra a bucle de datasets")
            self.create_datasets_CKAN(orga, data)


    def get_ckan_datasets(self):
        """
        #Retrieves datasets from a CKAN database using the CKAN API.    
        #Returns a list of dataset dictionaries retrieved from the CKAN database.

        Returns:
        - The list of datasets names retrieved from the CKAN database.
        """
        # Create a CKAN API client
        print(f"ckan: {self.ckan_url} {self.ckan_key}")

        ckan = ckanapi.RemoteCKAN(self.kan_url, apikey=self.ckan_key)

        try:
            # Retrieve the list of datasets
            datasets = ckan.action.package_list()
            # print(datasets)
            print(f"RECUPERA LA LISTA DE DATASETS CKAN ___{datasets}")
            return datasets

        except ckanapi.NotFound:
            print("____14____CKAN instance not found.")
        except ckanapi.NotAuthorized:
            print("____15____Not authorized to access CKAN API.")
        except ckanapi.CKANAPIError:
            print("____16____An error occurred while retrieving datasets.")

        return []
    
     