
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
from typing import List
import uvicorn
import uuid
from starlette.responses import RedirectResponse
from starlette.background import BackgroundTasks

from apis import get_whether, get_activities

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

templates = Jinja2Templates(directory="templates")

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# 선택 옵션 구성
CHOICES = {
    'page1': ['솔로 플랜', '프렌즈 데이', '패밀리 타임', '커플 데이트'],
    'page2': ['둘만의 시간', '다함께 즐기기'],
    'page3': ['성동/왕십리', '마포/홍대', '종로/광화문', '강남/역삼', '노원/공릉'],
    'page4': ['실내 액티비티', '아웃도어 플랜']
}

result_store = {}

async def generate_result(session_id: str, keywords: List[str]):
    prompt = await generate_prompt(keywords)
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

async def generate_fisrt_prompt(keywords: List[str]) -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            initial_prompt = f'''
            "키워드를 보고 적절하게 활용할 수 있는 API를 골라주세요
            I want you to act as an API expert for Korean.

                [사용 가능한 API 목록]
                0: 날씨 정보 API
                1: 지역 놀거리 정보 API
                2: 지역 축제 정보 API
                3: 블로그 맛집 리뷰 API
                4: 블로그 노래 리뷰 API
                5: 블로그 넷플릭스 리뷰 API
                6: 상영 중인 영화 리뷰 API

                [사용자 상황]
                - 모임 멤버: {keywords[0]}
                - 모임 유형: {keywords[1]}
                - 활동 지역: {keywords[2]}
                - 활동 환경: {keywords[3]}
            '''
            
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": "llama3.2",
                    "prompt": initial_prompt,
                    "stream": False,
                }
            )
            
            if response.status_code != 200:
                return "한국어 체크 실패"
                
            response_json = response.json()
            return response_json.get("response", "응답 없음")
    
    except Exception as e:
        print(f"Error in check_llama_korean: {str(e)}")
        return "에러 발생"

async def generate_prompt(keywords: List[str]) -> str:
    # recommend_apis = await generate_fisrt_prompt(keywords)
    recommend_apis = [0, 1, 2]
    print(recommend_apis)
    
    if 0 in recommend_apis:
        if keywords[2] == '성동/왕십리':
            xn, xy = (61,127)
        elif keywords[2] == '마포/홍대':
            xn, xy = (59, 127)
        elif keywords[2] == '종로/광화문':
            xn, xy = (60, 127)
        elif keywords[2] == '강남/역삼':
            xn, xy = (61, 126)  
        else:
            xn, xy = (61, 129)

        whether_info = get_whether.run(xn, xy)
        print(whether_info)

    if 1 in recommend_apis:
        activities_info = get_activities.run(keywords[2])
        print(activities_info)
    
    ## TODO - 2, 3, 4, 5, 6 index 에 대한 api 호출 추가
    
    second_prompt = f'''
        오늘 뭘 할지 아무것도 정하지 못한 사용자 상황을 보고, API 정보를 활용해주세요.
        사용자가 할 만한 것을 파악하여 하루를 참신하게 계획해주세요.

        Let's think step by step!
        I want you to act as an daily plan expert for Korean.

        [사용자 상황]

        - 모임 멤버: {keywords[0]}
        - 모임 유형: {keywords[1]}
        - 활동 지역: {keywords[2]}
        - 활동 환경: {keywords[3]}

        [API 정보]
        {whether_info}
        {activities_info}

        [응답조건]
        (중요) 완전한 한국어로만 답변해주세요. * 텍스트는 포함하지 말아주세요. 
        보기 명확한 리스트 형식으로 주세요.
        시간별로 구분하지 않아도 됩니다. 대신 카테고리 별로 보기 좋게 정리해주세요.
    '''
    

    return second_prompt

async def call_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"Sending request to Ollama API with prompt: {prompt}")
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": "llama3.2", 
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
async def select_page3(request: Request, keyword: str = Form(...)):
    keyword1 = request.session.get('keyword1')
    keyword2 = request.session.get('keyword2')
    request.session['keyword3'] = keyword
    return templates.TemplateResponse(
        "select.html",
        {
            "request": request,
            "page_num": 4,
            "options": CHOICES['page4'],
            "selected_keywords": [keyword1, keyword2, keyword]
        }
    )

@app.post("/select/4", response_class=HTMLResponse)
async def select_page4(
    request: Request, 
    background_tasks: BackgroundTasks,
    keyword: str = Form(...)
):
    try:
        keyword1 = request.session.get('keyword1')
        keyword2 = request.session.get('keyword2')
        keyword3 = request.session.get('keyword3')
        keywords = [keyword1, keyword2, keyword3, keyword]
        
        session_id = str(uuid.uuid4())
        request.session['result_id'] = session_id
        
        result_store[session_id] = {
            'ready': False,
            'keywords': keywords
        }
        
        background_tasks.add_task(generate_result, session_id, keywords)
        
        return templates.TemplateResponse(
            "loading.html",
            {
                "request": request,
                "keywords": keywords
            }
        )
    except Exception as e:
        print(f"Error in select_page4: {str(e)}")
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
    session_id = request.session.get('result_id')
    if not session_id or session_id not in result_store:
        return {"ready": False}
    
    return {"ready": result_store[session_id]['ready']}

@app.get("/result", response_class=HTMLResponse)
async def show_result(request: Request):
    session_id = request.session.get('result_id')
    if not session_id or session_id not in result_store:
        return RedirectResponse(url='/')
        
    result_data = result_store[session_id]
    
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