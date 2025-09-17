from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import sqlite3
import os
import player_analysis
import get_player_puuid
from pydantic import BaseModel



app = FastAPI()

class AnalysisRequest(BaseModel):
    prev_result: dict
    avg_result: dict
    tier: str
    team: str

@app.get("/")
def root():
    return {"msg": "LOL Project API is running 🚀"}

@app.post("/analysis")
def root(req: AnalysisRequest):
    req = json.dump(req)
    comment = player_analysis.create_comment(
        req.prev_result,
        req.avg_result,
        req.tier,
        req.team
    )
    return comment
    

