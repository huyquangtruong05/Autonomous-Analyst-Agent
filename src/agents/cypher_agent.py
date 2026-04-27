import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_neo4j import Neo4jGraph
from langchain_neo4j import GraphCypherQAChain 

from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

# connect database
graph = Neo4jGraph(
    url=os.getenv("URI"),
    username=os.getenv("AUTH_USERNAME"),
    password=os.getenv("AUTH_PASSWORD")
)


llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

CYPHER_GENERATION_TEMPLATE = """Bạn là một chuyên gia Data Engineer viết mã Cypher cho cơ sở dữ liệu Neo4j.
Nhiệm vụ: Chuyển đổi câu hỏi bằng Tiếng Việt sang một câu lệnh Cypher duy nhất.

QUY TẮC TỐI QUAN TRỌNG:
1. Chỉ sử dụng các Node và Relationship có trong Schema dưới đây.
2. TUYỆT ĐỐI KHÔNG viết nhiều câu lệnh tách biệt có nhiều chữ RETURN. Lệnh Cypher chỉ được có MỘT chữ RETURN ở cuối cùng.
3. Nếu cần đếm/truy vấn nhiều loại Node khác nhau trong cùng một câu hỏi, HÃY DÙNG TỪ KHÓA 'WITH' ĐỂ CHUỖI CHÚNG LẠI. 
   Ví dụ MẪU CHUẨN: MATCH (s:Seller) WITH count(s) as sellers MATCH (p:Product) RETURN sellers, count(p) as products
4. Trả về DUY NHẤT mã Cypher, không giải thích dài dòng.

Schema của Database:
{schema}

Câu hỏi của User: {question}
Cypher Query:"""

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template=CYPHER_GENERATION_TEMPLATE
)

cypher_chain = GraphCypherQAChain.from_llm(
    cypher_llm=llm,
    qa_llm=llm,
    graph=graph,
    verbose=True,
    allow_dangerous_requests=True,
    cypher_prompt=CYPHER_PROMPT # direction for llm
)

def cypher_agent_node(state: dict):
    print("\n   [ Cypher Agent đang truy cập Database...]")
    user_query = state["messages"][-1].content
    
    try:
        result = cypher_chain.invoke({"query": user_query})
        answer = result["result"]
    except Exception as e:
        answer = f"Xin lỗi, tôi gặp sự cố khi truy xuất dữ liệu từ Đồ thị: {str(e)}"
        
    return {"messages": [AIMessage(content=f"[Cypher Agent]: {answer}")]}

if __name__ == "__main__":
    print(" ĐANG KIỂM TRA ĐỘNG CƠ CYPHER AGENT...\n")
    
    mock_state = {
        "messages": [
            AIMessage(content="Người dùng vừa hỏi câu dưới đây:"),
            AIMessage(content="Có bao nhiêu nhà bán hàng và bao nhiêu sản phẩm trên hệ thống?")
        ]
    }
    
    result = cypher_agent_node(mock_state)
    
    print("\n" + "="*50)
    print(" CÂU TRẢ LỜI TỪ AGENT:")
    print(result["messages"][0].content)
    print("="*50)