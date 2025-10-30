import numpy as np

class YOLOv11Detector:
    def __init__(self, weights='yolo11s.pt', conf=0.4, iou=0.5, device='cuda:0', max_dets=10):
        try:
            from ultralytics import YOLO
        except Exception as e:
            raise RuntimeError(f'Ultralytics not available: {e}')
        self.model = YOLO(weights)
        try:
            self.model.fuse()
        except Exception:
            pass
        self.conf = conf
        self.iou = iou
        self.device = device
        self.max_dets = max_dets

    def infer(self, img_bgr):
        rgb = img_bgr[..., ::-1]
        results = self.model.predict(
            source=rgb,
            conf=self.conf,
            iou=self.iou,
            device=self.device,
            max_det=self.max_dets,
            verbose=False
        )
        dets = []
        if not results:
            return dets
        r = results[0]
        names = r.names
        if r.boxes is None:
            return dets
        for b in r.boxes:
            xyxy = b.xyxy[0].tolist()
            conf = float(b.conf[0].item()) if hasattr(b, 'conf') else 0.0
            cls_id = int(b.cls[0].item()) if hasattr(b, 'cls') else -1
            cls_name = names.get(cls_id, str(cls_id))
            dets.append({
                "bbox": [float(x) for x in xyxy],
                "conf": conf,
                "cls_id": cls_id,
                "cls_name": cls_name
            })
        return dets
