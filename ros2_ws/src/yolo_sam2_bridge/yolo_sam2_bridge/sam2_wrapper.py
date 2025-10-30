import numpy as np

class SAM2BoxSegmentor:
    """
    Minimal SAM2 wrapper that takes an image (BGR) and a box [x1,y1,x2,y2],
    and returns a binary mask (H,W) where True=object.
    Adjust import paths if your SAM2 install differs.
    """
    def __init__(self, model_cfg, checkpoint, device='cuda'):
        try:
            from sam2.build_sam import build_sam2, SAM2ImagePredictor
        except Exception as e:
            raise RuntimeError(f"SAM2 import failed: {e}")
        self.SAM2ImagePredictor = SAM2ImagePredictor
        self.model = build_sam2(model_cfg, checkpoint, device=device)
        self.predictor = SAM2ImagePredictor(self.model)

    def segment_with_box(self, img_bgr, box_xyxy):
        img_rgb = img_bgr[..., ::-1].copy()
        self.predictor.set_image(img_rgb)
        box = np.array(box_xyxy, dtype=np.float32)
        masks, scores, logits = self.predictor.predict(
            box=box[None, :],
            multimask_output=False
        )
        if masks is None or len(masks) == 0:
            return None, 0.0
        m = masks[0].astype(bool)
        s = float(scores[0]) if scores is not None else 1.0
        return m, s
