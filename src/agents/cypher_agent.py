import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate 
from langchain_neo4j import Neo4jGraph
from langchain_neo4j import GraphCypherQAChain 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

# connect to DATABASE NEO4J
graph = Neo4jGraph(
    url=os.getenv("URI"),
    username=os.getenv("AUTH_USERNAME"),
    password=os.getenv("AUTH_PASSWORD")
)

# llm and chain
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# CYPHER LLM 
CYPHER_GENERATION_TEMPLATE = """Bạn là một chuyên gia Data Engineer viết mã Cypher cho cơ sở dữ liệu Neo4j.

QUY TẮC TỐI QUAN TRỌNG:
1. Chỉ sử dụng các Node và Relationship có trong Schema dưới đây.
2. TUYỆT ĐỐI KHÔNG viết nhiều câu lệnh tách biệt có nhiều chữ RETURN. Lệnh Cypher chỉ được có MỘT chữ RETURN ở cuối cùng.
3. NẾU CÂU HỎI CÓ NHIỀU VẾ (Ví dụ: "Có bao nhiêu sản phẩm, và tại sao khách hay chê?"):
   -> BẠN CHỈ ĐƯỢC PHÉP TRÍCH XUẤT CYPHER CHO PHẦN SỐ LIỆU, THỐNG KÊ (Có bao nhiêu sản phẩm). 
   -> Bỏ qua hoàn toàn phần hỏi về lý do, cảm xúc, review. Đừng cố gắng JOIN bảng Review nếu không được yêu cầu đếm đánh giá.
4. Trả về DUY NHẤT mã Cypher, không giải thích dài dòng.

Schema của Database:
{schema}

Câu hỏi của User: {question}
Cypher Query:"""

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template=CYPHER_GENERATION_TEMPLATE
)

# QA LLM
QA_TEMPLATE = """Bạn là một chuyên gia báo cáo số liệu.
Dựa trên kết quả truy vấn cơ sở dữ liệu dưới đây, hãy trả lời câu hỏi của người dùng.

LƯU Ý QUAN TRỌNG:
- CHỈ trả lời phần câu hỏi liên quan đến con số, thống kê mà kết quả truy vấn cung cấp.
- BỎ QUA HOÀN TOÀN các vế câu hỏi hỏi về lý do, đánh giá, cảm xúc (vì đã có chuyên gia khác xử lý). 
- Tuyệt đối KHÔNG xin lỗi hay nhắc đến việc thiếu thông tin cho phần lý do đó. Trả lời ngắn gọn, trực diện vào số liệu.

Kết quả truy vấn CSDL:
{context}

Câu hỏi của người dùng: {question}
Câu trả lời số liệu:"""

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"], 
    template=QA_TEMPLATE
)

cypher_chain = GraphCypherQAChain.from_llm(
    cypher_llm=llm,
    qa_llm=llm,
    graph=graph,
    verbose=True,
    allow_dangerous_requests=True,
    cypher_prompt=CYPHER_PROMPT,
    qa_prompt=QA_PROMPT 
)

# node for cypher_agent
def cypher_agent_node(state: dict):
    user_query = state["messages"][-1].content
    
    try:
        result = cypher_chain.invoke({"query": user_query})
        answer = result["result"]
    except Exception as e:
        answer = f"Xin lỗi, tôi gặp sự cố khi truy xuất dữ liệu từ Đồ thị: {str(e)}"
        
    return {"messages": [AIMessage(content=f"[Cypher Agent]: {answer}")]}

