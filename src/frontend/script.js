document.addEventListener("DOMContentLoaded", () => {
  // dom elements
  const landingView = document.getElementById("landing-view");
  const chatView = document.getElementById("chat-view");

  const loginModal = document.getElementById("login-modal");
  const registerModal = document.getElementById("register-modal");

  const btnOpenLogin = document.getElementById("btn-open-login");
  const btnOpenRegister = document.getElementById("btn-open-register");
  const closeLogin = document.getElementById("close-login");
  const closeRegister = document.getElementById("close-register");

  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const btnLogout = document.getElementById("btn-logout");

  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatContainer = document.getElementById("chat-container");

  // config URL Backend
  const BASE_URL = "http://localhost:8000";

  // close/open modal
  const openModal = (modal) => {
    modal.style.display = "flex";
  };
  const closeModal = (modal) => {
    modal.style.display = "none";
  };

  btnOpenLogin.addEventListener("click", () => openModal(loginModal));
  btnOpenRegister.addEventListener("click", () => openModal(registerModal));
  closeLogin.addEventListener("click", () => closeModal(loginModal));
  closeRegister.addEventListener("click", () => closeModal(registerModal));

  window.addEventListener("click", (e) => {
    if (e.target === loginModal) closeModal(loginModal);
    if (e.target === registerModal) closeModal(registerModal);
  });

  // login automation (API /me)
  const checkAuthAndAutoLogin = async () => {
    const token = localStorage.getItem("ai_agent_token");
    if (!token) return; // if no token, do nothing

    try {
      const response = await fetch(`${BASE_URL}/users/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        console.log(`Auto-login successful! Hello: ${userData.username}`);

        // if token valid, directly show chat view
        landingView.classList.remove("view-active");
        landingView.classList.add("view-hidden");

        chatView.classList.remove("view-hidden");
        chatView.classList.add("view-active");
      } else {
        // if token invalid/expired, remove it from storage
        console.warn("Token expired or invalid. Removing from storage.");
        localStorage.removeItem("ai_agent_token");
      }
    } catch (error) {
      console.error("Error checking authentication:", error);
    }
  };

  checkAuthAndAutoLogin();

  // Register (API /register - JSON)
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(registerForm);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await fetch(`${BASE_URL}/users/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        // successfully registered, now auto-login the user
        closeModal(registerModal);

        landingView.classList.remove("view-active");
        landingView.classList.add("view-hidden");

        chatView.classList.remove("view-hidden");
        chatView.classList.add("view-active");

        registerForm.reset();

        try {
          const result = await response.json();
          console.log("success register:", result);
        } catch (err) {
          console.log("Register successful (Backend returned status 201).");
        }
      } else {
        const errorData = await response.json();
        const errorMessage =
          errorData.detail || errorData.message || "Register failed.";
        alert(`Error: ${errorMessage}`);
      }
    } catch (error) {
      console.error("Error connection:", error);
    }
  });

  // login (API /login - Form URL Encoded)
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    // collect form data and convert to URL-encoded string
    const formData = new FormData(loginForm);
    const urlEncodedData = new URLSearchParams(formData).toString();

    try {
      const response = await fetch(`${BASE_URL}/users/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: urlEncodedData,
      });

      if (response.ok) {
        const result = await response.json();

        // save token to localStorage for future authenticated requests
        localStorage.setItem("ai_agent_token", result.access_token);
        console.log("Login successful! Token saved.");

        // close modal and show chat view
        closeModal(loginModal);

        landingView.classList.remove("view-active");
        landingView.classList.add("view-hidden");

        chatView.classList.remove("view-hidden");
        chatView.classList.add("view-active");

        loginForm.reset();
      } else {
        const errorData = await response.json();
        const errorMessage = errorData.detail || "Invalid login information.";
        alert(errorMessage);
      }
    } catch (error) {
      console.error("Network error:", error);
      alert("Cannot connect to the server. Please check the backend.");
    }
  });

  // logout
  btnLogout.addEventListener("click", () => {
    // Remove Token from browser storage
    localStorage.removeItem("ai_agent_token");
    console.log("Logged out.");

    // Go back to Landing Page
    chatView.classList.remove("view-active");
    chatView.classList.add("view-hidden");

    landingView.classList.remove("view-hidden");
    landingView.classList.add("view-active");

    // Clear data on forms
    loginForm.reset();
    registerForm.reset();
  });

  // CHAT - API /messages/send_message
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const messageText = chatInput.value.trim();
    if (!messageText) return;

    // display user message immediately for better UX
    appendMessage("user", messageText);
    chatInput.value = "";

    // get token from localStorage to authenticate API request
    const token = localStorage.getItem("ai_agent_token");
    if (!token) {
      appendMessage(
        "ai",
        "[System Error]: Trying to send message without authentication. Please log in again.",
      );
      return;
    }

    try {
      // send message to BE API
      const response = await fetch(`${BASE_URL}/messages/send_message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: messageText }),
      });

      if (response.ok) {
        const data = await response.json();

        // receive AI response and display in chat
        const aiResponse = data.content;

        appendMessage("ai", aiResponse);
      } else {
        const errorData = await response.json();
        appendMessage(
          "ai",
          `[System Error]: ${errorData.detail || "Cannot analyze data."}`,
        );
      }
    } catch (error) {
      console.error("Error calling chat API:", error);
      appendMessage(
        "ai",
        "[System Error]: Cannot connect to the server. Please check the backend.",
      );
    }
  });

  function appendMessage(sender, text) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", `${sender}-message`);

    const avatar = sender === "ai" ? "AI" : "U";

    msgDiv.innerHTML = `
      <div class="avatar">${avatar}</div>
      <div class="text">${text}</div>
    `;

    chatContainer.appendChild(msgDiv);

    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
});
