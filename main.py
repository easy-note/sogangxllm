from imp import reload
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import httpx
from typing import List, Optional
import uvicorn
import uuid
from starlette.responses import RedirectResponse
from starlette.background import BackgroundTasks

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# Templates 설정
templates = Jinja2Templates(directory="templates")

# Ollama API 엔드포인트
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# 선택 옵션들
CHOICES = {
    'page1': ['가족', '친구', '애인', '혼자'],
    'page2': ['외식', '영화', '운동'],
    'page3': ['한식', '양식', '중식']
}

# 결과를 저장할 전역 변수
result_store = {}

async def generate_result(session_id: str, keywords: List[str]):
    """백그라운드에서 결과 생성"""
    prompt = generate_prompt(keywords)
    try:
        response = await call_ollama(prompt)
        result_store[session_id] = {
            'ready': True,
            'result': response,
            'keywords': keywords
        }
    except Exception as e:
        result_store[session_id] = {
            'ready': True,
            'error': str(e),
            'keywords': keywords
        }
        
        
def generate_prompt(keywords: List[str]) -> str:
    """키워드들을 기반으로 프롬프트 생성"""
    # return f"""당신은 선택된 키워드를 바탕으로 맞춤형 일정을 추천해주는 어시스턴트입니다.

    #         상황:
    #         - 함께하는 사람: {keywords[0]}
    #         - 하고 싶은 활동: {keywords[1]}
    #         - 선호하는 음식: {keywords[2]}

    #         다음 사항을 고려하여 구체적인 일정을 추천해주세요:
    #         1. 시간대별 활동 계획
    #         2. 추천하는 특정 장소나 맛집
    #         3. 예상 비용
    #         4. 준비물이나 주의사항

    #         친근하고 상세한 어투로 설명해주세요."""
    
    messages = "안녕? 한국어 가능해?. 답변은 무조건 한국어로 해줘. "


    return messages



async def call_ollama(prompt: str) -> str:
    """Ollama API 호출"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # 타임아웃 시간 증가
            print(f"Sending request to Ollama API with prompt: {prompt}")
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": "llama3.2",  # llama3.2 대신 llama2를 사용
                    "prompt": prompt,
                    "stream": False,
                }
            )
            print(f"Ollama API response status: {response.status_code}")
            print(f"Ollama API response: {response.text}")
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status code {response.status_code}")
                
            response_json = response.json()
            return response_json.get("response", "No response generated")
            
    except Exception as e:
        print(f"Error calling Ollama API: {str(e)}")
        raise
    
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """첫 번째 페이지"""
    request.session.clear()
    return templates.TemplateResponse(
        "select.html",
        {
            "request": request,
            "page_num": 1,
            "options": CHOICES['page1'],
            "selected_keywords": []
        }
    )

@app.post("/select/1", response_class=HTMLResponse)
async def select_page1(request: Request, keyword: str = Form(...)):
    """첫 번째 선택 처리"""
    request.session['keyword1'] = keyword
    return templates.TemplateResponse(
        "select.html",
        {
            "request": request,
            "page_num": 2,
            "options": CHOICES['page2'],
            "selected_keywords": [keyword]
        }
    )

@app.post("/select/2", response_class=HTMLResponse)
async def select_page2(request: Request, keyword: str = Form(...)):
    """두 번째 선택 처리"""
    keyword1 = request.session.get('keyword1')
    request.session['keyword2'] = keyword
    return templates.TemplateResponse(
        "select.html",
        {
            "request": request,
            "page_num": 3,
            "options": CHOICES['page3'],
            "selected_keywords": [keyword1, keyword]
        }
    )


@app.post("/select/3", response_class=HTMLResponse)
async def select_page3(
    request: Request, 
    background_tasks: BackgroundTasks,
    keyword: str = Form(...),
    
):
    """세 번째 선택 처리 및 결과 생성"""
    try:
        keyword1 = request.session.get('keyword1')
        keyword2 = request.session.get('keyword2')
        keywords = [keyword1, keyword2, keyword]
        
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        request.session['result_id'] = session_id
        
        # 결과 초기화
        result_store[session_id] = {
            'ready': False,
            'keywords': keywords
        }
        
        # 백그라운드에서 결과 생성 시작
        background_tasks.add_task(generate_result, session_id, keywords)
        
        # 로딩 페이지로 이동
        return templates.TemplateResponse(
            "loading.html",
            {
                "request": request,
                "keywords": keywords
            }
        )
    except Exception as e:
        print(f"Error in select_page3: {str(e)}")
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "keywords": keywords if 'keywords' in locals() else [],
                "story": None,
                "error": f"오류가 발생했습니다: {str(e)}"
            }
        )

@app.get("/check_result")
async def check_result(request: Request):
    """결과 생성 상태 확인"""
    session_id = request.session.get('result_id')
    if not session_id or session_id not in result_store:
        return {"ready": False}
    
    return {"ready": result_store[session_id]['ready']}

@app.get("/result", response_class=HTMLResponse)
async def show_result(request: Request):
    """결과 표시"""
    session_id = request.session.get('result_id')
    if not session_id or session_id not in result_store:
        return RedirectResponse(url='/')
        
    result_data = result_store[session_id]
    
    # 결과 표시 후 삭제
    del result_store[session_id]
    
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "keywords": result_data['keywords'],
            "story": result_data.get('result'),
            "error": result_data.get('error')
        }
    )
        
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
