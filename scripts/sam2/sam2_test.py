video_path = "/opt/sam2/demo/data/gallery/01_dog.mp4" 

# file: demo_video_sam2_streaming_multi_preview.py
import os, cv2, torch
import numpy as np
from transformers import Sam2VideoModel, Sam2VideoProcessor, infer_device

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True,max_split_size_mb:128"

def downscale(img, max_side=640):
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    return cv2.resize(img, (int(w*s), int(h*s)), interpolation=cv2.INTER_AREA) if s < 1.0 else img

cap = cv2.VideoCapture(video_path)
# cap = cv2.VideoCapture(0)
ok, f0 = cap.read()
if not ok: raise RuntimeError("cannot read video")
f0 = cv2.cvtColor(f0, cv2.COLOR_BGR2RGB)
f0 = downscale(f0, 640)

device = infer_device()
dtype  = torch.bfloat16 if torch.cuda.is_available() else torch.float32
model = Sam2VideoModel.from_pretrained("facebook/sam2.1-hiera-tiny").to(device, dtype=dtype).eval()
proc  = Sam2VideoProcessor.from_pretrained("facebook/sam2.1-hiera-tiny")

# 複数領域のクリック位置とマスクを保持
clicked_points = []
object_masks = []
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), 
          (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 128, 0)]

# 最初のフレームの入力を準備（推論に使用）
inputs0 = proc(images=f0, device=device, return_tensors="pt")

def run_inference_for_point(point_x, point_y):
    """指定した点に対してSAM2推論を実行してマスクを取得"""
    print(f"  推論実行中... 点: ({point_x}, {point_y})")
    
    # 一時セッションを作成
    temp_session = proc.init_video_session(inference_device=device, dtype=dtype)
    
    with torch.inference_mode():
        proc.add_inputs_to_inference_session(
            inference_session=temp_session, 
            frame_idx=0, 
            obj_ids=1,
            input_points=[[[[point_x, point_y]]]],
            input_labels=[[[1]]],
            original_size=inputs0.original_sizes[0],
        )
        out = model(inference_session=temp_session, frame=inputs0.pixel_values[0])
        masks = proc.post_process_masks([out.pred_masks], 
                                       original_sizes=inputs0.original_sizes, 
                                       binarize=True)[0]
    
    # マスクを取得（最初のオブジェクト）
    mask = masks[0, 0].cpu().numpy()
    print(f"  マスク取得完了")
    return mask

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:  # 左クリック: 領域追加
        print(f"\n領域 {len(clicked_points) + 1} を追加:")
        clicked_points.append((x, y))
        
        # その場で推論を実行してマスクを取得
        mask = run_inference_for_point(x, y)
        object_masks.append(mask)
        
        print(f"  領域 {len(clicked_points)} の追跡準備完了")

cv2.namedWindow("click points (left: add, ESC: done)")
cv2.setMouseCallback("click points (left: add, ESC: done)", on_mouse)

print("領域を指定してください...")
print("- 左クリック: 追跡する領域をクリック（推論が自動実行されます）")
print("- ESC: 領域確定してトラッキング開始")
print("- R: リセット\n")

