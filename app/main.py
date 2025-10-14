from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import sqlite3
import os
import player_analysis
import get_player_puuid
from pydantic import BaseModel
from typing import List
import torch
from item_model import recommend_items_filtered



app = FastAPI()

class AnalysisRequest(BaseModel):
    prev_result: dict
    avg_result: dict
    tier: str
    team: str

class ItemFeedbackRequest(BaseModel):
    my_roles: List[str]                
    enemy_roles: List[List[str]]     


@app.get("/")
def root():
    return {"msg": "LOL Project API is running 🚀"}

@app.post("/analysis")
def root(req: AnalysisRequest):
    comment = player_analysis.create_comment(
        req.prev_result,
        req.avg_result,
        req.tier,
        req.team
    )
    return comment
    
@app.post("/item_feedback")
def item_feedback(req: ItemFeedbackRequest):
    top_items = recommend_items_filtered(req.my_roles, req.enemy_roles, top_n=5)
    return {"recommended_items": top_items}

