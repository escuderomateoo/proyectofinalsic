import logging
import db

logger = logging.getLogger(__name__)


def guardar_comprobante_csv(comprobante_data: dict) -> None:
    try:
        db.guardar_comprobante(
            monto=str(comprobante_data.get("Monto", "")),
            fecha_hora=str(comprobante_data.get("Fecha y hora", "")),
            numero_operacion=str(comprobante_data.get("Número de operación", "")),
            remitente=str(comprobante_data.get("Nombre, CUIT/CUIL y CVU del remitente", "")),
            destinatario=str(comprobante_data.get("Nombre, CUIT/CUIL y CVU del destinatario", "")),
        )
        logger.info("Comprobante guardado en DB.")
    except Exception as e:
        logger.error("Error guardando comprobante: %s", e)
