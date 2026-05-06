import cv2
import numpy as np
import urllib.request
import io
from PIL import Image

class InpaintingService:
    def __init__(self):
        # Aquí irá tu configuración de Stability AI más adelante
        pass

    def apply_rough_wallpaper(self, original_img_cv, binary_mask, material_url, tile_size=300):
        """
        Toma cualquier imagen (aunque sea una laptop de Picsum) y la repite 
        como un mosaico sobre el área de la máscara.
        """
        try:
            # 1. Descargamos la "textura" (sea lo que sea que venga en el mock)
            req = urllib.request.urlopen(material_url)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            texture = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if texture is None:
                raise Exception("No se pudo decodificar la imagen del material")

            # Redimensionamos la textura al tamaño del azulejo para el mosaico
            texture = cv2.resize(texture, (tile_size, tile_size))

            # 2. Creamos el lienzo del tamaño de la foto original
            h_img, w_img, _ = original_img_cv.shape
            tiled_canvas = np.zeros((h_img, w_img, 3), dtype=np.uint8)

            # 3. Llenamos el lienzo repitiendo la textura (Tiling)
            for y in range(0, h_img, tile_size):
                for x in range(0, w_img, tile_size):
                    h_tile = min(tile_size, h_img - y)
                    w_tile = min(tile_size, w_img - x)
                    tiled_canvas[y:y+h_tile, x:x+w_tile] = texture[0:h_tile, 0:w_tile]

            # 4. Aplicamos la máscara para recortar
            # Convertimos la máscara de 1 canal a 3 canales para poder operar con la foto a color
            if len(binary_mask.shape) == 2:
                mask_3d = cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR)
            else:
                mask_3d = binary_mask

            # LA MEZCLA: Donde la máscara es blanca (255), ponemos el tapiz. 
            # Donde es negra (0), dejamos la foto original.
            rough_result = np.where(mask_3d == 255, tiled_canvas, original_img_cv)

            return rough_result

        except Exception as e:
            print(f"❌ Error aplicando papel tapiz: {e}")
            # Si falla la descarga, devolvemos la original para no romper el flujo
            return original_img_cv