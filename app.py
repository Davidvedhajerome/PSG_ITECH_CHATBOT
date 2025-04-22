from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from scrape_data import update_cutoff_data
import json
import re

load_dotenv()

app = FastAPI()

# CORS & Static
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load or update college data
if not os.path.exists("college_data.json"):
    college_data = {"colleges": []}
    update_cutoff_data()
else:
    with open("college_data.json", "r", encoding="utf-8") as f:
        college_data = json.load(f)
    update_cutoff_data()

# LangChain setup
embeddings = OpenAIEmbeddings()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_text(str(college_data))
vectorstore = Chroma.from_texts(texts, embeddings)

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    memory=memory
)

class Query(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot(request: Request):
    return templates.TemplateResponse("chatbot.html", {"request": request})

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(query: Query):
    try:
        result = qa_chain({"question": query.question})
        raw_answer = result["answer"]

        # Convert markdown bold **text** -> <b>text</b>
        formatted = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", raw_answer)

        # Convert bullet-style "- " to HTML bullets
        formatted = formatted.replace("\n- ", "<br>&bull; ")
        formatted = formatted.replace("\n", "<br>")

        # Detect links and convert them to clickable HTML anchors
        formatted = re.sub(
            r"(https?://[^\s]+)",
            r'<a href="\1" target="_blank" style="color:#1a73e8;text-decoration:underline;">\1</a>',
            formatted
        )

        return ChatResponse(answer=formatted)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-cutoffs")
async def update_cutoffs():
    try:
        new_cutoffs = update_cutoff_data()
        return {"message": f"Updated cut-off data with {len(new_cutoffs)} new PDFs"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
