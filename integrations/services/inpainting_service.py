import cv2
import numpy as np
import urllib.request

class InpaintingService:
    def __init__(self):
        # 💡 Nos libramos de las APIs por ahora. Motor 100% local y matemático.
        pass

    def _recortar_bordes_blancos(self, texture_cv):
        """
        ✂️ EL BISTURÍ: Quita el borde blanco del producto de WooCommerce.
        """
        gray = cv2.cvtColor(texture_cv, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        coords = cv2.findNonZero(thresh)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            recorte = texture_cv[y:y+h, x:x+w]
            print(f"✂️ [OpenCV] Fondo blanco eliminado. Nuevo tamaño: {recorte.shape[:2]}")
            return recorte
            
        return texture_cv

    def _limpiar_mascara(self, binary_mask):
        """
        🧼 LA ASPIRADORA: Elimina el ruido de la segmentación.
        Si Segformer detecta 16 paredes de cristal, esto las une o borra la basura
        y se queda solo con las estructuras masivas.
        """
        # 1. Suavizamos y conectamos pedazos rotos (Morphological Close)
        kernel = np.ones((15, 15), np.uint8)
        closed_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
        
        # 2. Borramos manchitas aisladas (Morphological Open)
        opened_mask = cv2.morphologyEx(closed_mask, cv2.MORPH_OPEN, kernel)

        # 3. FILTRO DE ÁREA: Buscamos los bloques y medimos su tamaño
        contours, _ = cv2.findContours(opened_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        clean_mask = np.zeros_like(opened_mask)
        
        if not contours:
            return opened_mask

        # Ordenamos los pedazos de mayor a menor tamaño
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Definimos el umbral: Todo pedazo que sea menor al 3% del tamaño de la foto, se borra.
        total_area = opened_mask.shape[0] * opened_mask.shape[1]
        min_area_threshold = total_area * 0.03 

        bloques_guardados = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area_threshold:
                # Si es un bloque grande (pared principal o piso), lo dibujamos
                cv2.drawContours(clean_mask, [cnt], -1, 255, thickness=cv2.FILLED)
                bloques_guardados += 1
            else:
                # Como están ordenados de mayor a menor, si este no pasó, los demás tampoco
                break 

        print(f"🧼 [OpenCV] Máscara purificada. De {len(contours)} fragmentos, nos quedamos con los {bloques_guardados} más grandes.")
        return clean_mask

    def apply_rough_wallpaper(self, original_img_cv, binary_mask, material_url, tile_size=300):
        """
        🚀 EL MOTOR DE RENDER: Tiling matemático, seguro y ultra rápido.
        """
        try:
            print(f"📥 Descargando textura real del catálogo: {material_url}")
            req = urllib.request.urlopen(material_url)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            texture = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if texture is None:
                raise Exception("No se pudo decodificar la imagen del material real")

            # 1. Quitamos los marcos blancos del producto
            texture = self._recortar_bordes_blancos(texture)

            # 2. Redimensionamos al tamaño del azulejo/cerámica
            texture = cv2.resize(texture, (tile_size, tile_size))
            h_img, w_img, _ = original_img_cv.shape

            # 3. Creamos el tapiz repitiendo la textura rapidísimo con Numpy
            reps_y = int(np.ceil(h_img / tile_size))
            reps_x = int(np.ceil(w_img / tile_size))
            tiled_canvas = np.tile(texture, (reps_y, reps_x, 1))
            tiled_canvas = tiled_canvas[:h_img, :w_img]

            # 4. Ajustamos la máscara original al tamaño exacto de la foto
            if len(binary_mask.shape) == 2:
                mask_3d = cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR)
            else:
                mask_3d = binary_mask

            if mask_3d.shape != original_img_cv.shape:
                mask_3d = cv2.resize(mask_3d, (w_img, h_img), interpolation=cv2.INTER_NEAREST)

            # 5. 💡 PURIFICAMOS LA MÁSCARA PARA QUITAR LAS 16 PAREDES FANTASMAS
            mask_limpia = self._limpiar_mascara(mask_3d[:, :, 0]) # Le pasamos 1 solo canal al purificador
            mask_limpia_3d = cv2.cvtColor(mask_limpia, cv2.COLOR_GRAY2BGR)

            # 6. LA MEZCLA FINAL CON LA MÁSCARA LIMPIA
            rough_result = np.where(mask_limpia_3d == 255, tiled_canvas, original_img_cv)
            return rough_result

        except Exception as e:
            print(f"❌ Error en mosaico matemático crudo: {e}")
            return original_img_cv