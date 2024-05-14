import json
import random
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse
from .models import BasePictures, User, UserAccuracy, UserProceeding
from function.server_use import scoring_points

picture_number_by_level = [2, 5, 3, 5, 3] #[2,5,3]만 해두니 level 3과 4에서 list over되어 5, 3 추가함

# http://127.0.0.1:8000/picture-load/

# Create your views here.
def test_picture_load(request):
    return render(request, "test-image-load.html") # templates 폴더 안에 test-image-load.html가 존재함

#회원정보 확인
def fetch_user_info(request):
    #request에서 로그인 정보를 추출하는 코드 추후 추가
    #사용자 정보 임의 설정
    user_name = 'test1'
    if user_name:
        try:
            # DB에서 해당 사용자의 난이도 정보를 가져옴
            user = User.objects.get(name=user_name)
        except User.DoesNotExist:
            # 사용자가 존재하지 않는 경우 새로운 사용자를 생성하고 저장
            user = User(name=user_name)
            user.save()
            # 새로운 사용자에 대해 UserProceeding을 초기화
            user_proceeding = UserProceeding(user=user, level=1, last_order=0, is_order=0)
            user_proceeding.save()
            # UserAccuracy도 초기화
            user_accuracy = UserAccuracy(user=user, successive_correct=0, successive_wrong=0)
            user_accuracy.save()
        else:
            # 사용자가 존재하는 경우 UserProceeding 가져오기
            try:
                user_proceeding = UserProceeding.objects.get(user=user)
            except UserProceeding.DoesNotExist:
                # UserProceeding이 존재하지 않을 경우 error
                return None, JsonResponse({'error': 'User proceeding not found'}, status=404)
        
        # 세션에 사용자 정보 저장
        request.session['user_name'] = user_name
        request.session['user_id'] = user.user_id
        request.session['level'] = user_proceeding.level

        return user_proceeding, None  # UserProceeding 객체와 None 반환
    else:
        return None, JsonResponse({'error': 'No name provided'}, status=400)

#base그림 출력
def load_base_picture(request):
    # fetch_user_info 함수를 호출하여 사용자 진행 정보를 가져옴
    # 오류가 발생하면 error_response를 반환
    user_proceeding, error_response = fetch_user_info(request)
    if error_response:
        return error_response  # 오류 응답 반환

    try:
        # 사용자 진행 정보에서 현재 레벨을 가져옴
        level = user_proceeding.level
        # 레벨 조정 로직: 레벨이 2 이하이면 그대로 사용하고, 3 이상이면 2를 뺌
        picture_level = level if level <= 2 else level - 2  
        request.session['picture_level'] = picture_level  # 세션에 조정된 레벨을 저장

        # 현재 진행 상태의 last_order에 해당하는 그림을 가져옴
        base_picture = BasePictures.objects.get(level=picture_level, order=user_proceeding.last_order)
        
        # 가져온 그림의 URL, 레벨, 순서를 템플릿에 전달하여 렌더링
        return render(request, 'level-image.html', {
            'level': level,
            'url': base_picture.url,
            'order': base_picture.order
        })
    except BasePictures.DoesNotExist:
        # 그림이 존재하지 않는 경우 오류 응답 반환
        return JsonResponse({'error': 'Base picture not found'}, status=404)


