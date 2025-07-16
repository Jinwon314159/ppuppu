import os
import json
import configparser
from types import FunctionType
from typing import TypedDict
from db import create_connection

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END


def load_api_key_from_ini(file_path="api.ini"):
    config = configparser.ConfigParser()
    config.read(file_path)
    try:
        os.environ["OPENAI_API_KEY"] = config["api"]["key"]
        print("✅ API key loaded.")
    except KeyError:
        raise RuntimeError("❌ 'api.ini'에 [api] 섹션 또는 key 항목이 없습니다.")


load_api_key_from_ini()


# 상태 스키마 (공통)
class SentimentState(TypedDict, total=False):
    input: str
    sentiment: str
    analysis_result: dict
    final_response: str


def load_prompt_templates():
    """프롬프트 DB에서 모두 불러와 PromptTemplate 객체로 매핑"""
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, prompt FROM graph_prompts")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {row["id"]: PromptTemplate.from_template(row["prompt"]) for row in rows}


def load_components(prompt_templates: dict):
    """컴포넌트 DB에서 불러와 실제 실행 가능한 함수로 반환"""
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM graph_components")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # 필요 시 기본 LLM 인스턴스 (하드코딩 가능)
    llm_o1 = ChatOpenAI(model="o1")
    llm_main = ChatOpenAI(model="gpt-4o", temperature=0.7)

    namespace = {
        "json": json,
        "llm_o1": llm_o1,
        "llm_main": llm_main,
        "PromptTemplate": PromptTemplate,
        "SentimentState": SentimentState
    }

    # 프롬프트도 등록
    for pid, template in prompt_templates.items():
        namespace[f"prompt{pid}"] = template

    component_functions = {}

    for row in rows:
        try:
            exec(row["code"], namespace)
            fn = namespace.get(row["name"])
            if isinstance(fn, FunctionType):
                component_functions[row["name"]] = fn
        except Exception as e:
            print(f"❌ Error loading component {row['name']}: {e}")

    return component_functions


def build_langgraph(flow_name: str):
    """지정된 플로우 이름으로 LangGraph 빌드"""
    # 1. DB에서 flow_json 불러오기
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT flow_json FROM graph_flows WHERE name = %s AND is_active = TRUE", (flow_name,))
    row = cursor.fetchone()

    if not row:
        raise ValueError(f"Flow '{flow_name}' not found in DB.")

    flow_data = json.loads(row["flow_json"])

    cursor.close()
    conn.close()

    # 2. 필요한 리소스 로드
    prompt_templates = load_prompt_templates()
    component_functions = load_components(prompt_templates)

    # 3. 그래프 빌드
    builder = StateGraph(state_schema=SentimentState)

    # 노드 추가
    for node in flow_data["nodes"]:
        name = node["name"]
        func_name = node["component"]
        fn = component_functions.get(func_name)
        if not fn:
            raise RuntimeError(f"Component function '{func_name}' not found.")
        builder.add_node(name, fn)

    # 진입점
    builder.set_entry_point(flow_data["entry_point"])

    # 조건 분기
    if "conditional_edges" in flow_data:
        c = flow_data["conditional_edges"]
        router_fn = component_functions.get(c["router"])
        if not router_fn:
            raise RuntimeError(f"Routing function '{c['router']}' not found.")
        builder.add_conditional_edges(
            c["from"],
            router_fn,
            c["conditions"]
        )

    # 일반 간선 추가
    for edge in flow_data.get("edges", []):
        _from = edge["from"]
        _to = edge["to"]
        builder.add_edge(_from, END if _to == "__END__" else _to)

    return builder.compile()


if __name__ == "__main__":
    graph = build_langgraph("sentiment_analysis_flow")
    result = graph.invoke({"input": "I absolutely love how intuitive the UI is."})
    print("\n=== Final Response ===")
    print(result["final_response"])
