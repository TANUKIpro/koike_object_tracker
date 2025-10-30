import cv2
import numpy as np

def draw_overlay(image_bgr, dets):
    img = image_bgr.copy()
    for d in dets:
        x1,y1,x2,y2 = [int(v) for v in d['bbox']]
        conf = d.get('conf', 0.0)
        name = d.get('cls_name', '?')
        cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(img, f"{name} {conf:.2f}", (x1, max(0, y1-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        if 'mask' in d and d['mask'] is not None:
            mask = d['mask'].astype(np.uint8) * 255
            color = np.zeros_like(img)
            color[:,:,2] = mask
            img = cv2.addWeighted(img, 1.0, color, 0.4, 0)
    return img
