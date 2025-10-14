import csv
import os

def guardar_comprobante_csv(data):
    archivo = "comprobantes.csv"
    existe = os.path.exists(archivo)

    with open(archivo, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow([
                "Monto", "Fecha y hora", "Número de operación",
                "Remitente nombre", "Remitente CUIT/CUIL", "Remitente CVU",
                "Destinatario nombre", "Destinatario CUIT/CUIL", "Destinatario CVU"
            ])

        writer.writerow([
            data.get("monto", ""),
            data.get("fecha_hora", ""),
            data.get("nro_operacion", ""),
            data.get("remitente", {}).get("nombre", ""),
            data.get("remitente", {}).get("cuit_cuil", ""),
            data.get("remitente", {}).get("cvu", ""),
            data.get("destinatario", {}).get("nombre", ""),
            data.get("destinatario", {}).get("cuit_cuil", ""),
            data.get("destinatario", {}).get("cvu", "")
        ])
