import { showPopup, hidePopup} from './popup.js';

document.addEventListener("DOMContentLoaded", function() {
    let container = document.querySelector('.navbar-progress-container');
    let progressBar = document.querySelector('progress');
    let analysis_popup = document.getElementById("analysisPopup");
    let exitPopup=document.getElementById("exitPopup");
    //let messageContainer = document.getElementById("messageContainer"); // 비슷한것같나요 메시지 컨테이너
    //let imagePopup = document.getElementById("imagePopup"); // 비교이미지 팝업
  
    /*시간 설정*/
    let duration = 15000; // 프로그레스바 15초
    //let hideDuration = 30000; // navbar+progressbar 사라지는 시간 30초(변수만 설정, 아직 미구현)
    let popupDuration = 15000; // 분석중입니다 팝업시간 15초
  
    /*프로그레스바 감소*/
    function updateProgressBar() {
      let decrementAmount = progressBar.max / (duration / 100); // Calculate decrement per 100ms
      progressBar.value -= decrementAmount;
      if (progressBar.value <= 0) {
        clearInterval(progressInterval);
        hideElements(); //프로그레스바 0 -> 요소사라짐
      }
    }  
    let progressInterval = setInterval(updateProgressBar, 100);  


  
    /*navbar+progressbar 사라짐 + 로딩중 팝업 */
    function hideElements(){

      analysis_popup.style.display = "flex"; //analysis popup 보이기 
      showPopup("analysisPopup");
      

      //hidePopup("analysisPopup");

      
      showElements(); //navbar+progressbar 다시 보여주는 함수

    }
  
    function showElements() { //여기에 비교 텍스트, 비교이미지 보여주는 것 구현 추가할 예정
      container.style.transform = 'translateY(0)'; //navbar+progress bar 다시 보여주기
      container.style.opacity = 1;
    }
  
  
  //  var byebye = ["벌써 가시나요? 다음에 또 봐요.", "안녕히가세요!", "다음에 또 오실거죠? 기다리고 있을게요."];
  //    var randomByebye = byebye[Math.floor(Math.random() * byebye.length)]; // 랜덤인사
  //    document.getElementById('random-byebye').textContent = randomByebye; 
    
  });
  
  
  
  //모든 학습파일
  function visible(current, total){
    var arr = [];
    for(let k = 0; k< total; k++){
      arr[k] = k+"text";
    }
    var con = document.getElementById(arr[current]);
    for(let j = 0; j<arr.length; j++){
      var hid = document.getElementById(arr[j]);
      hid.style.display = 'none';
    }   
    con.style.display = 'block';    
    
  }
  
  
  
  console.log("보내기");console.log("보내기");console.log("보내기");console.log("보내기");
  
  
