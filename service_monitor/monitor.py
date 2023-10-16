import docker
import yaml
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def read_yaml():
    with open('/app/src/ckanext-testapi/ckanext/testapi/control.yaml', 'r') as file:
        data = yaml.safe_load(file)
    with open('/app/src/ckanext-auroral_integration/ckanext/auroral_integration/control.yaml', 'r') as file:
        data = yaml.safe_load(file)
    return data
    
def save_yaml(data):
    with open('/app/src/ckanext-testapi/ckanext/testapi/control.yaml', 'w') as file:
        yaml.dump(data, file)
    with open('/app/src/ckanext-auroral_integration/ckanext/auroral_integration/control.yaml', 'w') as file:
        yaml.dump(data, file)
        
        
def monitor_container_logs(container_id):
    try:
        client = docker.from_env()
        container = client.containers.get(container_id)
        logs = container.logs(stream=True, follow=True)
        for log in logs:
            result = log.decode().strip()
            if "Running CKAN on http://0.0.0.0:5000" in result:
                
                control = read_yaml()
                control["val"] = 1       
                    
                save_yaml(control)
                
                logger.info('dato cambiado ********************')
                
    except docker.errors.NotFound as e:
        print(f"El contenedor con ID {container_id} no fue encontrado.")
    except docker.errors.APIError as e:
        print(f"Error en la API de Docker: {e}")
        
        


if __name__ == "__main__":
    logger.info('________________Iniciando monitor de contenedor________________')
    container_id_to_monitor = "ckan-dev"  # Reemplazar con el ID del contenedor
    control = read_yaml()
    control["val"] = 0       
    save_yaml(control)
    monitor_container_logs(container_id_to_monitor)
    
    