import json
from config import DATASET_PATH

# Función para cargar el dataset desde el archivo JSON
def cargar_dataset():
    
	try:
		# Abre el archivo dataset.json en modo lectura y codificación utf-8
		with open(DATASET_PATH, 'r', encoding='utf-8') as f:
			# Carga y retorna el contenido como una lista de diccionarios
			return json.load(f)
	except Exception:
		# Si hay error (por ejemplo, el archivo no existe), retorna una lista vacía
		return []

# Busca una pregunta exacta en el dataset y retorna la respuesta si la encuentra
def buscar_en_dataset(pregunta, dataset):
	# Normaliza la pregunta (quita espacios y pasa a minúsculas)
	pregunta = pregunta.strip().lower()
	# Recorre cada elemento del dataset
	for item in dataset:
		# Compara la pregunta del usuario con la del dataset (normalizada)
		if item['pregunta'].strip().lower() == pregunta:
			# Si hay coincidencia exacta, retorna la respuesta
			return item['respuesta']
	# Si no encuentra coincidencia, retorna None
	return None
