from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .game_manager import GameManager
from .schemas import *

app = FastAPI()
manager = GameManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/game/new")
def new_game():
    return manager.new_game()


@app.get("/api/game/state")
def state():
    return manager.get_public_state()


@app.post("/api/game/play")
def play(req: CardActionRequest):
    return manager.play_card(req.card_id)


@app.post("/api/game/give")
def give(req: CardActionRequest):
    return manager.give_card(req.card_id)


@app.post("/api/game/continue")
def cont(req: ContinueRequest):
    return manager.choose_continuation(req.continue_choice)


@app.post("/api/game/advance")
def advance():
    return manager.advance_ai()