# クリック入力ループ
while True:
    # 表示用フレームを準備
    display_img = cv2.cvtColor(f0, cv2.COLOR_RGB2BGR).copy()
    
    # 各オブジェクトのマスクを半透明で重ね合わせ
    for i, mask in enumerate(object_masks):
        color = colors[i % len(colors)]
        overlay = display_img.copy()
        overlay[mask > 0] = color
        cv2.addWeighted(overlay, 0.4, display_img, 0.6, 0, display_img)
    
    # クリックした点を表示
    for i, (px, py) in enumerate(clicked_points):
        color = colors[i % len(colors)]
        cv2.circle(display_img, (px, py), 8, color, -1)
        cv2.circle(display_img, (px, py), 10, (255, 255, 255), 2)
        cv2.putText(display_img, str(i+1), (px+15, py), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 説明テキストを表示
    cv2.putText(display_img, f"Objects: {len(clicked_points)} (Click to add)", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(display_img, "Left Click: Add | R: Reset | ESC: Start tracking", 
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    cv2.imshow("click points (left: add, ESC: done)", display_img)
    
    key = cv2.waitKey(10)
    if key == 27:  # ESC: 完了
        if len(clicked_points) > 0:
            break
        else:
            print("最低1つの領域を指定してください")
    elif key == ord('r') or key == ord('R'):  # R: リセット
        clicked_points = []
        object_masks = []
        print("\nリセットしました\n")

cv2.destroyWindow("click points (left: add, ESC: done)")

if len(clicked_points) == 0:
    print("領域が指定されていません。終了します。")
    exit()

print(f"\n━━━━━━━━━━━━━━━━━━━━━━")
print(f"合計 {len(clicked_points)} 個の領域でトラッキング開始")
print(f"━━━━━━━━━━━━━━━━━━━━━━\n")

# トラッキング用セッションを新規作成
session = proc.init_video_session(inference_device=device, dtype=dtype)

# 1枚目を処理（全オブジェクトを登録）
with torch.inference_mode():
    # 各クリックポイントをオブジェクトとして追加し、その都度推論を実行
    for obj_id, (px, py) in enumerate(clicked_points, start=1):
        proc.add_inputs_to_inference_session(
            inference_session=session, 
            frame_idx=0, 
            obj_ids=obj_id,
            input_points=[[[[px, py]]]],
            input_labels=[[[1]]],
            original_size=inputs0.original_sizes[0],
        )
        # 各オブジェクト追加後に推論を実行
        out = model(inference_session=session, frame=inputs0.pixel_values[0])

# 以降は1フレームずつトラッキング
print("トラッキング中... (ESCで終了)\n")
frame_count = 0
while True:
    ok, f = cap.read()
    if not ok: 
        break
    f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
    f = downscale(f, 640)
    
    with torch.inference_mode():
        inputs = proc(images=f, device=device, return_tensors="pt")
        out = model(inference_session=session, frame=inputs.pixel_values[0])
        
        # デバッグ: pred_masksの形状を確認（最初のフレームのみ）
        if frame_count == 0:
            print(f"pred_masks shape: {out.pred_masks.shape}")
            print(f"期待されるオブジェクト数: {len(clicked_points)}")
        
        # マスクの後処理（binarize=Falseで取得してから手動で二値化）
        masks_raw = proc.post_process_masks([out.pred_masks], 
                                            original_sizes=inputs.original_sizes, 
                                            binarize=False)[0]
    
    # 表示用画像を準備
    vis = cv2.cvtColor(f, cv2.COLOR_RGB2BGR)
    
    # 各オブジェクトのマスクを異なる色で重ね合わせ
    tracked_count = 0
    for obj_id in range(len(clicked_points)):
        if obj_id < masks_raw.shape[0]:
            # マスクを二値化
            m = (masks_raw[obj_id, 0] > 0.0).cpu().numpy()
            
            if m.any():  # マスクが存在する場合のみ表示
                tracked_count += 1
                color = colors[obj_id % len(colors)]
                # 半透明で色を重ねる
                overlay = vis.copy()
                overlay[m] = color
                cv2.addWeighted(overlay, 0.5, vis, 0.5, 0, vis)
                
                # オブジェクト番号をマスクの中心に表示
                moments = cv2.moments(m.astype(np.uint8))
                if moments["m00"] != 0:
                    cx = int(moments["m10"] / moments["m00"])
                    cy = int(moments["m01"] / moments["m00"])
                    cv2.putText(vis, str(obj_id + 1), (cx, cy), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
    
    # フレーム数とトラッキング情報を表示
    cv2.putText(vis, f"Frame: {frame_count} | Tracking: {tracked_count}/{len(clicked_points)}", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow("SAM2 streaming (multi-object)", vis)
    frame_count += 1
    
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("\n終了しました")