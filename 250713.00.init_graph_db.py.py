from db import create_connection
from datetime import datetime

# SQL 초기화 스크립트
INIT_SCRIPT = """
DROP TABLE IF EXISTS graph_flows;
DROP TABLE IF EXISTS graph_components;
DROP TABLE IF EXISTS graph_prompts;

CREATE TABLE graph_prompts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prompt TEXT NOT NULL,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE graph_components (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code TEXT NOT NULL,
    prompt_id INT DEFAULT NULL,
    is_executable BOOLEAN DEFAULT FALSE,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE graph_flows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    flow_json JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
"""

# 초기 삽입 데이터
PROMPTS = [
    '''
Please analyze the sentiment of the following sentence and respond in JSON format like this:

{{ 
  "sentiment": "<positive | negative | neutral>", 
  "reason": "<brief explanation>" 
}}

Sentence: {input}
''',
    '''
You said something positive. Compliment it or build on it constructively:
"{input}"
''',
    '''
You expressed something negative. Respond with empathy and suggestions:
"{input}"
'''
]

COMPONENTS = [
    (
        "analyze_sentiment",
        '''def analyze_sentiment(state: SentimentState) -> SentimentState:
    result = (prompt1 | llm_o1).invoke({"input": state["input"]})
    print("[Analysis Result]\\n", result.content)
    try:
        parsed = json.loads(result.content)
        state["sentiment"] = parsed.get("sentiment", "").lower()
        state["analysis_result"] = parsed
    except json.JSONDecodeError:
        raise RuntimeError("❌ 감정 분석 결과가 JSON 형식이 아닙니다.")
    return state''',
        1, True
    ),
    (
        "respond_positive",
        '''def respond_positive(state: SentimentState) -> SentimentState:
    result = (prompt2 | llm_main).invoke({"input": state["input"]})
    state["final_response"] = result.content
    return state''',
        2, True
    ),
    (
        "respond_negative",
        '''def respond_negative(state: SentimentState) -> SentimentState:
    result = (prompt3 | llm_main).invoke({"input": state["input"]})
    state["final_response"] = result.content
    return state''',
        3, True
    ),
    (
        "route_sentiment",
        '''def route_sentiment(state: SentimentState) -> str:
    sentiment = state.get("sentiment", "")
    return "positive_response" if sentiment == "positive" else "negative_response"''',
        None, True
    )
]

FLOW_JSON = '''{
  "entry_point": "analyze",
  "nodes": [
    {"name": "analyze", "component": "analyze_sentiment"},
    {"name": "positive_response", "component": "respond_positive"},
    {"name": "negative_response", "component": "respond_negative"}
  ],
  "edges": [
    {"from": "positive_response", "to": "__END__"},
    {"from": "negative_response", "to": "__END__"}
  ],
  "conditional_edges": {
    "from": "analyze",
    "router": "route_sentiment",
    "conditions": {
      "positive_response": "positive_response",
      "negative_response": "negative_response"
    }
  }
}'''


def initialize_database():
    conn = create_connection()
    cursor = conn.cursor()

    print("🚧 Dropping and creating tables...")
    for statement in INIT_SCRIPT.strip().split(";"):
        if statement.strip():
            cursor.execute(statement + ";")

    print("📝 Inserting prompts...")
    for prompt in PROMPTS:
        cursor.execute("INSERT INTO graph_prompts (prompt) VALUES (%s)", (prompt,))
    conn.commit()

    print("📝 Inserting components...")
    for name, code, prompt_id, is_exec in COMPONENTS:
        cursor.execute(
            "INSERT INTO graph_components (name, code, prompt_id, is_executable) VALUES (%s, %s, %s, %s)",
            (name, code, prompt_id, is_exec)
        )
    conn.commit()

    print("📝 Inserting flow definition...")
    cursor.execute(
        "INSERT INTO graph_flows (name, flow_json) VALUES (%s, %s)",
        ("sentiment_analysis_flow", FLOW_JSON)
    )
    conn.commit()

    cursor.close()
    conn.close()
    print("✅ Database initialized successfully.")


if __name__ == "__main__":
    initialize_database()
