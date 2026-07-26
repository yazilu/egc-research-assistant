from fastapi import FastAPI
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 将项目 nltk_data 目录加入 NLTK 搜索路径
_nltk_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nltk_data')
if os.path.isdir(_nltk_data_dir):
    os.environ['NLTK_DATA'] = _nltk_data_dir

from router import history_rt, ai_serarch_rt, user_rt, egc_rt

app = FastAPI()

app.include_router(user_rt.router)
app.include_router(history_rt.router)
app.include_router(ai_serarch_rt.router)
app.include_router(egc_rt.router)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
