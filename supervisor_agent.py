import os
from typing import Annotated, Literal, Sequence, TypedDict, List
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_steps: List[str] 

def cypher_agent_node(state: AgentState):
    print("   [ Đang chạy Cypher Agent - Xử lý logic số liệu...]")
    response = AIMessage(content="[Cypher Agent]: Hệ thống hiện có 5,000 sản phẩm và 4,705 nhà bán hàng.")
    return {"messages": [response]}

def graph_rag_agent_node(state: AgentState):
    print("   [ Đang chạy GraphRAG Agent - Xử lý ngữ nghĩa vector...]")
    response = AIMessage(content="[GraphRAG Agent]: Phân tích review cho thấy 80% khách hàng chê sản phẩm giá rẻ vì lỗi móp méo hộp.")
    return {"messages": [response]}

class RouteDecision(BaseModel):
    next_steps: List[Literal["cypher_agent", "graph_rag_agent", "FINISH"]] = Field(
        description="""Quyết định linh hoạt:
        - Trả về ['cypher_agent'] nếu chỉ hỏi 1 vế về số liệu, đếm, tính tổng.
        - Trả về ['graph_rag_agent'] nếu chỉ hỏi 1 vế về lý do, cảm xúc, review.
        - Trả về ['cypher_agent', 'graph_rag_agent'] nếu câu hỏi chứa 2 vế đòi hỏi CẢ 2 chuyên môn.
        - Trả về ['FINISH'] nếu là câu chào hỏi."""
    )
    reasoning: str = Field(description="Lý do tại sao lại phân phối công việc như vậy.")

def supervisor_node(state: AgentState):
    print("\n [SUPERVISOR ĐANG SUY NGHĨ...]")
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(RouteDecision)
    
    system_prompt = """Bạn là Giám đốc Điều phối (Router) của hệ thống AI phân tích E-commerce.
    Nhiệm vụ: Đọc câu hỏi và gọi ĐÚNG, ĐỦ số lượng Agent cần thiết. Không gọi thừa.
    - 'cypher_agent': Thống kê, số liệu, cơ sở dữ liệu có cấu trúc.
    - 'graph_rag_agent': Phân tích văn bản, lý do, ngữ nghĩa phi cấu trúc.
    Tuyệt đối không tự trả lời câu hỏi chuyên môn, hãy giao việc. Nếu người dùng chào hỏi, hãy chào lại và chọn FINISH."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}")
    ])
    
    decision = (prompt | structured_llm).invoke({"messages": state["messages"]})
    
    print(f"   => Quyết định: Giao cho {decision.next_steps}")
    print(f"   => Lý do: {decision.reasoning}")
    
    if "FINISH" in decision.next_steps:
        normal_response = llm.invoke(state["messages"])
        return {"next_steps": ["FINISH"], "messages": [normal_response]}
        
    return {"next_steps": decision.next_steps}

workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("cypher_agent", cypher_agent_node)
workflow.add_node("graph_rag_agent", graph_rag_agent_node)

def route_step(state: AgentState):
    if "FINISH" in state["next_steps"]:
        return END
    return state["next_steps"]

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges("supervisor", route_step)
workflow.add_edge("cypher_agent", END)
workflow.add_edge("graph_rag_agent", END)

app = workflow.compile()

def chat_with_system(user_query: str):
    print(f"\n{'='*70}\n USER: {user_query}\n{'-'*70}")
    
    inputs = {"messages": [HumanMessage(content=user_query)]}
    final_state = app.invoke(inputs, config={"recursion_limit": 5})
            
    print("\n KẾT QUẢ TỔNG HỢP:")
    for msg in final_state['messages'][1:]: 
        print(f"  {msg.content}")

if __name__ == "__main__":
    # Test Case 1: Chỉ cần 1 Agent Số liệu
    chat_with_system("Hệ thống hiện tại có bao nhiêu nhà bán hàng?")
    
    # Test Case 2: Chỉ cần 1 Agent Ngữ nghĩa
    chat_with_system("Tại sao mọi người hay phàn nàn về sản phẩm này?")
    
    # Test Case 3: Cần CẢ 2 Agent song song
    chat_with_system("Có bao nhiêu sản phẩm trên hệ thống, và tại sao hàng giá rẻ hay bị chê?")
    
    # Test Case 4: Không cần Agent nào
    chat_with_system("Hi!")