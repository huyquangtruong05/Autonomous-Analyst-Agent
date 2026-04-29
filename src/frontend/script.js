document.addEventListener("DOMContentLoaded", () => {
  // DOM elements
  const landingPage = document.getElementById("landing-page");
  const chatContainer = document.getElementById("chat-container");
  const loginBtn = document.getElementById("login-btn");
  const getStartedBtn = document.getElementById("get-started-btn");
  const heroCta = document.getElementById("hero-cta");
  const ctaStart = document.getElementById("cta-start");
  const backBtn = document.getElementById("back-to-landing");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const chatMessages = document.getElementById("chat-messages");

  landingPage.style.display = "block";
  chatContainer.style.display = "none";

  // Function to switch to chat view
  function openChat() {
    landingPage.style.display = "none";
    chatContainer.style.display = "flex";
    setTimeout(() => userInput.focus(), 100);
  }

  // Function to go back to landing
  function closeChat() {
    chatContainer.style.display = "none";
    landingPage.style.display = "block";
  }

  [loginBtn, getStartedBtn, heroCta, ctaStart].forEach((btn) => {
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openChat();
      });
    }
  });

  if (backBtn) {
    backBtn.addEventListener("click", closeChat);
  }

  // Chat
  function addMessage(text, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender);
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    if (sender === "bot") {
      messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="bot-icon"><i class="fas fa-robot"></i></div>
                    <div class="text">
                        <p>${text}</p>
                        <span class="time">${timeStr}</span>
                    </div>
                </div>
            `;
    } else {
      messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="text">
                        <p>${text}</p>
                        <span class="time">${timeStr}</span>
                    </div>
                </div>
            `;
    }
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function getAIResponse(userMessage) {
    const lowerMsg = userMessage.toLowerCase();
    if (lowerMsg.includes("revenue") || lowerMsg.includes("doanh thu")) {
      return "Based on the latest quarter, revenue increased by 18% YoY. The main drivers were the new product line and improved customer retention. I'd recommend reallocating budget toward top-performing channels.";
    } else if (lowerMsg.includes("trend") || lowerMsg.includes("xu hướng")) {
      return "I've detected an upward trend in user engagement over the last 30 days. Mobile usage is up 34%, suggesting we should prioritize mobile experience improvements.";
    } else if (lowerMsg.includes("report") || lowerMsg.includes("báo cáo")) {
      return "I can generate a full performance report for you. It will cover KPIs, cohort analysis, and forecasting. Would you like me to send it as a PDF or share a live dashboard?";
    } else if (
      lowerMsg.includes("hello") ||
      lowerMsg.includes("hi") ||
      lowerMsg.includes("hey")
    ) {
      return "Hello! I'm ready to analyze your data. You can ask about revenue, trends, or request a report.";
    } else {
      return "Interesting question. Let me pull the relevant data… Based on the current dataset, I see a 12% improvement in conversion rates after the last campaign. Would you like a deeper drill-down by region?";
    }
  }

  function handleSendMessage() {
    const message = userInput.value.trim();
    if (message === "") return;
    addMessage(message, "user");
    userInput.value = "";
    setTimeout(() => {
      const reply = getAIResponse(message);
      addMessage(reply, "bot");
    }, 800);
  }

  sendBtn.addEventListener("click", handleSendMessage);
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSendMessage();
    }
  });

  const bars = document.querySelectorAll(".bar-fill");
  bars.forEach((bar) => {
    const width = bar.style.width;
    bar.style.width = "0%";
    setTimeout(() => {
      bar.style.width = width;
    }, 400);
  });
});
