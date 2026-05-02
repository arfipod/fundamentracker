import os
from google import genai
from dotenv import load_dotenv

# Cargamos tus credenciales exactamente igual que en el otro script
load_dotenv('/home/arfipod/git/fundamentracker/.env')

def listar_modelos():
    print("🔍 Buscando modelos disponibles en tu API...\n")
    
    # Verificamos que la clave se ha cargado bien
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: No se encontró GEMINI_API_KEY en el .env")
        return

    try:
        client = genai.Client()
        
        # client.models.list() devuelve todos los modelos a los que tienes acceso
        modelos = client.models.list()
        
        # Formateamos la salida como una tabla para que sea fácil de leer
        print(f"{'NOMBRE DEL MODELO (ID)':<40} | {'NOMBRE PARA MOSTRAR'}")
        print("-" * 80)
        
        for m in modelos:
            # m.name es el ID que usas en el código (ej. gemini-2.5-flash)
            nombre_id = m.name
            display = m.display_name or "N/A"
            print(f"{nombre_id:<40} | {display}")
            
    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")

if __name__ == "__main__":
    listar_modelos()