# 다음 order의 그림을 가져오는 함수
@csrf_exempt
def change_base_picture(request):
    # 요청의 body에서 JSON 데이터를 파싱하여 'is_order' 값을 가져옴
    data = json.loads(request.body.decode('utf-8'))
    is_order = data.get('is_order', False)

    try:
        # 세션에서 사용자 ID, 레벨, 그림 레벨을 가져옴
        user_id = request.session.get('user_id')
        level = request.session.get('level')  # 현재 레벨을 세션에서 가져옴
        picture_level = level if level <= 2 else level - 2  # 조정된 레벨 계산
        
        # 사용자 진행 정보를 데이터베이스에서 가져옴
        user_proceeding = UserProceeding.objects.get(user_id=user_id)

        # 레벨이 설정된 범위를 벗어나면 오류 반환
        if level >= len(picture_number_by_level):
            return JsonResponse({'error': 'Level out of range'}, status=400)

        if is_order:
            # is_order가 참일 때: 다음 순서의 그림을 역순으로 가져오는 로직
            if level == 3 or level == 4:
                # 레벨 3, 4일 때 역순으로 그림을 가져옴
                new_order = (user_proceeding.last_order - 1 + picture_number_by_level[level]) % picture_number_by_level[level]
                user_proceeding.last_order = new_order
            else:
                # 기타 레벨에서는 정순으로 다음 순서의 그림을 가져옴
                new_order = (user_proceeding.last_order + 1) % picture_number_by_level[level]
                user_proceeding.last_order = new_order
        else:
            # is_order가 거짓일 때: 랜덤으로 그림을 선택하는 로직
            all_pictures = list(BasePictures.objects.filter(level=picture_level).values_list('order', flat=True))
            seen_pictures = user_proceeding.seen_pictures or []
            available_pictures = [order for order in all_pictures if order not in seen_pictures]
            
            # 모든 그림을 본 경우, 본 그림 목록을 리셋하여 다시 선택할 수 있게 함
            if not available_pictures:
                seen_pictures = []  # 이미 본 그림 목록 리셋
                available_pictures = all_pictures

            # 랜덤으로 그림을 선택
            chosen_order = random.choice(available_pictures)
            user_proceeding.last_order = chosen_order
            seen_pictures.append(chosen_order)
            user_proceeding.seen_pictures = seen_pictures

        # 변경된 진행 정보를 저장
        user_proceeding.save()

        # 선택된 그림을 데이터베이스에서 가져옴
        base_picture = BasePictures.objects.get(level=picture_level, order=user_proceeding.last_order)
        # 그림의 URL과 순서를 JSON 형태로 반환
        return JsonResponse({'url': base_picture.url, 'order': base_picture.order}, status=200)

    except UserProceeding.DoesNotExist:  # 사용자 진행 정보 x
        return JsonResponse({'error': 'User proceeding not found'}, status=404)
    except BasePictures.DoesNotExist:  # 선택된 그림x
        return JsonResponse({'error': 'Base picture not found'}, status=404)
    except IndexError:  # 인덱스 범위 아웃
        return JsonResponse({'error': 'Index out of range'}, status=400)


@require_http_methods(["GET"])
def get_picture(request):
    picture_id = request.GET.get('picture', None) #picture 요청
    
    if picture_id:
        try:
            picture_id = int(picture_id) - 1 #인덱스 0부터 시작
            picture = BasePictures.objects.get(picture_id=picture_id) # 해당 ID의 그림을 데이터베이스에서 가져옴
            return JsonResponse({'url': picture.url})
        except BasePictures.DoesNotExist:
            return JsonResponse({'error': 'Button not found'}, status=404)
    else:
        # 'picture' 매개변수가 제공되지 않았을 경우 오류 반환
        return JsonResponse({'error': 'No button name provided'}, status=400)

