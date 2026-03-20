import cv2
import numpy as np
import mediapipe as mp
from rknn_emotion import RKNNEmotionDetector

# ========= 初始化 RKNN =========
emotion_detector = RKNNEmotionDetector("best_emotion_model.rknn")

# ========= 类别（必须与训练一致） =========
emotion_labels = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise"
]

# ========= 二维情绪映射 =========
valence_map = np.array([-0.7, -0.6, -0.7, 0.9, 0.0, -0.8, 0.4])
arousal_map = np.array([0.8, 0.6, 0.9, 0.6, 0.2, 0.2, 0.8])

def emotion_to_va(probs):
    valence = np.sum(probs * valence_map)
    arousal = np.sum(probs * arousal_map)
    return valence, arousal

def interpret_emotion(valence, arousal):
    if valence > 0.4 and arousal > 0.6:
        return "Excited"
    if valence > 0.5 and arousal < 0.4:
        return "Relaxed"
    if valence > 0.2:
        return "Positive"
    if valence < -0.5 and arousal > 0.6:
        return "Angry / Stressed"
    if valence < -0.5 and arousal < 0.4:
        return "Depressed"
    if valence < -0.2:
        return "Negative"
    if arousal > 0.7:
        return "Nervous"
    return "Calm"

def draw_emotion_disk(valence, arousal):
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    center = (150, 150)
    radius = 120

    cv2.circle(img, center, radius, (200,200,200), 2)

    cv2.line(img, (30,150), (270,150), (150,150,150), 1)
    cv2.line(img, (150,30), (150,270), (150,150,150), 1)

    cv2.putText(img, "Positive", (185,145),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    cv2.putText(img, "Negative", (50,145),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    cv2.putText(img, "Excited", (120,60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    cv2.putText(img, "Calm", (130,250),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    x = int(center[0] + valence * radius)
    y = int(center[1] - arousal * radius)

    cv2.circle(img, (x,y), 6, (0,255,255), -1)

    cv2.imshow("Emotion Disk", img)

# ========= Mediapipe 人脸检测 =========
mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# ========= 摄像头 =========
cap = cv2.VideoCapture(0)

# ========= 时间平滑 =========
last_probs = np.zeros(7)
alpha = 0.4

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    faces = face_detector.process(rgb)

    probs = None
    valence, arousal = 0, 0
    state = ""

    if faces.detections:
        boxes = []
        for det in faces.detections:
            bbox = det.location_data.relative_bounding_box
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            ww = int(bbox.width * w)
            hh = int(bbox.height * h)
            boxes.append((x,y,ww,hh))

        x,y,ww,hh = sorted(boxes, key=lambda b: b[2]*b[3], reverse=True)[0]

        x = max(0,x)
        y = max(0,y)
        ww = min(ww, w-x)
        hh = min(hh, h-y)

        face = frame[y:y+hh, x:x+ww]

        probs, label, conf = emotion_detector.infer(face)

        # 时间平滑
        probs = alpha * probs + (1 - alpha) * last_probs
        last_probs = probs

        valence, arousal = emotion_to_va(probs)
        state = interpret_emotion(valence, arousal)

        cv2.rectangle(frame, (x,y), (x+ww,y+hh), (0,255,0), 2)

    # ===== 左上角显示 =====
    start_y = 25

    if probs is not None:
        cv2.putText(frame, "Emotion Probabilities",
                    (10, start_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

        for i, p in enumerate(probs):
            text = f"{emotion_labels[i]}: {p:.2f}"
            cv2.putText(frame, text,
                        (10, start_y + 25 + i*20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (0,255,0), 1)

        cv2.putText(frame, f"Valence: {valence:.2f}",
                    (10, start_y + 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)

        cv2.putText(frame, f"Arousal: {arousal:.2f}",
                    (10, start_y + 230),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)

        cv2.putText(frame, state,
                    (10, start_y + 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

    cv2.imshow("Emotion VA System", frame)
    draw_emotion_disk(valence, arousal)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
emotion_detector.release()