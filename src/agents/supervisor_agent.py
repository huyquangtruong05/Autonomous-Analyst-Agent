import os
from typing import Annotated, Literal, Sequence, TypedDict, List
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from src.agents.cypher_agent import cypher_agent_node
from src.agents.graph_rag_agent import graph_rag_agent_node


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_steps: List[str] 

class RouteDecision(BaseModel):
    next_steps: List[Literal["cypher_agent", "graph_rag_agent", "FINISH"]] = Field(
        description="""Quyết định linh hoạt:
        - ['cypher_agent']: Hỏi về số liệu, đếm, tính tổng, giá cả, nhà bán hàng, danh mục.
        - ['graph_rag_agent']: Hỏi về lý do, đánh giá, review, cảm xúc khách hàng.
        - ['cypher_agent', 'graph_rag_agent']: Câu hỏi có cả 2 ý trên.
        - ['FINISH']: Câu chào hỏi bình thường."""
    )
    reasoning: str = Field(description="Lý do phân bổ công việc.")


def supervisor_node(state: AgentState):
    
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
    # if both agents are needed, we can run them in parallel and then merge results at the end
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
            
    print("\n AI RESPONSE:")
    
    responses = []
    for msg in final_state['messages'][1:]: 
        print(f"  {msg.content}")
        responses.append(msg.content)

    return " ".join(responses)   
    