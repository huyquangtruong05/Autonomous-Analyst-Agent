import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_neo4j import Neo4jVector
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

# model local MiniLM-L12 to embed rv 
embeddings = HuggingFaceEmbeddings(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# connect to neo4j database and use existing vector index "review_vector"
vector_store = Neo4jVector.from_existing_index(
    embedding=embeddings,
    url=os.getenv("URI"),
    username=os.getenv("AUTH_USERNAME"),
    password=os.getenv("AUTH_PASSWORD"),
    index_name="review_vector",          
    text_node_property="content",        
)

# use Groq LLM for better Vietnamese understanding and generation
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

# search tools: retriever from neo4j vector index
retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# Prompt for llama-3.3-70b-versatile to answer questions based on retrieved reviews
# write prompt to guide AI how to answer
template = """Bạn là chuyên gia phân tích đánh giá khách hàng E-commerce.
Hãy sử dụng các đánh giá của khách hàng (Ngữ cảnh) dưới đây để trả lời câu hỏi.

LƯU Ý QUAN TRỌNG: 
- Chỉ tập trung trả lời các ý hỏi về lý do, đánh giá, cảm xúc, chất lượng.
- BỎ QUA HOÀN TOÀN các ý hỏi về đếm số lượng, thống kê số liệu (ví dụ: "có bao nhiêu sản phẩm"). KHÔNG CẦN xin lỗi hay giải thích về việc thiếu số liệu.
- Nếu trong ngữ cảnh không có thông tin chê bai, hãy nói "Dựa trên các dữ liệu hiện có, hầu hết khách hàng đều hài lòng và chưa ghi nhận phàn nàn về vấn đề này."

Ngữ cảnh (Các review liên quan):
{context}

Câu hỏi của sếp: {query}
Câu trả lời:"""
prompt = PromptTemplate.from_template(template)

# format
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


qa_chain = (
    {"context": retriever | format_docs, "query": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# node for graph_rag_agent
def graph_rag_agent_node(state: dict):
    user_query = state["messages"][-1].content
    
    try:
        answer = qa_chain.invoke(user_query)
    except Exception as e:
        answer = f"Lỗi truy xuất GraphRAG: {str(e)}"

    return {"messages": [AIMessage(content=f"[GraphRAG Agent]: {answer}")]}
