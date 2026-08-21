import cv2
import re
from ultralytics import YOLO
from fast_alpr import ALPR
from collections import Counter
import requests
from datetime import datetime
import time
import sqlite3


device = "cpu"


model = YOLO("yolov8s.pt")


alpr = ALPR()


point1 = None
point2 = None



plate_results = {}


plate_history = {}


PLATE_CHECK_INTERVAL = 5


last_plate_check = {}


truck_times = {}
truck_history = []

WEB_UPDATE_INTERVAL = 1


last_web_update = 0


def is_valid_turkish_plate(plate):

    plate = (
        plate
        .replace(" ", "")
        .replace("-", "")
        .upper()
    )

    if len(plate) < 7 or not plate[:2].isdigit() or not 1 <= int(plate[:2]) <= 81:
      return False

    if not re.fullmatch(
        r"[0-9]{2}[A-Z0-9]+",
        plate
    ):
        return False

    return True

def send_data_to_web(
    truck_history,
    camera_connected,
    reset=False
):

    data = {
        "camera_connected": camera_connected,
        "truck_count": len(truck_history),
        "trucks": truck_history,
        "reset": reset
    }

    try:

        requests.post(
            "http://127.0.0.1:8000/update",
            json=data,
            timeout=5
        )

    except requests.RequestException as e:

        print(
            "WEB'E VERİ GÖNDERİLEMEDİ:",
            e
        )
def check_reset():

    try:

        response = requests.get(
            "http://127.0.0.1:8000/api/status"
        )

        data = response.json()

        return data.get("reset", False)

    except requests.RequestException:

        return False


def mouse(event, x, y, flags, param):

    global point1, point2

    if event == cv2.EVENT_LBUTTONDOWN:

        if point1 is None or point2 is not None:

            point1 = (x, y)

            point2 = None

            print("İlk nokta:", point1)

        else:

            point2 = (x, y)

            print("İkinci nokta:", point2)

def connect_camera():

#buraya ip atanıcak !!
cap = connect_camera()

if not cap.isOpened():
    print("Kamera bağlantısı kurulamadı.")

cv2.namedWindow("Video")


cv2.setMouseCallback("Video", mouse)


frame_number = 0


while True:

    if check_reset():

     truck_history.clear()

    print("Tır kayıtları sıfırlandı.")

    requests.post(
        "http://127.0.0.1:8000/reset-complete"
    )

    ret, frame = cap.read()

    if not ret:

     print("KAMERA BAĞLANTISI KESİLDİ.")


     send_data_to_web(
        truck_history,
        False
    )

     cap.release()

     time.sleep(2)

     cap = connect_camera()

     print("KAMERA YENİDEN BAĞLANDI.")

     continue


    frame_number += 1


    frame = cv2.resize(
        frame,
        (960, 540)
    )


    if point1 is not None and point2 is not None:

        x1 = min(
            point1[0],
            point2[0]
        )

        y1 = min(
            point1[1],
            point2[1]
        )

        x2 = max(
            point1[0],
            point2[0]
        )

        y2 = max(
            point1[1],
            point2[1]
        )



        roi_frame = frame[
            y1:y2,
            x1:x2
        ]


        results = model.track(
            roi_frame,
            persist=True,
            tracker="bytetrack.yaml",
            imgsz=640,
            device=device,
            verbose=False
        )


        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )


        cv2.putText(
            frame,
            "ROI",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )


        for box in results[0].boxes:


            x_min, y_min, x_max, y_max = map(
                int,
                box.xyxy[0]
            )


            x_min += x1
            x_max += x1
            y_min += y1
            y_max += y1


            confidence = float(
                box.conf[0]
            )


            class_id = int(
                box.cls[0]
            )


            class_name = model.names[class_id]


            if box.id is None:

                continue


            track_id = int(
                box.id.item()
            )


            if class_name != "truck":

                continue


            if confidence < 0.75:

                continue


            truck_width = x_max - x_min
            truck_height = y_max - y_min

            truck_area = truck_width * truck_height


            is_close_enough = truck_area > 10200

            crop_x1 = max(
                0,
                x_min
            )

            crop_y1 = max(
                0,
                y_min
            )

            crop_x2 = min(
                frame.shape[1],
                x_max
            )

            crop_y2 = min(
                frame.shape[0],
                y_max
            )


            truck_crop = frame[
                crop_y1:crop_y2,
                crop_x1:crop_x2
            ]



            should_check_plate = (

                track_id not in last_plate_check

                or

                frame_number
                - last_plate_check[track_id]
                >= PLATE_CHECK_INTERVAL

            )


            if (
                should_check_plate
                and
                is_close_enough
                and
                truck_crop.size != 0
            ):

                last_plate_check[track_id] = frame_number




                enlarged_truck = cv2.resize(

                    truck_crop,

                    None,

                    fx=2.0,
                    fy=2.0,

                    interpolation=cv2.INTER_CUBIC

                )




                alpr_results = alpr.predict(
                    enlarged_truck
                )




                for alpr_result in alpr_results:

                    if alpr_result.ocr is None:

                        continue


                    plate = alpr_result.ocr.text


                    if not plate:

                        continue




                    plate = (
                        plate
                        .replace(" ", "")
                        .replace("-", "")
                        .upper()
                    )


                    if not is_valid_turkish_plate(plate):

                        continue

                    if track_id not in plate_history:

                        plate_history[track_id] = []


                    plate_history[track_id].append(
                        plate
                    )




                    counts = Counter(
                        plate_history[track_id]
                    )


                    best_plate, best_count = (
                        counts.most_common(1)[0]
                    )



                    previous_plate = plate_results.get(
                        track_id
                    )



                    if previous_plate != best_plate:

                        print(
                            f"ID {track_id} "
                            f"-> Plaka: {plate} "
                            f"-> En güçlü aday: {best_plate}"
                        )

                    if not any(
                    truck["id"] == track_id
                    for truck in truck_history
):
                     truck_times[track_id] = datetime.now().strftime("%H:%M:%S")

                     truck_history.append({
                     "id": track_id,
                     "plate": best_plate,
                      "time": truck_times.get(track_id)
    })
                    plate_results[track_id] = best_plate



            cv2.rectangle(
                frame,
                (x_min, y_min),
                (x_max, y_max),
                (0, 255, 0),
                2
            )


            text = (
                f"ID:{track_id} "
                f"Truck "
                f"{confidence:.2f}"
            )



            if track_id in plate_results:

                text += (
                    f" "
                    f"PLAKA:"
                    f"{plate_results[track_id]}"
                )


            cv2.putText(
                frame,
                text,
                (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 0, 0),
                2
            )

    current_time = time.time()

    if (
        current_time - last_web_update
        >= WEB_UPDATE_INTERVAL
    ):

        send_data_to_web(
            truck_history,
            True
        )

        last_web_update = current_time


    cv2.putText(
        frame,
        f"Total Trucks: {len(truck_history)}",
        (30, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2
    )


    cv2.imshow(
        "Video",
        frame
    )


    key = cv2.waitKey(1) & 0xFF


    if key == ord("q"):
     send_data_to_web(truck_history,False)
     truck_history.clear()
     break

    elif key == ord("r"):

        point1 = None
        point2 = None

        print("Roı bölgesi sıfırlandı, tekrar oluşturabilirsiniz.")



cap.release()

cv2.destroyAllWindows()