@require_http_methods(["POST"])
@csrf_exempt 
@require_http_methods(["POST"])
@csrf_exempt 
def adjust_level(request):
    user_id = request.session.get('user_id')  # 사용자ID

    if not user_id:  # 사용자ID 없으면 인증오류 반환
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    data = json.loads(request.body.decode('utf-8'))
    action = data.get('action')  # action 값 가져오기

    try:
        user_proceeding = UserProceeding.objects.get(user__user_id=user_id)  # 사용자 진행정보 DB 접근 
        old_level = user_proceeding.level

        # 'action' 값에 따라 레벨을 증가 또는 감소
        if action == 1 and user_proceeding.level < 4:
            user_proceeding.level += 1
        elif action == -1 and user_proceeding.level > 0:
            user_proceeding.level -= 1

        # 레벨 변경이 있을 경우 order를 조정하고 seen_pictures 초기화
        if old_level != user_proceeding.level:
            if user_proceeding.level in [0, 1, 2]:
                # 레벨 0, 1, 2는 0번 그림부터 시작
                user_proceeding.last_order = 0
            elif user_proceeding.level == 3:
                # picture_level 1의 마지막 그림 order를 찾음
                last_picture = BasePictures.objects.filter(level=1).order_by('-order').first()
                user_proceeding.last_order = last_picture.order if last_picture else 0
            elif user_proceeding.level == 4:
                # picture_level 2의 마지막 그림 order를 찾음
                last_picture = BasePictures.objects.filter(level=2).order_by('-order').first()
                user_proceeding.last_order = last_picture.order if last_picture else 0
            
            # 본 그림 목록 초기화
            user_proceeding.seen_pictures = []
            
            # 사용자 정확도 정보 초기화
            user_accuracy = UserAccuracy.objects.get(user_id=user_id)
            user_accuracy.successive_correct = 0
            user_accuracy.successive_wrong = 0
            user_accuracy.save()  # 변경 사항을 데이터베이스에 저장
            user_proceeding.save() 

            # 새 레벨과 last_order에 기반하여 이미지 URL 가져오기
            picture_level = user_proceeding.level if user_proceeding.level <= 2 else user_proceeding.level - 2
            picture = BasePictures.objects.filter(level=picture_level, order=user_proceeding.last_order).first()
            if picture:
                image_url = picture.url
                # seen_pictures에 현재 last_order를 추가하고 저장
                user_proceeding.seen_pictures.append(user_proceeding.last_order)  # seen_pictures에 추가
                user_proceeding.save()
            else:
                image_url = None  # 해당 레벨과 순서에 맞는 그림이 없는 경우

            # 세션에 새 레벨과 그림 레벨 저장
            request.session['level'] = user_proceeding.level
            request.session['picture_level'] = picture_level

            return JsonResponse({
                'new_level': user_proceeding.level,
                'first_picture_order': user_proceeding.last_order,
                'url': image_url
            }, status=200)
        else:
            # 레벨 변경이 없는 경우에도 기본 응답 반환
            picture_level = user_proceeding.level if user_proceeding.level <= 2 else user_proceeding.level - 2
            picture = BasePictures.objects.filter(level=picture_level, order=user_proceeding.last_order).first()
            image_url = picture.url if picture else None
            return JsonResponse({
                'new_level': user_proceeding.level,
                'first_picture_order': user_proceeding.last_order,
                'url': image_url
            }, status=200)

    except UserProceeding.DoesNotExist:
        return JsonResponse({'error': 'User proceeding not found'}, status=404)
    except BasePictures.DoesNotExist:
        return JsonResponse({'error': 'No base picture found for this level and order'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# 난이도 자동 조정 구현 테스트 필요    
@csrf_exempt
def adjust_level_with_accuracy(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    # JSON 데이터에서 accuracy 값을 추출
    data = json.loads(request.body)
    accuracy = data.get('accuracy', 0)  # 기본값 설정

    try:
        # 사용자 정확도와 진행 정보를 DB에서 가져옴
        user_accuracy = UserAccuracy.objects.get(user_id=user_id)
        user_proceeding = UserProceeding.objects.get(user=user_id)
        level_changed = False # 레벨 변경 여부 초기화

        # accuracy 값에 따라 연속 정답 또는 오답 수를 갱신
        if accuracy >= 0.6:
            user_accuracy.successive_correct += 1
            user_accuracy.successive_wrong = 0 #상 기록시 하 리셋
        elif accuracy < 0.2:
            user_accuracy.successive_wrong += 1
            user_accuracy.successive_correct = 0 #하 기록시 상 리셋
        else:
            user_accuracy.successive_correct = 0 #중 기록시 상,하 리셋
            user_accuracy.successive_wrong = 0

        # 연속 정답 수가 3 이상이면 레벨을 1 증가
        if user_accuracy.successive_correct >= 3:
            if user_proceeding.level < 4:
                user_proceeding.level += 1
                level_changed = True #level 변경
            user_accuracy.successive_correct = 0
        # 연속 오답 수가 2 이상이면 레벨을 1 감소
        elif user_accuracy.successive_wrong >= 2:
            if user_proceeding.level > 0:
                user_proceeding.level -= 1
                level_changed = True #level 변경
            user_accuracy.successive_wrong = 0

        # 변경된 진행 정보와 정확도 정보를 저장
        user_proceeding.save()
        user_accuracy.save()

        return JsonResponse({
            'current_level': user_proceeding.level,
            'successive_correct': user_accuracy.successive_correct,
            'successive_wrong': user_accuracy.successive_wrong,
            'level_changed': level_changed
        }, status=200)

    except UserAccuracy.DoesNotExist:
        return JsonResponse({'error': 'User accuracy record not found'}, status=404)
    except UserProceeding.DoesNotExist:
        return JsonResponse({'error': 'User proceeding not found'}, status=404)
