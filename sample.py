import os
import json
import configparser
from typing import TypedDict

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# 1. API 키 로드
def load_api_key_from_ini(file_path="api.ini"):
    config = configparser.ConfigParser()
    config.read(file_path)
    try:
        os.environ["OPENAI_API_KEY"] = config["api"]["key"]
        print("✅ API key loaded.")
    except KeyError:
        raise RuntimeError("❌ 'api.ini'에 [api] 섹션 또는 key 항목이 없습니다.")
load_api_key_from_ini()

# 2. LLM 설정
llm_o1 = ChatOpenAI(model="o1")
llm_main = ChatOpenAI(model="gpt-4o", temperature=0.7)

# 3. 프롬프트 정의
prompt1 = PromptTemplate.from_template("""
Please analyze the sentiment of the following sentence and respond in JSON format like this:

{{ 
  "sentiment": "<positive | negative | neutral>", 
  "reason": "<brief explanation>" 
}}

Sentence: {input}
""")

prompt2 = PromptTemplate.from_template("""
You said something positive. Compliment it or build on it constructively:
"{input}"
""")

prompt3 = PromptTemplate.from_template("""
You expressed something negative. Respond with empathy and suggestions:
"{input}"
""")

# 4. 상태 스키마 정의
class SentimentState(TypedDict, total=False):
    input: str
    sentiment: str
    analysis_result: dict
    final_response: str

# 5. 노드 함수 정의
def analyze_sentiment(state: SentimentState) -> SentimentState:
    result = (prompt1 | llm_o1).invoke({"input": state["input"]})
    print("[Analysis Result]\n", result.content)
    try:
        parsed = json.loads(result.content)
        state["sentiment"] = parsed.get("sentiment", "").lower()
        state["analysis_result"] = parsed
    except json.JSONDecodeError:
        raise RuntimeError("❌ 감정 분석 결과가 JSON 형식이 아닙니다.")
    return state

def respond_positive(state: SentimentState) -> SentimentState:
    result = (prompt2 | llm_main).invoke({"input": state["input"]})
    state["final_response"] = result.content
    return state

def respond_negative(state: SentimentState) -> SentimentState:
    result = (prompt3 | llm_main).invoke({"input": state["input"]})
    state["final_response"] = result.content
    return state

# 6. 조건 분기
def route_sentiment(state: SentimentState) -> str:
    sentiment = state.get("sentiment", "")
    return "positive_response" if sentiment == "positive" else "negative_response"

# 7. LangGraph 정의
builder = StateGraph(state_schema=SentimentState)

builder.add_node("analyze", analyze_sentiment)
builder.add_node("positive_response", respond_positive)
builder.add_node("negative_response", respond_negative)

builder.set_entry_point("analyze")
builder.add_conditional_edges(
    "analyze",
    route_sentiment,
    {
        "positive_response": "positive_response",
        "negative_response": "negative_response",
    }
)

builder.add_edge("positive_response", END)
builder.add_edge("negative_response", END)

graph = builder.compile()

# 8. 실행
if __name__ == "__main__":
    input_text = "I absolutely love how intuitive the UI is."
    result = graph.invoke({"input": input_text})
    print("\n=== Final Response ===")
    print(result["final_response"])