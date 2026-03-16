import cv2
from ultralytics import YOLO
import socket

# --- CONFIGURACIÓN DE RED HACIA EL ESP8266 ---
ESP_IP = "IPESPOMICROCONTROLADOR" # <--- ¡CAMBIA ESTO POR LA IP DE TU ESP8266!
PUERTO = 4210
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Cargando IA...")
model = YOLO('best.pt')

# Iniciar cámara (usa 0, 1 o la que corresponda a la tuya)
cap = cv2.VideoCapture(1) 

ANCHO_ZONA_MUERTA = 100
ultimo_comando_enviado = ""

while True:
    ret, frame = cap.read()
    if not ret:
        break

    alto, ancho, _ = frame.shape
    centro_imagen = ancho // 2

    # Detectar personas
    resultados = model(frame, classes=0, verbose=False)

    # Lista para guardar info de todas las personas detectadas
    personas = []

    for r in resultados:
        for caja in r.boxes:
            x1, y1, x2, y2 = map(int, caja.xyxy[0])
            
            # Calcular el "tamaño" de la persona en pantalla (Área)
            area = (x2 - x1) * (y2 - y1)
            centro_x = int((x1 + x2) / 2)
            
            personas.append({
                "centro_x": centro_x, 
                "area": area, 
                "box": (x1, y1, x2, y2)
            })

    # Ordenar a las personas de mayor a menor tamaño
    personas.sort(key=lambda p: p["area"], reverse=True)

    # Nos quedamos SOLO con las 2 primeras (los tiradores principales)
    tiradores_principales = personas[:2]

    accion = "ESPERANDO..."
    color_accion = (200, 200, 200)

    # Evaluamos si hay 1 o 2 personas en pantalla
    if len(tiradores_principales) > 0:
        
        if len(tiradores_principales) == 1:
            # LÓGICA 1: Si hay solo 1 persona, el objetivo es esa persona
            objetivo_x = tiradores_principales[0]["centro_x"]
            x1, y1, x2, y2 = tiradores_principales[0]["box"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "Siguiendo a 1", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        else:
            # LÓGICA 2: Si hay 2 personas, calculamos el centro entre ellos dos
            t1_x = tiradores_principales[0]["centro_x"]
            t2_x = tiradores_principales[1]["centro_x"]
            objetivo_x = int((t1_x + t2_x) / 2)
            
            for t in tiradores_principales:
                x1, y1, x2, y2 = t["box"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, "Centrando a 2", (objetivo_x + 10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Dibujar la línea azul que queremos seguir (ya sea el centro de 1 o el medio de 2)
        cv2.line(frame, (objetivo_x, 0), (objetivo_x, alto), (255, 255, 0), 3)

# Lógica de movimiento
        limite_izq = centro_imagen - (ANCHO_ZONA_MUERTA // 2)
        limite_der = centro_imagen + (ANCHO_ZONA_MUERTA // 2)

        cv2.line(frame, (limite_izq, 0), (limite_izq, alto), (0, 0, 255), 1)
        cv2.line(frame, (limite_der, 0), (limite_der, alto), (0, 0, 255), 1)

        # 1. Definimos qué queremos hacer
        comando_actual = ""
        if objetivo_x < limite_izq:
            accion = "<< MOVER IZQUIERDA"
            color_accion = (0, 0, 255)
            comando_actual = "I"
        elif objetivo_x > limite_der:
            accion = "MOVER DERECHA >>"
            color_accion = (0, 0, 255)
            comando_actual = "D"
        else:
            accion = "CENTRADO (QUIETO)"
            color_accion = (0, 255, 0)
            comando_actual = "C"

        # 2. SOLO enviamos por Wi-Fi si el comando es NUEVO
        if comando_actual != ultimo_comando_enviado:
            sock.sendto(comando_actual.encode(), (ESP_IP, PUERTO))
            ultimo_comando_enviado = comando_actual # Actualizamos el recuerdo

    # Opcional: Dibujar en GRIS al árbitro y a la gente del fondo para ver que los ignora
    for p in personas[2:]:
        x1, y1, x2, y2 = p["box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 100), 1)

    # Mostrar textos
    cv2.putText(frame, f"Estado: {accion}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color_accion, 2)
    cv2.imshow('VAR Esgrima IA', frame)

    if cv2.waitKey(1) == 27: # Presiona ESC para salir
        break

cap.release()
cv2.destroyAllWindows()
