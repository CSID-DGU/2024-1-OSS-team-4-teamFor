
from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
from django.views.decorators.csrf import csrf_exempt
import os
import json
from function.server_use import scoring_points, make_picture

# API 키 작성된 메모장 주소
keys_file_path = os.path.join('../API', 'api_keys.txt')

# 파일에서 API 키를 로드하는 함수
with open(keys_file_path, 'r', encoding='utf-8') as file:
    keys = json.load(file)

# API 키 사용
NAVER_API_KEY_ID = f"{keys['naver_api_keys_id']}"
NAVER_API_KEY = f"{keys['naver_api_keys']}"

@csrf_exempt
def proxy_to_naver_stt(request):
    if request.method == 'POST' and request.FILES.get('audioFile'):
        print('잘 들어옴')
        naver_api_url = 'https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor'
        headers = {
            "Content-Type": "application/octet-stream",  # 오디오 파일의 유형에 따라 수정할 수 있습니다.
            "X-NCP-APIGW-API-KEY-ID": NAVER_API_KEY_ID,
            "X-NCP-APIGW-API-KEY": NAVER_API_KEY,
        }
        
        audio_file = request.FILES['audioFile'].read()
        response = requests.post(naver_api_url, headers=headers, data=audio_file)
        data = response.json()
        print('초기 데이터:',data)

        if "text" in data:            
            accuracy, true_word, whole_prompt = scoring_points(data['text']) 
            data['accuracy'] = accuracy
            data['len_true_word'] = len(true_word)
            data['p'] = list(whole_prompt)

        response_to_client = JsonResponse(data, safe=False)
        response_to_client["Access-Control-Allow-Origin"] = "*"
        response_to_client["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response_to_client["Access-Control-Allow-Headers"] = "Content-Type"
        print('최종 반환:', response_to_client)
        return response_to_client
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def make_pic_karlo(request):
    if request.method == 'POST':
        print('함수 호출 완료')
        body_unicode = request.body.decode('utf-8')
        body_data = json.loads(body_unicode)

        whole_prompt = body_data.get('text', '')
        image_response = make_picture(whole_prompt)
        data = {'image_url': image_response['images'][0]['image']}
        
        print(data)

        response_to_client = JsonResponse(data, safe=False)
        response_to_client["Access-Control-Allow-Origin"] = "*"
        response_to_client["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response_to_client["Access-Control-Allow-Headers"] = "Content-Type"

        return response_to_client


# urls.py
from django.urls import path
from .views import proxy_to_naver_stt

urlpatterns = [
    path('api/naver-stt/', proxy_to_naver_stt, name='naver_stt_proxy'),
]

#시작 html 결정
@csrf_exempt
def index(request):
    return render(request, '../Frontend_UI/Camera.html')

@csrf_exempt
def second_page(request):
    return render(request, '../Frontend_UI/index.html')



def send_audio_to_naver_stt(request):
    if request.method == 'POST' and request.FILES.get('audioFile'):
        audio_file = request.FILES['audioFile'].read()  # 파일을 메모리에 로드합니다.
        url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor"

        headers = {
            "Content-Type": "application/octet-stream",  # 오디오 파일의 유형에 따라 수정할 수 있습니다.
            "X-NCP-APIGW-API-KEY-ID": NAVER_API_KEY_ID,
            "X-NCP-APIGW-API-KEY": NAVER_API_KEY,
        }

        response = requests.post(url, data=audio_file, headers=headers)
        rescode = response.status_code
        if rescode == 200:
            response_data = response.json()
            # 응답 본문 내용을 콘솔에 출력합니다.
            print("네이버 음성 인식 API 응답:")
            print(response_data)
            return JsonResponse(response_data, safe=False)
        else:
            # 네이버 API 응답 본문을 포함하여 오류 메시지를 개선합니다.
            return JsonResponse({'error': 'Failed to process audio file', 'message': response.text}, status=rescode)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


#웹 캠 이용해서 사진 저장 
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
@csrf_exempt
def upload_image(request):
    path = None
    full_path = None

    if request.method == 'POST':
        image = request.FILES.get('photo')
        if image:
            # 세션에서 이미지 카운터를 가져옵니다.
            image_counter = request.session.get('image_counter', 0)
            folder_counter = request.session.get('folder_counter', 1)
            image_counter += 1
            
            # 기본 폴더 이름 설정
            base_folder_name = 'User_images'
            
            # 실제 저장될 폴더 이름 설정
            folder_name = f"{base_folder_name}_{folder_counter}"
            
            # 파일 이름 설정
            file_name = os.path.join(folder_name, f"image_{image_counter}.jpg")
            
            # 이미지 저장
            path = default_storage.save(file_name, ContentFile(image.read()))
            full_path = os.path.join(settings.MEDIA_ROOT, path)
            
            # 세션에 이미지 카운터와 폴더 카운터 업데이트
            request.session['image_counter'] = image_counter
            request.session['folder_counter'] = folder_counter
            
            print(f"Image {image_counter} uploaded successfully to {full_path}")
            
            # 10번째 이미지 후 세션 리셋 및 폴더 카운터 증가
            if image_counter >= 10:
                request.session['image_counter'] = 0  # 이미지 카운터 리셋
                request.session['folder_counter'] = folder_counter + 1  # 폴더 카운터 증가
                
                train_model_again(os.path.join(settings.MEDIA_ROOT, folder_name))

            return JsonResponse({'message': 'Image uploaded successfully!', 'path': full_path})
        else:
            print("No image provided")
            return JsonResponse({'error': 'No image provided'}, status=400)
    else:
        print("Invalid request")
        return JsonResponse({'error': 'Invalid request'}, status=400)

#모델 추가 학습
from imutils import paths
import face_recognition
#import argparse
import pickle
import cv2
import os

def train_model_again(request):
    # 기존에 저장된 얼굴 인코딩과 이름을 불러옵니다.
    with open("../SilverTech/function/encodings.pickle", "rb") as f:
        data = pickle.load(f)
    knownEncodings = data["encodings"]
    knownNames = data["names"]

    # 새로운 이미지 경로 설정 (새로운 학습 데이터 경로)
    newImagePaths = list(paths.list_images(request))

    # 새로운 이미지 데이터에 대해 루프를 돌면서 처리
    for (i, imagePath) in enumerate(newImagePaths):
        print("[INFO] processing image {}/{}".format(i + 1, len(newImagePaths)))
        name = imagePath.split(os.path.sep)[-2]

        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            knownEncodings.append(encoding)
            knownNames.append(name)

    # 수정된 인코딩과 이름 데이터를 다시 pickle 파일로 저장합니다.
    print("[INFO] serializing encodings...")
    data = {"encodings": knownEncodings, "names": knownNames}
    with open("encodings.pickle", "wb") as f:
        f.write(pickle.dumps(data))
    f.close()




def train_model_again1(image_folder_path):
    # 기존에 저장된 얼굴 인코딩과 이름을 불러옵니다.
    with open("../SilverTech/function/encodings.pickle", "rb") as f:
        data = pickle.load(f)
    knownEncodings = data["encodings"]
    knownNames = data["names"]

    # 새로운 이미지 경로 설정 (새로운 학습 데이터 경로)
    newImagePaths = list(paths.list_images(image_folder_path))

    # 새로운 이미지 데이터에 대해 루프를 돌면서 처리
    for (i, imagePath) in enumerate(newImagePaths):
        print("[INFO] processing image {}/{}".format(i + 1, len(newImagePaths)))
        name = imagePath.split(os.path.sep)[-2]

        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            knownEncodings.append(encoding)
            knownNames.append(name)

    # 수정된 인코딩과 이름 데이터를 다시 pickle 파일로 저장합니다.
    print("[INFO] serializing encodings...")
    data = {"encodings": knownEncodings, "names": knownNames}
    with open("../SilverTech/function/encodings.pickle", "wb") as f:
        f.write(pickle.dumps(data))




